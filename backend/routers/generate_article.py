import os, json
from fastapi import APIRouter
from pydantic import BaseModel

from ..generate_article import build_full_outline


router = APIRouter()

ROUTER_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(ROUTER_DIR)
DATA_DIR = os.path.join(BACKEND_DIR, "data")

MEDIA_FILE = os.path.join(DATA_DIR, "suggested_media_output.json")


# ==============================
# Data Models
# ==============================
class Cluster(BaseModel):
    group_id: int | None = None
    summary: str | None = None
    topic: str | None = None
    keywords: list[str] | None = None
    entities: list[str] | None = None
    claims: list[str] | None = None
    sources: list[str] | None = None
    videos: list[str] | None = None
    avg_reliability: float | None = None
    conflict: bool | None = None


class ScriptRequest(BaseModel):
    cluster: dict    # entire cluster dict
    outline: str     # base article text
    media: list      # media list (not needed but user provides it)
    format: str      # "1" / "2" / "3"


# ==============================
# /generate_article endpoint
# ==============================
@router.post("/generate_article")
def generate_article(cluster: Cluster):
    """
    Generates a full outline article using Qwen2.5-1.5B.
    """

    # Convert to dict so build_full_outline receives clean data
    cluster_dict = cluster.dict()

    # ---- Generate outline using the new Qwen-powered system ----
    outline = build_full_outline(cluster_dict)

    # ---- Load suggested media for the cluster ----
    media = []
    try:
        with open(MEDIA_FILE, "r", encoding="utf-8") as f:
            media_data = json.load(f)

        for item in media_data:
            if item.get("group_id") == cluster.group_id:
                media = item.get("media", [])
                break

    except Exception as e:
        print("⚠ Could not load media:", e)

    return {
        "article": outline,
        "media": media
    }


# ==============================
# /generate_script endpoint
# ==============================
@router.post("/generate_script")
def generate_script(req: ScriptRequest):
    """
    Formats a final script with columns based on template 1/2/3
    (Your ScriptGenerator stays the same)
    """
    from ..generate_script import ScriptGenerator
    script_gen = ScriptGenerator()

    cluster = req.cluster
    group_id = cluster.get("group_id")

    # ---- Retrieve matching media ----
    media = []
    try:
        with open(MEDIA_FILE, "r", encoding="utf-8") as f:
            media_data = json.load(f)
        for item in media_data:
            if item["group_id"] == group_id:
                media = item["media"]
                break
    except Exception as e:
        print("⚠ Could not load media:", e)

    # ---- Build base narrative ----
    title = cluster.get("summary", "Bản tin tổng hợp")
    category = cluster.get("topic", "Thời sự")

    try:
        fmt = int(req.format)
    except:
        fmt = 1

    outline = req.outline

    if fmt == 1:
        final_script = script_gen.make_one_column(title, category, outline)
    elif fmt == 2:
        final_script = script_gen.make_two_columns(title, category, outline)
    elif fmt == 3:
        final_script = script_gen.make_three_columns(title, category,   outline)
    else:
        final_script = script_gen.make_one_column(title, category, outline)
    return {"script": final_script}
