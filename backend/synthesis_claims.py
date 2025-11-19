import os, json, torch, numpy as np
from tqdm import tqdm
from collections import defaultdict, Counter
from sentence_transformers import SentenceTransformer, util
from sklearn.cluster import DBSCAN, KMeans
from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    AutoModelForSequenceClassification,
)

# =====================================================
# CONFIG
# =====================================================
EMBED_MODEL = "intfloat/multilingual-e5-base"
SUMMARY_MODEL = "VietAI/vit5-base-vietnews-summarization"
NLI_MODEL = "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"

MIN_CLAIMS_PER_GROUP = 2
CONFIDENCE_THRESHOLD = 0.65
INPUT_PATH = "./data/claims_enriched.json"
OUTPUT_PATH = "./data/claims_grouped_summary.json"

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# =====================================================
# LOAD MODELS
# =====================================================
print("🔄 Loading models...")
embedder = SentenceTransformer(EMBED_MODEL)
tokenizer_sum = AutoTokenizer.from_pretrained(SUMMARY_MODEL)
model_sum = AutoModelForSeq2SeqLM.from_pretrained(SUMMARY_MODEL).to(device)
tokenizer_nli = AutoTokenizer.from_pretrained(NLI_MODEL)
model_nli = AutoModelForSequenceClassification.from_pretrained(NLI_MODEL).to(device)

# =====================================================
# LOAD & FLATTEN DATA (NEW ENRICHED FLAT FORMAT)
# =====================================================
raw_data = json.load(open(INPUT_PATH, "r", encoding="utf-8"))
print(f"📥 Loaded {len(raw_data)} enriched claim rows.")

claims = []

for item in raw_data:
    # must contain text
    text = item.get("text")
    if not text:
        continue

    # filter low-confidence claims early
    if item.get("confidence", 0) < CONFIDENCE_THRESHOLD:
        continue

    claims.append({
        "id": item.get("article_id"),
        "url": item.get("url", ""),
        "title": item.get("title", ""),
        "claim": text.strip(),
        "topic": item.get("topic", "Chưa xác định"),
        "reliability": item.get("confidence", 0.0),
        "entities": item.get("entities", []),
        "keywords": item.get("keywords", []),
    })

print(f"📚 Loaded {len(claims)} valid high-confidence claims.")

# =====================================================
# HELPERS
# =====================================================
def entity_text(c):
    ents = c.get("entities", [])
    if not ents:
        return ""
    return " | Thực thể: " + ", ".join(e["text"] for e in ents if e.get("text"))

def normalize_entities(text):
    return (
        text.replace("WHO", "Tổ chức Y tế Thế giới")
        .replace("TP HCM", "TP.HCM")
        .replace("VN", "Việt Nam")
    )

def boost_embedding(embedding, claim):
    """Weight embeddings by number of entities and keywords."""
    weight = 1.0 + 0.05 * len(claim.get("entities", [])) + 0.02 * len(claim.get("keywords", []))
    return embedding * weight

# =====================================================
# STEP 1 — GROUP CLAIMS BY TOPIC
# =====================================================
topic_groups = defaultdict(list)
for c in claims:
    topic = c.get("topic") or "Chưa xác định"
    topic_groups[topic].append(c)

print(f"🧩 Found {len(topic_groups)} topic categories.")

# =====================================================
# STEP 2 — CLUSTER WITHIN EACH TOPIC (ADAPTIVE + FALLBACK)
# =====================================================
groups = {}
group_counter = 0

