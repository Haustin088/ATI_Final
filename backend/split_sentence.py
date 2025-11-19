import os
import json
import re
import textwrap

DATA_DIR = "data"
INPUT_FILE = os.path.join(DATA_DIR, "crawled_articles.json")
OUTPUT_FILE = os.path.join(DATA_DIR, "crawled_sentences.json")

def normalize_text(text: str):
    if not text:
        return ""
    text = textwrap.dedent(text)
    text = re.sub(r"\s*\n\s*", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(
        r"\b(Ảnh minh họa|Ảnh|Nguồn|Theo)\b[: ]*[^.!?]*",
        "",
        text,
        flags=re.IGNORECASE
    )
    text = re.sub(r"\b[A-Z]{2,}\b", "", text)
    protect = {
        " USD.": " USD<eos>",
        " VND.": " VND<eos>",
        " đồng.": " đồng<eos>"
    }
    for k, v in protect.items():
        text = text.replace(k, v)
    text = re.sub(r"(\d+\/\d+)\.", r"\1<eos>", text)
    text = re.sub(r",\s*\.", ".", text)
    text = re.sub(r"\.\s*\.", ".", text)
    text = re.sub(r"\(\s*\)", "", text)
    text = re.sub(r"\(\s*[^A-Za-zÀ-ỹ0-9]+\s*\)", "", text)
    text = re.sub(r"\(\s*[0-9\/\.]+\s*\)", "", text)
    text = re.sub(r"\(\s*\)", "", text)
    text = re.sub(r"\s{2,}", " ", text)

    return text.strip()

def split_vietnamese_sentences(content: str):
    text = normalize_text(content)
    raw = re.split(r'(?<=[.!?])\s+(?=["“A-ZÀ-Ỹ0-9])', text)

    sentences = []
    for s in raw:
        s = s.strip()
        if not s:
            continue
        s = s.replace("<eos>", ".")
        s = re.sub(r",\s*\.", ".", s)
        s = re.sub(r"\.\s*\.", ".", s)
        if s in {".", "..", "..."}:
            continue
        sentences.append(s)

    merged = []
    buf = None

    for s in sentences:
        if buf is None:
            buf = s
            continue

        open_quotes = (buf.count('"') % 2 == 1) or (buf.count("“") % 2 == 1)

        looks_like_new = re.match(r'^["“]?[A-ZÀ-Ỹ0-9]', s) is not None

        if open_quotes and not looks_like_new:
            buf += " " + s
        else:
            merged.append(buf)
            buf = s

    if buf:
        merged.append(buf)

    final = []
    for s in merged:
        if len(s.split()) >= 9:
            final.append(s)

    return final

def process_crawled_articles():
    if not os.path.exists(INPUT_FILE):
        raise FileNotFoundError(f"Missing: {INPUT_FILE}")

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        articles = json.load(f)

    output = []

    for art in articles:
        article_id = art.get("id")
        content = art.get("content", "")

        if not article_id:
            continue

        sentences = split_vietnamese_sentences(content)

        output.append({
            "id": article_id,
            "sentences": sentences
        })

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✔ Cleaned sentences saved → {OUTPUT_FILE}")
    print(f"✔ Total articles processed: {len(output)}")

if __name__ == "__main__":
    process_crawled_articles()
