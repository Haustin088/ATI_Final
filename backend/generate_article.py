import os, json, re, random
from datetime import datetime
from typing import List, Dict, Any, Optional

import torch
from sentence_transformers import SentenceTransformer
from sklearn.cluster import AgglomerativeClustering
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, pipeline

# -----------------------------
# CONFIG
# -----------------------------
MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"
OFFLOAD_DIR = os.path.join(os.path.dirname(__file__), "model_offload")
os.makedirs(OFFLOAD_DIR, exist_ok=True)

EMBED_MODEL = "intfloat/multilingual-e5-base"
EMBED_MIN_LEN = 80
SUMMARY_MIN_LEN = 50

FIXED_INTRO = "Những thông tin dưới đây được tổng hợp từ các dữ liệu hiện có và được trình bày theo cách trung lập, khách quan nhất có thể."
FIXED_DISCLAIMER = "Dàn ý dưới đây nhằm hệ thống hóa nội dung từ các nguồn liên quan và không thay thế cho đánh giá đầy đủ của chuyên gia hay cơ quan chức năng."
FIXED_CLOSING = "Dù nội dung thuộc lĩnh vực nào, việc tiếp cận thông tin một cách thận trọng và dựa trên nguồn đáng tin cậy luôn là yếu tố quan trọng."
FIXED_SIGNATURE = "Chúng tôi sẽ tiếp tục cập nhật khi có thêm dữ liệu mới hoặc các thông tin liên quan."

HEALTH_KEYWORDS = [
    "ung thư", "carotenoid", "dịch tễ", "phòng ngừa", "lối sống", "vaccine",
    "tim mạch", "đái tháo đường", "huyết áp", "sức khỏe", "kháng sinh",
    "bệnh", "triệu chứng", "chẩn đoán"
]

# -----------------------------
# MODEL LOAD (module-level)
# -----------------------------
print(f"[generate_article] [{datetime.now().strftime('%H:%M:%S')}] 🔄 Loading Qwen model ({MODEL_NAME})...")

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
)

# load tokenizer & model
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
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

print(f"[generate_article] [{datetime.now().strftime('%H:%M:%S')}] ✅ Model ready.")

# -----------------------------
# EMBEDDING MODEL
# -----------------------------
_embed_model = SentenceTransformer(EMBED_MODEL)


def embed_claims(claims: List[str]):
    if not claims:
        return None
    return _embed_model.encode(claims, normalize_embeddings=True)


# -----------------------------
# CLUSTERING
# -----------------------------
def cluster_claims(embeddings, distance_threshold=0.8):
    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=distance_threshold,
        metric="cosine",
        linkage="average",
    )
    return clustering.fit_predict(embeddings)


def group_by_label(claims: List[str], labels: List[int]) -> Dict[int, List[str]]:
    groups: Dict[int, List[str]] = {}
    for c, l in zip(claims, labels):
        groups.setdefault(int(l), []).append(c)
    return groups


# -----------------------------
# LLM wrapper
# -----------------------------
def llm(prompt: str, max_tokens: int = 400) -> str:
    out = pipe(
        [{"role": "user", "content": prompt}],
        max_new_tokens=max_tokens,
        do_sample=False,
        temperature=0.1,
        repetition_penalty=1.05,
    )
    return out[0].get("generated_text", "").strip()


# -----------------------------
# Safe templates for expansion (no LLM)
# -----------------------------
UNIVERSAL_REASONING = [
    "Điều này cho thấy tình tiết này có vai trò đáng chú ý trong toàn bộ bối cảnh.",
    "Chi tiết này phản ánh một phần diễn biến cần được quan tâm thêm.",
    "Điều này nhấn mạnh rằng các sự việc có thể phức tạp hơn so với quan sát ban đầu.",
    "Thông tin này giúp làm rõ hơn diễn biến chung của sự việc.",
    "Đây là một yếu tố quan trọng trong việc hiểu toàn bộ câu chuyện.",
]

