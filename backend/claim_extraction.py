import os, json, torch, re
from tqdm import tqdm
from datetime import datetime
from transformers import (
    pipeline,
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig
)

# ======================================
# 🔧 Config
# ======================================
os.environ["TRANSFORMERS_SAFE_MODEL_FORCING"] = "1"
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:64"

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")

INPUT_FILE = os.path.join(DATA_DIR, "crawled_sentences.json")
OUTPUT_FILE = os.path.join(DATA_DIR, "claims_output.json")
CHECKPOINT_FILE = os.path.join(DATA_DIR, "claims_checkpoint.json")
OFFLOAD_DIR = os.path.join(BASE_DIR, "offload_cache")

MODEL = "Qwen/Qwen3-4B-Instruct-2507"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OFFLOAD_DIR, exist_ok=True)

# ======================================
# ⚙️ Load Model
# ======================================
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
)

print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 Loading model...")
tokenizer = AutoTokenizer.from_pretrained(MODEL, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    MODEL,
    device_map="auto",
    quantization_config=bnb_config,
    low_cpu_mem_usage=True,
    offload_folder=OFFLOAD_DIR,
    trust_remote_code=True,
)
model.eval()

pipe = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
    torch_dtype=torch.float16,
    trust_remote_code=True,
    return_full_text=False,  
)

print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Model loaded!\n")

DEBUG = True

# ======================================
# 🧠 Single-Sentence JSON Classifier
# ======================================
@torch.inference_mode()
def classify_sentence(sentence: str) -> bool:
    prompt = f"""
Bạn là hệ thống phân loại câu.

Nhiệm vụ:
Xác định xem câu sau có phải là một phát biểu mang tính thực tế,
mô tả một sự kiện, hành động, con số hoặc thông tin khách quan
mà về nguyên tắc có thể kiểm chứng được.

KHÔNG được xem là phát biểu thực tế:
- ý kiến cá nhân
- cảm xúc
- dự đoán
- phỏng đoán
- lời khuyên
- nhận xét chủ quan
- câu đùa hoặc ví dụ minh hoạ
- trích dẫn bình luận của người khác

Câu: "{sentence}"

TRẢ LỜI THEO ĐÚNG ĐỊNH DẠNG JSON CHỈ GỒM:
{{ "answer": "YES" }}
hoặc
{{ "answer": "NO" }}

Không viết gì khác.
"""
    response = pipe(
        [{"role": "user", "content": prompt}],
        max_new_tokens=50,
        temperature=0.0,
        do_sample=False
    )[0]["generated_text"]

    print("-----")
    print("Câu:", sentence)
    print("Phân loại:", response)
    print("-----\n")

    match = re.search(r'\{\s*"answer"\s*:\s*"(YES|NO)"\s*\}', response)
    if not match:
        return False

    return match.group(1) == "YES"

# ======================================
# 🧠 Extract claims (NO BATCH)
# ======================================
def extract_claims_from_sentences(sentences: list[str]) -> list[str]:
    claims = []
    for s in sentences:
        if classify_sentence(s):
            claims.append(s.strip())
    return claims


# ======================================
# 📂 File helpers
# ======================================
def load_articles():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data if isinstance(data, list) else [data]

def load_existing(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
            return d if isinstance(d, list) else []
    except:
        return []

def save_checkpoint(results, path):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


# ======================================
# 🚀 Main
# ======================================
def main():
    articles = load_articles()
    print(f"📂 Loaded {len(articles)} sentence-level articles")

    results = load_existing(OUTPUT_FILE)
    checkpoint = load_existing(CHECKPOINT_FILE)

    merged = {r["id"]: r for r in (results + checkpoint) if "id" in r}
    done_ids = set(merged.keys())

    start = datetime.now()

    for article in tqdm(articles, desc="🧠 Classifying sentences"):
        article_id = article["id"]
        if article_id in done_ids:
            continue

        sentences = article.get("sentences", [])
        if not sentences:
            continue

        claims = extract_claims_from_sentences(sentences)
        article_url = article.get("url", "")

        merged[article_id] = {
            "id": article_id,
            "url": article_url,
            "claims": claims,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }

        if len(merged) % 5 == 0:
            save_checkpoint(list(merged.values()), CHECKPOINT_FILE)

    save_checkpoint(list(merged.values()), OUTPUT_FILE)

    print(f"\n✅ Done! Saved {len(merged)} results → {OUTPUT_FILE}")
    print("⏱️ Runtime:", datetime.now() - start)


if __name__ == "__main__":
    main()