for topic, topic_claims in tqdm(topic_groups.items(), desc="🔹 Clustering by topic"):
    if len(topic_claims) < 2:
        continue

    # 🔧 Adaptive eps based on topic
    if "Sức khỏe" in topic or "Y tế" in topic:
        eps = 0.48
    elif "Lối sống" in topic or "Thói quen" in topic:
        eps = 0.46
    else:
        eps = 0.44

    texts = [normalize_entities(c["claim"]) + entity_text(c) for c in topic_claims]
    embeddings = embedder.encode(
        texts,
        normalize_embeddings=True,
        convert_to_tensor=True,
        show_progress_bar=False,
    )
    embeddings = torch.stack([boost_embedding(emb, topic_claims[i]) for i, emb in enumerate(embeddings)])

    sim_matrix = util.cos_sim(embeddings, embeddings).cpu().numpy()
    dist_matrix = np.clip(1 - sim_matrix, 0, 1)

    clustering = DBSCAN(eps=eps, min_samples=2, metric="precomputed").fit(dist_matrix)
    labels = clustering.labels_

    unique_labels = set(labels)
    cluster_count = len(unique_labels) - (1 if -1 in unique_labels else 0)
    noise_points = list(labels).count(-1)
    print(f"🧮 Topic '{topic}': {cluster_count} clusters, {noise_points} noise points (eps={eps}).")

    local_clusters = defaultdict(list)
    for i, label in enumerate(labels):
        if label == -1:
            continue
        local_clusters[int(label)].append(topic_claims[i])

    # ✅ Simplified filtering: semantic cohesion only
    for cluster_id, cluster_claims in local_clusters.items():
        if len(cluster_claims) < MIN_CLAIMS_PER_GROUP:
            continue
        sub_emb = embedder.encode(
            [c["claim"] for c in cluster_claims],
            normalize_embeddings=True,
            convert_to_tensor=True,
        )
        avg_sim = float(util.cos_sim(sub_emb, sub_emb).mean())
        if avg_sim < 0.3:
            continue
        groups[group_counter] = cluster_claims
        group_counter += 1

    # 🧩 Fallback KMeans clustering if DBSCAN too coarse
    if cluster_count <= 1 and len(topic_claims) >= 4:
        k = min(3, len(topic_claims) // 3 + 1)
        print(f"⚙️  Fallback KMeans for '{topic}' (k={k}) ...")
        kmeans = KMeans(n_clusters=k, n_init=5, random_state=42)
        k_labels = kmeans.fit_predict(embeddings.cpu().numpy())
        km_clusters = defaultdict(list)
        for i, label in enumerate(k_labels):
            km_clusters[int(label)].append(topic_claims[i])
        for cluster_id, cluster_claims in km_clusters.items():
            if len(cluster_claims) < MIN_CLAIMS_PER_GROUP:
                continue
            groups[group_counter] = cluster_claims
            group_counter += 1

print(f"✅ Created {len(groups)} refined entity-aware claim groups.")

# =====================================================
# STEP 3 — SUMMARIZATION
# =====================================================
def summarize_viet(claims_list, topic):
    text = " ".join(claims_list)
    prefix = "Tóm tắt ngắn gọn, trung lập, không thêm suy diễn: "
    inputs = tokenizer_sum(prefix + text, return_tensors="pt", truncation=True, max_length=512).to(device)
    summary_ids = model_sum.generate(
        **inputs,
        num_beams=3,
        no_repeat_ngram_size=2,
        max_length=80,
        min_length=15,
        early_stopping=True,
    )
    return tokenizer_sum.decode(summary_ids[0], skip_special_tokens=True).strip()

# =====================================================
# STEP 4 — CONTRADICTION DETECTION
# =====================================================
def check_contradictions(claims_list):
    contradictions = 0
    total_pairs = 0
    for i in range(len(claims_list)):
        for j in range(i + 1, len(claims_list)):
            total_pairs += 1
            pair = (claims_list[i], claims_list[j])
            inputs = tokenizer_nli(pair, return_tensors="pt", truncation=True, padding=True).to(device)
            with torch.no_grad():
                logits = model_nli(**inputs).logits
                preds = torch.argmax(torch.softmax(logits, dim=-1), dim=-1)
                if preds[0].item() == 0:
                    contradictions += 1
    return total_pairs > 0 and contradictions / total_pairs > 0.3

# =====================================================
# STEP 5 — SUMMARIZE & SAVE
# =====================================================
results = []
for gid, group_claims in tqdm(groups.items(), desc="🧾 Summarizing groups"):
    claim_texts = [c["claim"] for c in group_claims]
    topic_candidates = [c["topic"] for c in group_claims if c["topic"]]
    topic = max(set(topic_candidates), key=topic_candidates.count, default="Chung")

    summary = summarize_viet(claim_texts, topic)
    contradiction = check_contradictions(claim_texts)

    reliabilities = [c["reliability"] for c in group_claims if c.get("reliability") is not None]
    avg_rel = round(float(np.mean(reliabilities)), 3) if reliabilities else None

    all_keywords = [kw for c in group_claims for kw in c.get("keywords", [])]
    top_keywords = [k for k, _ in Counter(all_keywords).most_common(8)]

    all_entities = [e["text"] for c in group_claims for e in c.get("entities", []) if e.get("text")]
    top_entities = [e for e, _ in Counter(all_entities).most_common(6)]

    results.append({
        "group_id": int(gid),
        "summary": summary,
        "topic": topic,
        "keywords": top_keywords,
        "entities": top_entities,
        "claims": claim_texts,
        "sources": list(set(c["url"] for c in group_claims)),
        "avg_reliability": avg_rel,
        "conflict": contradiction,
    })

# =====================================================
# STEP 6 — SAVE OUTPUT & REPORT
# =====================================================
json.dump(results, open(OUTPUT_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

all_entities = [ent for g in results for ent in g.get("entities", [])]
avg_group_size = np.mean([len(g["claims"]) for g in results]) if results else 0

print("\n📊 === SUMMARY REPORT ===")
print(f"🧠 Total groups: {len(results)}")
print(f"📄 Avg claims/group: {avg_group_size:.2f}")
print(f"🏷️ Unique entities: {len(set(all_entities))}")
if all_entities:
    print(f"🔥 Top entities: {', '.join([e for e, _ in Counter(all_entities).most_common(10)])}")
print(f"\n💾 Saved grouped + summarized claims to: {OUTPUT_PATH}")