UNIVERSAL_CONTEXT = [
    "một chi tiết cần được theo dõi kỹ hơn.",
    "một phần của bức tranh tổng thể đang dần hé lộ.",
    "một khía cạnh thể hiện chiều sâu của sự việc.",
    "một dấu hiệu cho thấy câu chuyện có thể liên quan đến nhiều yếu tố khác nhau.",
    "một điểm đáng chú ý khi đặt cạnh các claim khác.",
]

UNIVERSAL_CONNECTORS = [
    "Bên cạnh đó,",
    "Ngoài ra,",
    "Ở một diễn biến liên quan,",
    "Theo ghi nhận,",
    "Trong bối cảnh đó,",
]

def expand_claim_safe(claim: str) -> str:
    c = (claim or "").strip()
    if not c:
        return c
    if len(c) >= 90:
        return c

    # safe expansion pieces
    part1 = random.choice(UNIVERSAL_REASONING)
    part2 = random.choice(UNIVERSAL_CONTEXT)
    connector = random.choice(UNIVERSAL_CONNECTORS)

    expanded = f"{c}. {part1} Đây là {part2}"
    if random.random() < 0.35:
        expanded = f"{connector} {expanded[0].lower() + expanded[1:]}"
    return expanded

# -----------------------------
# JSON helpers
# -----------------------------
_JSON_OBJ_RE = re.compile(r"\{[\s\S]*?\}")


def extract_first_json(raw: str) -> Optional[str]:
    if not raw:
        return None
    stack = 0
    start = None
    for i, ch in enumerate(raw):
        if ch == "{":
            if stack == 0:
                start = i
            stack += 1
        elif ch == "}":
            if stack > 0:
                stack -= 1
                if stack == 0 and start is not None:
                    return raw[start:i + 1]
    m = _JSON_OBJ_RE.search(raw)
    return m.group(0) if m else None


def safe_load_json(raw: str) -> Optional[dict]:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        snippet = extract_first_json(raw)
        if not snippet:
            return None
        try:
            return json.loads(snippet)
        except Exception:
            return None


# -----------------------------
# Topic naming: LLM suggests N names (one per group). We map deterministically.
# -----------------------------
def name_topics_safely(num_groups: int) -> List[str]:
    prompt = f"""
Bạn là trợ lý biên tập. Hãy đặt {num_groups} tên chủ đề NGẮN (1–5 từ), mỗi tên trên 1 dòng.
YÊU CẦU:
- Không giải thích.
- Tránh các cụm chung chung như 'tác dụng thuốc', 'nguyên nhân bệnh', 'lối sống'.
- Không được thêm claim hay phân tích.
"""
    raw = llm(prompt, max_tokens=80)
    lines = [l.strip("-• ").strip() for l in raw.split("\n") if l.strip()]
    # ensure count
    while len(lines) < num_groups:
        lines.append(f"Chủ đề {len(lines)+1}")
    return lines[:num_groups]


def refine_clusters_with_qwen(cluster_groups: Dict[int, List[str]]) -> Dict[str, List[str]]:
    # deterministic safe mapping: LLM provides N names, we map by order to preserve claims
    num = len(cluster_groups)
    names = name_topics_safely(num)
    refined: Dict[str, List[str]] = {}
    for (cid, clist), name in zip(cluster_groups.items(), names):
        refined[name] = clist
    return refined


# -----------------------------
# Strict rewrite (use LLM but forbid adding facts)
# -----------------------------
def rewrite_claim_strict(claim: str) -> str:
    prompt = f"""
Viết lại câu sau rõ ràng hơn nhưng KHÔNG được thêm bất kỳ thông tin mới nào:
"{claim}"
YÊU CẦU:
- 1 câu duy nhất.
- Không thêm nguyên nhân, không thêm chẩn đoán, không suy đoán.
- Giữ nguyên các thực tế trong câu gốc.
BẮT ĐẦU:
"""
    out = llm(prompt, max_tokens=60).strip()
    out = out.strip("-• ").strip()
    return out if out else claim


