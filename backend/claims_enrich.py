import os, torch, json , re, pickle, string
import numpy as np
from tqdm import tqdm
from transformers import pipeline, AutoTokenizer, AutoModel
from underthesea import word_tokenize, pos_tag
from collections import Counter
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
INPUT_FILE = os.path.join(DATA_DIR, "claims_checkpoint.json")
OUTPUT_FILE = os.path.join(DATA_DIR, "claims_enriched.json")

# ======================================================
# STAGE 1️⃣ — TOPIC CLASSIFICATION (with filtering)
# ======================================================
TOPIC_LABELS = [
    "Sức khỏe & Y tế",
    "Dinh dưỡng & Thực phẩm",
    "Tai nạn & An toàn",
    "Lối sống & Thói quen",
    "Trẻ em & Giáo dục",
    "Thể thao",
    "Công nghệ & Khoa học",
    "Xã hội & Pháp luật",
    "Giải trí & Văn hóa"
]
MIN_CONFIDENCE = 0.5

print("🔹 Loading zero-shot topic classifier (joeddav/xlm-roberta-large-xnli)...")
classifier = pipeline(
    "zero-shot-classification",
    model="joeddav/xlm-roberta-large-xnli",
    device=0 if torch.cuda.is_available() else -1
)
print("✅ Topic model loaded.\n")


# FIX: claim is now an object, so claim["text"], not the raw string
def classify_topics(articles):
    filtered = []
    total_in, total_out = 0, 0

    for art in tqdm(articles, desc="📊 Classifying topics"):
        kept_claims = []

        for claim in art["claims"]:
            total_in += 1
            
            # FIX: extract text properly
            claim_text = claim["text"].strip()

            prompt = (
                f"Đây là một câu trong bài báo tiếng Việt: '{claim_text}'. "
                "Hãy xác định chủ đề phù hợp nhất trong danh sách sau."
            )

            result = classifier(prompt, TOPIC_LABELS, multi_label=True)
            scores, labels = result["scores"], result["labels"]

            top_idx = int(np.argmax(scores))
            top_label, top_score = labels[top_idx], float(scores[top_idx])

            if top_score < MIN_CONFIDENCE:
                continue

            kept_claims.append({
                "text": claim_text,
                "topic": top_label,
                "confidence": round(top_score, 3)
            })
            total_out += 1

        if kept_claims:
            art["claims"] = kept_claims
            filtered.append(art)

    drop_ratio = (total_in - total_out) / max(1, total_in) * 100
    print(f"\n✅ Topic filtering done — {total_out}/{total_in} kept ({100 - drop_ratio:.1f}%)\n")
    return filtered


# ======================================================
# STAGE 2️⃣ — NER (Electra-based + DATE regex)
# ======================================================
print("🔹 Loading NER model (NlpHUST/ner-vietnamese-electra-base)...")
ner_pipeline = pipeline(
    "token-classification",
    model="NlpHUST/ner-vietnamese-electra-base",
    tokenizer="NlpHUST/ner-vietnamese-electra-base",
    aggregation_strategy="simple"
)
print("✅ NER model loaded.\n")

DATE_PATTERNS = [
    r"\b(?:năm|tháng|ngày)\s+\d{1,4}\b",
    r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b",
    r"\b\d{1,2}-\d{1,2}(?:-\d{2,4})?\b",
    r"\b\d{4}\b",
    r"\bmỗi\s+(sáng|chiều|ngày|tuần|tháng|năm)\b",
    r"\b(?:hôm nay|ngày mai|hôm qua)\b",
    r"\b(?:mùa xuân|mùa hè|mùa thu|mùa đông)\b",
]

def extract_dates(text):
    found = []
    for pattern in DATE_PATTERNS:
        for m in re.finditer(pattern, text, flags=re.IGNORECASE):
            found.append({"label": "DATE", "text": m.group(), "start": m.start(), "end": m.end(), "score": 1.0})
    return found

def add_entities(articles):
    enriched = []
    for art in tqdm(articles, desc="🔍 Extracting entities"):
        new_claims = []
        for c in art["claims"]:
            text = c["text"]
            ents = ner_pipeline(text)
            entities = [{"label": e["entity_group"], "text": e["word"], "score": float(e["score"])} for e in ents]
            entities += extract_dates(text)
            c["entities"] = entities
            new_claims.append(c)
        art["claims"] = new_claims
        enriched.append(art)
    return enriched


