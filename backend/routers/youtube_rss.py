from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from urllib.parse import urlparse
import os, json

router = APIRouter(prefix="/youtube", tags=["YouTube"])

# ---- Path setup ----
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # backend/
DATA_PATH = os.path.join(BASE_DIR, "data")
YOUTUBE_FILE = os.path.join(DATA_PATH, "youtube_sources.json")

# ---- Ensure storage exists ----
os.makedirs(DATA_PATH, exist_ok=True)
if not os.path.exists(YOUTUBE_FILE):
    with open(YOUTUBE_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)

# ---- Helpers ----
def load_data():
    with open(YOUTUBE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(YOUTUBE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ---- Models ----
class YoutubeItem(BaseModel):
    name: str
    url: str

class YoutubeDelete(BaseModel):
    url: str

# ---- Routes ----
@router.get("/list")
def list_youtube():
    return {"youtube": load_data()}

@router.post("/add")
async def add_youtube(req: YoutubeItem):
    data = load_data()

    # prevent duplicate
    if any(item["url"] == req.url for item in data):
        raise HTTPException(status_code=400, detail="Kênh này đã tồn tại.")

    # extract domain (youtube.com, youtu.be, etc)
    parsed = urlparse(req.url)
    domain = parsed.netloc or "unknown"

    data.append({
        "name": req.name,
        "url": req.url,
        "domain": domain
    })

    save_data(data)
    return {"message": "Đã thêm kênh YouTube."}

@router.delete("/delete")
async def delete_youtube(req: YoutubeDelete):
    data = load_data()
    before = len(data)

    data = [item for item in data if item["url"] != req.url]

    if len(data) == before:
        raise HTTPException(status_code=404, detail="Không tìm thấy kênh.")

    save_data(data)
    return {"message": "Đã xóa kênh YouTube."}