def rewrite_all_claims_strict(claims: List[str]) -> List[str]:
    return [rewrite_claim_strict(c) for c in claims]


# -----------------------------
# Enrichment: expand short claims using safe templates (no LLM)
# -----------------------------
def enrich_claims_safe(claims: List[str]) -> List[str]:
    return [expand_claim_safe(c) for c in claims]


def enrich_summary(summary: str) -> str:
    if not summary:
        return ""
    if len(summary.strip()) < SUMMARY_MIN_LEN:
        p = f"""
Viết lại tóm tắt sau cho rõ ràng, đầy đủ hơn nhưng KHÔNG thêm thông tin mới:
"{summary}"
"""
        out = llm(p, max_tokens=80).strip()
        return out if out else summary
    return summary


# -----------------------------
# Balance single-claim topics (optional LLM but safe)
# -----------------------------
def balance_topics(topics: Dict[str, List[str]]) -> Dict[str, List[str]]:
    balanced: Dict[str, List[str]] = {}
    for topic, clist in topics.items():
        if len(clist) == 1:
            claim = clist[0]
            # ask LLM to paraphrase 1-2 clarifying sentences, but forbid new facts
            p = f"""
Dưới đây là một claim duy nhất:
"{claim}"
Hãy viết 1–2 câu diễn đạt lại để làm rõ ý nhưng KHÔNG được thêm thông tin mới.
Mỗi câu là một đơn vị ngắn.
"""
            out = llm(p, max_tokens=120).strip()
            lines = [l.strip() for l in re.split(r'\n|\.|\!|\?', out) if l.strip()]
            extras = [l for l in lines if len(l) > 10][:2]
            balanced[topic] = [claim] + extras
        else:
            balanced[topic] = clist
    return balanced


# -----------------------------
# Mode detection
# -----------------------------
def detect_mode_from_claims(claims: List[str]) -> str:
    text = " ".join(claims).lower()
    score = 0
    for kw in HEALTH_KEYWORDS:
        if kw in text:
            score += 1
    advisory_phrases = ["cần", "nên", "để phòng ngừa", "lời khuyên", "giúp giảm", "làm tăng"]
    for ph in advisory_phrases:
        if ph in text:
            score += 1
    return "explainer" if score >= 2 else "news"


# -----------------------------
# Cleaners and outline helpers
# -----------------------------
def normalize_bullets(text: str) -> str:
    lines = text.split("\n")
    out_lines = []
    for l in lines:
        s = l.strip()
        if not s:
            continue
        s = re.sub(r'^(Nhóm|Group)\s*\d+\s*:\s*', '', s, flags=re.IGNORECASE)
        if re.match(r"^\d+\.\s+", s):
            s = "- " + re.sub(r"^\d+\.\s+", "", s)
        if s.startswith("* "):
            s = "- " + s[2:]
        out_lines.append(s)
    return "\n".join(out_lines)


