from fastapi import APIRouter
import feedparser, os, json, hashlib, re, requests
from datetime import datetime
from readability import Document
from bs4 import BeautifulSoup
from fastapi import BackgroundTasks
from ..pipeline_universal import run_pipeline

router = APIRouter(prefix="/crawler", tags=["Crawler"])

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
RSS_FILE = os.path.join(DATA_DIR, "rss_sources.json")
ARTICLES_FILE = os.path.join(DATA_DIR, "crawled_articles.json")
LOG_FILE = os.path.join(DATA_DIR, "crawl_logs.json")

os.makedirs(DATA_DIR, exist_ok=True)
DEBUG_AUTH = True

def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_rss_sources():
    data = load_json(RSS_FILE, [])
    if not data:
        print("⚠️ No RSS sources found.")
        return []
    if all(isinstance(item, str) for item in data):
        return data
    elif all(isinstance(item, dict) and "url" in item for item in data):
        return [item["url"] for item in data]
    return []

def fetch_url_html(url, timeout=10):
    try:
        res = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
        res.raise_for_status()
        return res.text
    except Exception as e:
        if DEBUG_AUTH:
            print(f"⚠️ fetch_url_html failed for {url}: {e}")
        return None

def is_likely_person(name: str) -> bool:
    if not name:
        return False
    name = name.strip()
    words = name.split()
    if len(words) < 1 or len(words) > 5:
        return False
    if not all(re.match(r"^[A-ZĐÀ-Ỹ][a-zà-ỹ]+$", w) for w in words):
        return False
    if re.search(r"[\d:,%\-/]", name):
        return False
    return True

def extract_authors_from_html(html: str):
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    caption_keywords = re.compile(
        r"(Ảnh|Minh họa|Hình|Nguồn|Mô phỏng|Video|Biểu đồ|Đồ họa|Trung tâm|Bệnh viện)",
        re.IGNORECASE
    )
    doctor_prefix = re.compile(
        r"(BS\.?|BSCKI|BSCKII|BSCK|ThS\.?|TS\.?|PGS\.?|GS\.?)",
        re.IGNORECASE
    )

    # Step 1: Check bolded names first
    for tag in soup.select("p strong, p b"):
        text = tag.get_text(" ", strip=True)
        if not text:
            continue
        text = re.split(r"\s*\(", text, 1)[0].strip()
        if caption_keywords.search(text):
            continue
        if is_likely_person(text):
            return [text]

    # Step 2: Scan last few paragraphs for doctor-style lines
    paragraphs = soup.find_all("p")
    for p in reversed(paragraphs[-8:]):
        text = p.get_text(" ", strip=True)
        if not text or caption_keywords.search(text):
            continue
        if doctor_prefix.search(text):
            m = re.search(
                r'(?:BS\.?|BSCKI|BSCKII|ThS\.?|TS\.?|PGS\.?|GS\.?)\s*([A-ZĐ][a-zà-ỹ]+(?:\s+[A-ZĐ][a-zà-ỹ]+){0,4})',
                text
            )
            if m:
                name = m.group(1).strip()
                if is_likely_person(name):
                    return [name]
            break  # stop after doctor line

    # Step 3: "(Theo ...)" style at end
    tail_text = " ".join(
        p.get_text(" ", strip=True)
        for p in paragraphs[-8:]
        if not caption_keywords.search(p.get_text(" ", strip=True))
    )
    m = re.search(r'([A-ZĐ][a-zà-ỹ]+(?:\s+[A-ZĐ][a-zà-ỹ]+){0,4})\s*\(Theo', tail_text)
    if m and is_likely_person(m.group(1).strip()):
        return [m.group(1).strip()]

    return []

def extract_authors_from_entry(entry):
    names = []

    if entry.get("authors"):
        for a in entry.get("authors", []):
            if isinstance(a, dict):
                n = a.get("name") or a.get("email") or a.get("href")
                if n: names.append(n)
            elif isinstance(a, str):
                names.append(a)
    if not names and entry.get("author"):
        names.append(entry["author"])
    ad = entry.get("author_detail") or {}
    if not names and isinstance(ad, dict) and ad.get("name"):
        names.append(ad.get("name"))
    if not names and entry.get("contributors"):
        for c in entry.get("contributors", []):
            if isinstance(c, dict) and c.get("name"):
                names.append(c.get("name"))
            elif isinstance(c, str):
                names.append(c)
    for key in ("dc_creator", "creator"):
        if not names and entry.get(key) and isinstance(entry.get(key), str):
            names.append(entry.get(key))

    # normalize + dedupe
    cleaned = []
    for n in names:
        if n:
            n2 = re.sub(r"\s+", " ", n).strip()
            if n2 and n2 not in cleaned:
                cleaned.append(n2)

    final_cleaned = []
    for a in cleaned:
        a = re.split(r"\s*\(", a, 1)[0].strip()
        if is_likely_person(a) and a not in final_cleaned:
            final_cleaned.append(a)
    return final_cleaned

