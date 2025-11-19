from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from urllib.parse import urlparse
import feedparser
import os, json

router = APIRouter(prefix="/rss", tags=["RSS"])

# --- Path setup ---
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # backend/
DATA_PATH = os.path.join(BASE_DIR, "data")
RSS_FILE = os.path.join(DATA_PATH, "rss_sources.json")

# --- Ensure file exists ---
os.makedirs(DATA_PATH, exist_ok=True)
if not os.path.exists(RSS_FILE):
    with open(RSS_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)

# --- Helpers ---
def load_rss():
    with open(RSS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_rss(data):
    with open(RSS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# --- Request schema ---
class RSSItem(BaseModel):
    url: str

# --- Routes ---
@router.get("/list")
def get_rss_list():
    return {"rss": load_rss()}

class RSSRequest(BaseModel):
    url: str

@router.post("/add")
async def add_rss(req: RSSRequest):
    # Step 1: Try parsing the RSS
    feed = feedparser.parse(req.url)

    # Step 2: Check if it's a valid feed
    if not feed.entries or feed.bozo:  # bozo=True = parsing error
        raise HTTPException(status_code=400, detail="Liên kết không phải RSS hợp lệ.")

    # Step 3: Load current list
    if os.path.exists(RSS_FILE):
        with open(RSS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = []

    # Step 4: Prevent duplicate
    if any(item["url"] == req.url for item in data):
        raise HTTPException(status_code=400, detail="RSS này đã tồn tại.")

    # Step 5: Save valid feed
    source = feed.feed.get("link", req.url).split("/")[2]  # extract domain
    data.append({"url": req.url, "source": source})

    with open(RSS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return {"message": f"Đã thêm RSS từ {source}"}

class RSSDeleteRequest(BaseModel):
    url: str

@router.delete("/delete")
async def delete_rss(req: RSSDeleteRequest):
    if not os.path.exists(RSS_FILE):
        raise HTTPException(status_code=404, detail="RSS storage file not found")

    # Load existing data
    with open(RSS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Check if URL exists
    existing_count = len(data)
    data = [item for item in data if item["url"] != req.url]

    if len(data) == existing_count:
        raise HTTPException(status_code=404, detail="RSS link not found")

    # Save back the updated list
    with open(RSS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return {"message": f"Deleted {req.url}"}