def collapse_duplicate_blocks(text: str) -> str:
    if not text:
        return text
    text = text.replace("\r\n", "\n")
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    if not paragraphs:
        return text.strip()
    n = len(paragraphs)
    for L in range(1, n//2 + 1):
        if n % L == 0:
            chunk = paragraphs[:L]
            repeats = [paragraphs[i:i+L] for i in range(0, n, L)]
            if all(r == chunk for r in repeats):
                return "\n\n".join(chunk).strip()
    return "\n\n".join(paragraphs).strip()


def clean_outline(text: str) -> str:
    if not text:
        return text
    text = re.sub(r'^(Nhóm|Group)\s*\d+\s*:\s*', '', text, flags=re.IGNORECASE | re.MULTILINE)
    text = normalize_bullets(text)
    text = collapse_duplicate_blocks(text)
    lines = [ln.strip() for ln in text.split("\n")]
    cleaned = []
    prev = None
    for ln in lines:
        if ln == prev:
            continue
        cleaned.append(ln)
        prev = ln
    cleaned_text = []
    for ln in cleaned:
        ln = re.sub(r'^(Giới thiệu ngắn|Giới thiệu):', 'Giới thiệu:', ln, flags=re.IGNORECASE)
        ln = re.sub(r'^(Các luận điểm chính|Nội dung chính|Nội dung):', 'Nội dung chính:', ln, flags=re.IGNORECASE)
        ln = re.sub(r'^(Kết luận nội dung|Kết luận):', 'Kết luận nội dung:', ln, flags=re.IGNORECASE)
        cleaned_text.append(ln)
    return "\n".join(cleaned_text).strip()


# -----------------------------
# Outline generators (strict)
# -----------------------------
def generate_outline_sections_explainer(topics: Dict[str, List[str]]) -> str:
    prompt = f"""
Bạn là biên tập viên nội dung dạng giải thích (explainer).
Dưới đây là các topic với claim (đã được chuẩn hóa):

{json.dumps(topics, ensure_ascii=False, indent=2)}

YÊU CẦU BẮT BUỘC:
1) Mỗi gạch đầu dòng PHẢI dựa TRỰC TIẾP từ claim (trích hoặc diễn đạt lại).
2) KHÔNG được suy đoán, KHÔNG thêm thông tin mới.
3) NGHIÊM CẤM viết các tiêu đề chung như "Tác dụng của thuốc" hoặc "Nguyên nhân bệnh".
4) Giữ cấu trúc 3 phần: Giới thiệu; Nội dung chính; Kết luận nội dung.
5) Mỗi phần 2–4 gạch đầu dòng, bắt đầu bằng "- ".
BẮT ĐẦU:
"""
    raw = llm(prompt, max_tokens=380)
    if not raw or not raw.strip():
        return (
            "Giới thiệu:\n- [Không đủ dữ liệu]\n\n"
            "Nội dung chính:\n- [Không đủ dữ liệu]\n\n"
            "Kết luận nội dung:\n- [Không đủ dữ liệu]"
        )
    return clean_outline(raw)


def generate_outline_sections_news(topics: Dict[str, List[str]]) -> str:
    prompt = f"""
Bạn là biên tập viên tin tức. Dựa trên dữ liệu dưới đây (topic -> claims), hãy viết dàn ý ngắn gọn, factual, không suy đoán.

Dữ liệu:
{json.dumps(topics, ensure_ascii=False, indent=2)}

YÊU CẦU:
- 3 phần: Bối cảnh; Diễn biến chính; Phân tích / Tác động.
- Mỗi phần 2–4 gạch đầu dòng, bắt đầu bằng "-".
- Chỉ dùng thông tin có trong claim, không thêm dữ liệu.
Bắt đầu viết:
"""
    raw = llm(prompt, max_tokens=380)
    if not raw or not raw.strip():
        return "Bối cảnh:\n- [Không đủ dữ liệu]\n\nDiễn biến chính:\n- [Không đủ dữ liệu]\n\nPhân tích / Tác động:\n- [Không đủ dữ liệu]"
    return clean_outline(raw)


# -----------------------------
# Hook generator
# -----------------------------
def generate_hook(summary: str, entity: str = "nhân vật") -> str:
    if not summary or not summary.strip():
        return f"Câu chuyện về {entity} đang thu hút sự chú ý."
    prompt = f"""
Bạn là biên tập viên tin tức.
Viết 1 câu hook mở đầu dựa CHỈ trên tóm tắt sau (không thêm thông tin mới):

TÓM TẮT: "{summary}"

YÊU CẦU:
- 1 câu duy nhất.
- Không thêm, không suy đoán.
- Tự nhiên, rõ nghĩa.
Bắt đầu viết:
"""
    raw = llm(prompt, max_tokens=80)
    s = raw.replace("\n", " ").strip()
    s = s.strip().strip('"').strip("'").strip()
    if "." in s:
        s = s.split(".")[0].strip() + "."
    s = re.sub(r'\s+,', ',', s)
    s = re.sub(r'\s{2,}', ' ', s)
    return s if s else f"Câu chuyện về {entity} đang thu hút sự chú ý."


# -----------------------------
# Final assembly
# -----------------------------
def assemble_final_output(hook: str, middle: str) -> str:
    middle_clean = clean_outline(middle)
    if not middle_clean.startswith("- " + FIXED_DISCLAIMER):
        middle_block = f"- {FIXED_DISCLAIMER}\n{middle_clean}"
    else:
        middle_block = middle_clean
    final = f"""
🎬 DÀN Ý VIDEO (3–4 PHÚT)

1. Mở đầu (HOOK):
- {FIXED_INTRO}
- {hook}

2. Các phần nội dung:
{middle_block}

3. Kết luận:
- {FIXED_CLOSING}
- {FIXED_SIGNATURE}
""".strip()
    lines = [ln.rstrip() for ln in final.split("\n")]
    cleaned_lines = []
    prev_blank = False
    for ln in lines:
        if ln.strip() == "":
            if not prev_blank:
                cleaned_lines.append("")
            prev_blank = True
        else:
            cleaned_lines.append(ln.strip())
            prev_blank = False
    if cleaned_lines and cleaned_lines[0] == "":
        cleaned_lines = cleaned_lines[1:]
    if cleaned_lines and cleaned_lines[-1] == "":
        cleaned_lines = cleaned_lines[:-1]
    final_text = "\n".join(cleaned_lines)

    return final_text


# -----------------------------
# Top-level: build_full_outline
# -----------------------------
def build_full_outline(data: Dict[str, Any]) -> str:
    summary = (data.get("summary") or "").strip()
    claims = data.get("claims") or []
    entities = data.get("entities") or []

    # 1) strict rewrite (no new facts)
    claims = rewrite_all_claims_strict(claims)

    # 2) enrichment: expand short claims using safe templates
    claims = [expand_claim_safe(c) for c in claims]
    mode = detect_mode_from_claims(claims)

    # 3) optional summary enrichment
    if summary:
        summary = enrich_summary(summary)

    # fallback: few claims -> summary-based outline
    if len(claims) < 2 and summary:
        hook = generate_hook(summary, entities[0] if entities else "nhân vật")
        middle = generate_summary_based_outline(summary, entities)
        return assemble_final_output(hook, middle)

    if not claims and not summary:
        hook = f"Câu chuyện về {entities[0] if entities else 'nhân vật'} đang thu hút sự chú ý."
        middle = "Bối cảnh:\n- [Không đủ dữ liệu]\n\nDiễn biến chính:\n- [Không đủ dữ liệu]\n\nPhân tích / Tác động:\n- [Không đủ dữ liệu]"
        return assemble_final_output(hook, middle)

    # embed + cluster
    embeddings = embed_claims(claims) if claims else None
    if embeddings is None or getattr(embeddings, 'size', None) == 0 or len(embeddings) == 0:
        rough_groups = {0: claims}
    else:
        labels = cluster_claims(embeddings)
        rough_groups = group_by_label(claims, labels)

    # safe topic naming & mapping
    refined = refine_clusters_with_qwen(rough_groups)

    # balance topics (expand single-claim topics)
    refined = balance_topics(refined)

    # detect mode
    mode = detect_mode_from_claims(claims)

    # generate middle
    if mode == "explainer":
        middle = generate_outline_sections_explainer(refined)
    else:
        middle = generate_outline_sections_news(refined)

    # hook
    hook_src = summary if summary else " ".join(claims[:2])
    hook = generate_hook(hook_src, entities[0] if entities else "nhân vật")

    return assemble_final_output(hook, middle)
