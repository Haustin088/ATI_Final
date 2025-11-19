from fastapi import APIRouter
import psutil
import shutil
import os, json
from datetime import date

router = APIRouter(prefix="/system", tags=["System"])
BASE_DIR = os.path.dirname(__file__)
DATA_PATH = os.path.join(BASE_DIR, "..", "data", "crawled_articles.json")

@router.get("/status")
def get_system_status():
    cpu = psutil.cpu_percent(interval=0.5)
    memory = psutil.virtual_memory().percent
    total, used, _ = shutil.disk_usage(".")
    storage = used / total * 100

    # Check fake subsystem health
    database_ok = True
    api_ok = True
    queue_ok = True

    return {
        "cpu": cpu,
        "memory": memory,
        "storage": storage,
        "services": {
            "database": database_ok,
            "api": api_ok,
            "queue": queue_ok,
        }
    }

@router.get("/total")
def get_total_articles():
    """Return total number of crawled articles"""
    if not os.path.exists(DATA_PATH):
        return {"total": 0, "today": 0}

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    total = len(data)

    # count today
    today_str = date.today().isoformat()
    today_count = sum(1 for item in data if item.get("date", "").startswith(today_str))

    return {"total": total, "today": today_count}