# ======================================================
# STAGE 3️⃣ — KEYWORD EXTRACTION
# ======================================================
MODEL_NAME = "intfloat/multilingual-e5-base"
print(f"🔹 Loading model: {MODEL_NAME} ...")
device = "cuda" if torch.cuda.is_available() else "cpu"
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
e5_model = AutoModel.from_pretrained(MODEL_NAME).to(device)
e5_model.eval()

CACHE_FILE = os.path.join(DATA_DIR, "embedding_cache.pkl")
embedding_cache = {}
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "rb") as f:
        embedding_cache = pickle.load(f)

VI_STOPWORDS = {
    "là","ở","của","và","hoặc","với","cho","này","kia","đó",
    "trong","khi","để","các","những","một","được","bị","tại","theo"
}

def clean_phrase(p):
    p = p.strip().lower()
    p = re.sub(r"\s+", " ", p)
    p = re.sub(r"\(.*?\)", "", p).strip()
    if re.search(r"[,\.;:!?“”‘’…]", p):
        return None
    if sum(ch.isdigit() for ch in p) > len(p) * 0.4:
        return None
    if len(p.split()) < 2:
        return None
    toks = p.split()
    if sum(t in VI_STOPWORDS for t in toks) / len(toks) > 0.4:
        return None
    return p

def get_embeds(texts):
    new = [t for t in texts if t not in embedding_cache]
    if new:
        formatted = [f"passage: {t}" for t in new]

        inputs = tokenizer(
            formatted,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=256
        ).to(device)

        with torch.no_grad():
            out = e5_model(**inputs)
            cls_emb = out.last_hidden_state[:, 0, :]
            cls_emb = cls_emb / cls_emb.norm(dim=1, keepdim=True)

        for t, emb in zip(new, cls_emb.cpu().numpy()):
            embedding_cache[t] = emb

    return np.array([embedding_cache[t] for t in texts])

def cosine(a, b): 
    return cosine_similarity(a, b)

def generate_candidates(text):
    tokens = [t.replace("_", " ") for t in word_tokenize(text)]
    cands = set()

    for n in range(1, 5):
        for i in range(len(tokens) - n + 1):
            raw_phrase = " ".join(tokens[i:i+n])
            cleaned = clean_phrase(raw_phrase)
            if not cleaned:
                continue

            try:
                tags = [t for _, t in pos_tag(cleaned)]
                noun_ratio = sum(t in {"N","Np","Nc","Ng"} for t in tags) / len(tags)
                if noun_ratio < 0.5:
                    continue
            except:
                pass

            cands.add(cleaned)

    return list(cands)

def rank_keywords(text, candidates, top_n=10):
    if not candidates: 
        return []

    doc_text = f"query: {text}"
    cand_texts = [f"passage: {c}" for c in candidates]
    texts = [doc_text] + cand_texts

    embs = get_embeds(texts)
    doc_emb = embs[0].reshape(1, -1)
    cand_embs = embs[1:]

    sims = cosine(doc_emb, cand_embs)[0]
    ranked = sorted(zip(candidates, sims), key=lambda x: x[1], reverse=True)
    
    return [k for k,_ in ranked[:top_n]]

def dedupe_keywords(kws):
    final = []
    for k in sorted(kws, key=len, reverse=True):
        if not any(k in other for other in final):
            final.append(k)
    return final

def add_keywords(articles):
    final = []
    for art in tqdm(articles, desc="💡 Extracting keywords"):
        new_claims = []
        for c in art["claims"]:
            text = c["text"]
            cands = generate_candidates(text)
            kws = rank_keywords(text, cands)
            kws = dedupe_keywords(kws)
            c["keywords"] = kws
            new_claims.append(c)
        art["claims"] = new_claims
        final.append(art)
    return final


# ======================================================
# FLATTEN
# ======================================================
def flatten_claims(articles):
    flat = []
    for art in articles:
        art_id = art.get("id")
        art_url = art.get("url", "")

        for c in art["claims"]:
            flat.append({
                "article_id": art_id,
                "url": art_url,
                **c
            })
    return flat

# ======================================================
# MAIN PIPELINE
# ======================================================
def main():
    print(f"📂 Loading cleaned claims from {INPUT_FILE}")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        data = [data]

    # FIX: missing bracket and normalize claims
    for art in data:
        art["claims"] = [
            {"text": c} if isinstance(c, str) else c
            for c in art["claims"]
        ]

    step1 = classify_topics(data)
    step2 = add_entities(step1)
    step3 = add_keywords(step2)

    final = flatten_claims(step3)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 Enrichment complete → {OUTPUT_FILE}")
    print(f"📄 Total claims saved: {len(final)}")


if __name__ == "__main__":
    main()