# ---------------- Parse Article Entry ----------------

def parse_entry(entry, source_url):
    url = entry.get("link", "") or entry.get("id", "") or entry.get("guid", "")
    authors = extract_authors_from_entry(entry)

    page_html = None
    content_text = ""

    if not authors or not entry.get("content"):
        page_html = fetch_url_html(url)
        if page_html:
            if not authors:
                authors = extract_authors_from_html(page_html)
            try:
                doc = Document(page_html)
                content_text = BeautifulSoup(doc.summary(), "html.parser").get_text(separator="\n", strip=True)
            except Exception:
                content_text = ""

    if not content_text:
        if entry.get("summary"):
            content_text = BeautifulSoup(entry.get("summary"), "html.parser").get_text(separator="\n", strip=True)
        elif entry.get("content"):
            cont = entry.get("content")
            if isinstance(cont, list):
                first = cont[0]
                if isinstance(first, dict):
                    content_text = BeautifulSoup(first.get("value", ""), "html.parser").get_text(separator="\n", strip=True)
            elif isinstance(cont, str):
                content_text = BeautifulSoup(cont, "html.parser").get_text(separator="\n", strip=True)

    if isinstance(authors, str):
        authors = [authors]
    if not authors:
        authors = []

    if DEBUG_AUTH:
        print("---- ENTRY DEBUG ----")
        print("title:", entry.get("title"))
        print("feed-authors:", extract_authors_from_entry(entry))
        print("scraped-authors:", extract_authors_from_html(page_html) if page_html else [])
        print("final-authors:", authors)
        print("---------------------")

    return {
        "id": hashlib.md5((url or "").encode()).hexdigest(),
        "source": source_url,
        "url": url,
        "title": entry.get("title", "") or entry.get("headline", ""),
        "authors": authors,
        "date": entry.get("published", entry.get("updated", datetime.now().isoformat())),
        "content": content_text
    }

# ---------------- Crawl All Feeds ----------------

def crawl_all_feeds():
    sources = load_rss_sources()
    if not sources:
        raise ValueError("No RSS sources found in rss_sources.json")

    existing_articles = load_json(ARTICLES_FILE, [])
    logs = load_json(LOG_FILE, [])
    existing_ids = {a["id"] for a in existing_articles}

    run_log = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "results": [],
        "total_new": 0
    }

    for url in sources:
        print(f"🔍 Crawling {url}...")
        feed = feedparser.parse(url)
        added, failed = 0, 0

        for entry in feed.entries:
            try:
                article = parse_entry(entry, url)
                if not article["url"] or article["id"] in existing_ids:
                    continue
                existing_ids.add(article["id"])
                existing_articles.append(article)
                added += 1
            except Exception as e:
                print(f"⚠️ Failed parsing entry: {e}")
                failed += 1

        run_log["results"].append({
            "source": url,
            "added": added,
            "failed": failed,
            "status": "success" if added > 0 else ("warning" if failed > 0 else "empty")
        })
        run_log["total_new"] += added

        print(f"✅ {added} new articles added from {url}")

    save_json(ARTICLES_FILE, existing_articles)
    logs.insert(0, run_log)
    save_json(LOG_FILE, logs[:100])

    print(f"💾 Total stored: {len(existing_articles)} articles")
    return run_log


@router.post("/run")
def run_crawler():
    try:
        result = crawl_all_feeds()
        return {
            "success": True,
            "message": f"Crawl completed successfully! {result.get('total_new', 0)} bài viết mới được thêm.",
            "log": result
        }
    except Exception as e:
        print(f"❌ [DEBUG] Exception during crawl:\n{e}")
        return {"success": False, "error": str(e)}

@router.get("/logs")
def get_logs():
    logs = load_json(LOG_FILE, [])
    return {"logs": logs}

@router.post("/run_pipeline")
def run_pipeline_api(background_tasks: BackgroundTasks):
    """
    Start pipeline in background (non-blocking response).
    It will still run in the same process; heavy scripts run as subprocesses.
    """
    # run synchronously here and return result immediately is also possible,
    # but non-blocking UX is usually better. We'll start it as background task.
    def _job():
        run_pipeline()

    background_tasks.add_task(_job)
    return {"success": True, "message": "Pipeline started. Check data/ for outputs."}