import os
import json
from datetime import datetime
import feedparser
import requests
from bs4 import BeautifulSoup

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
LOG_PATH = os.path.join(DATA_DIR, "crawl_logs.json")
os.makedirs(DATA_DIR, exist_ok=True)

def load_logs():
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_logs(logs):
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)

def clean_html(raw_html):
    """Remove HTML tags, scripts, etc."""
    soup = BeautifulSoup(raw_html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return " ".join(soup.get_text().split())

def crawl_from_rss(rss_links):
    results = []
    for url in rss_links:
        feed = feedparser.parse(url)
        success = 0
        fail = 0
        for entry in feed.entries:
            try:
                title = entry.get("title", "").strip()
                link = entry.get("link", "")
                summary = clean_html(entry.get("summary", ""))
                published = entry.get("published", None)
                author = entry.get("author", "")
                category = entry.get("category", "")

                # Extract full content if possible
                content = ""
                if link:
                    try:
                        html = requests.get(link, timeout=10).text
                        content = clean_html(html)
                    except Exception:
                        content = summary

                results.append({
                    "url": link,
                    "title": title,
                    "summary": summary,
                    "content": content,
                    "published": published,
                    "author": author,
                    "category": category,
                    "source": url
                })
                success += 1
            except Exception:
                fail += 1

        results.append({
            "source": url,
            "success": success,
            "fail": fail,
            "status": "success" if success > 0 else "error"
        })
    return results

def run_crawler():
    """Main crawl routine"""
    rss_path = os.path.join(DATA_DIR, "rss_links.json")
    if not os.path.exists(rss_path):
        raise FileNotFoundError("rss_links.json not found!")

    with open(rss_path, "r", encoding="utf-8") as f:
        rss_links = json.load(f)

    results = crawl_from_rss(rss_links)
    logs = load_logs()
    logs.insert(0, {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "results": results
    })
    save_logs(logs)

    return results

def get_stats():
    logs = load_logs()
    if not logs:
        return {"total": 0, "success": 0, "fail": 0, "success_rate": 0}

    latest = logs[0]["results"]
    success = sum(r.get("success", 0) for r in latest if isinstance(r, dict))
    fail = sum(r.get("fail", 0) for r in latest if isinstance(r, dict))
    total = success + fail
    rate = round(success / total * 100, 2) if total else 0
    return {"total": total, "success": success, "fail": fail, "success_rate": rate}
