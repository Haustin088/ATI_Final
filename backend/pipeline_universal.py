# backend/pipeline_universal.py

import os
import json
import subprocess
import time
import sys
from datetime import datetime

# ---------------------------
# DIRECTORY STRUCTURE
# ---------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))     # backend/
DATA_DIR = os.path.join(BASE_DIR, "data")

# Script paths
SPLIT_SCRIPT       = os.path.join(BASE_DIR, "split_sentence.py")
EXTRACT_SCRIPT     = os.path.join(BASE_DIR, "claim_extraction.py")
ENRICH_SCRIPT      = os.path.join(BASE_DIR, "claims_enrich.py")
SYNTHESIS_SCRIPT   = os.path.join(BASE_DIR, "synthesis_claims.py")
SUGGESTED_MEDIA    = os.path.join(BASE_DIR, "suggested_media.py")

CRAWLED_ARTICLES   = os.path.join(DATA_DIR, "crawled_articles.json")
MEDIA_FILE         = os.path.join(DATA_DIR, "media_suggestions.json")
SENTENCES_FILE     = os.path.join(DATA_DIR, "crawled_sentences.json")

# Import crawler
try:
    from routers.crawl import crawl_all_feeds
except Exception as e:
    crawl_all_feeds = None
    _crawl_error = str(e)


# --------------------------------
# Helpers
# --------------------------------
def load_json(path, default=None):
    if not os.path.exists(path): 
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def run_subprocess(script_path, timeout=None):
    """Run a python script in a separate process."""
    try:
        start = time.time()
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True, text=True, timeout=timeout
        )
        return {
            "ok": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "elapsed": time.time() - start
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# --------------------------------
# Suggested Media (direct import)
# --------------------------------
def generate_media_per_article(max_media=2):
    try:
        from suggested_media import generate_suggested_media
    except Exception as e:
        return {"ok": False, "error": f"Cannot import suggested_media: {e}"}

    articles = load_json(CRAWLED_ARTICLES, [])
    results = {}

    for art in articles:
        aid = art.get("id")
        url = art.get("url")
        if not aid or not url:
            continue

        cluster_obj = {"sources": [url], "videos": []}
        try:
            media = generate_suggested_media(cluster_obj)
            results[aid] = media[:max_media]
        except:
            results[aid] = []

    save_json(MEDIA_FILE, results)
    return {"ok": True, "count": len(results)}


# --------------------------------
# MAIN PIPELINE
# --------------------------------
def run_pipeline():
    log = {"start": datetime.now().isoformat(), "steps": []}

    # Step 1: Crawl
    if crawl_all_feeds is None:
        log["steps"].append({
            "step": "crawl",
            "ok": False,
            "error": _crawl_error
        })
        return {"ok": False, "log": log}

    try:
        crawl_out = crawl_all_feeds()
        log["steps"].append({"step": "crawl", "ok": True, "result": crawl_out})
    except Exception as e:
        log["steps"].append({"step": "crawl", "ok": False, "error": str(e)})
        return {"ok": False, "log": log}

    # Step 2: Suggested Media
    try:
        media_out = generate_media_per_article()
        log["steps"].append({"step": "suggested_media", **media_out})
    except Exception as e:
        log["steps"].append({"step": "suggested_media", "ok": False, "error": str(e)})

    # Step 3: Split sentences
    try:
        from split_sentence import process_crawled_articles
        process_crawled_articles()
        log["steps"].append({"step": "split_sentences", "ok": True})
    except Exception as e:
        log["steps"].append({"step": "split_sentences", "ok": False, "error": str(e)})
        return {"ok": False, "log": log}

    # Step 4: Claim extraction
    extract_out = run_subprocess(EXTRACT_SCRIPT, timeout=3600)
    log["steps"].append({"step": "claim_extraction", **extract_out})
    if not extract_out.get("ok"):
        return {"ok": False, "log": log}

    # Step 5: Enrich claims
    enrich_out = run_subprocess(ENRICH_SCRIPT, timeout=3600)
    log["steps"].append({"step": "claims_enrich", **enrich_out})
    if not enrich_out.get("ok"):
        return {"ok": False, "log": log}

    # Step 6: Synthesis
    synth_out = run_subprocess(SYNTHESIS_SCRIPT, timeout=3600)
    log["steps"].append({"step": "synthesis", **synth_out})
    if not synth_out.get("ok"):
        return {"ok": False, "log": log}

    # Load final results
    grouped_file = os.path.join(DATA_DIR, "claims_grouped_summary.json")
    groups = load_json(grouped_file, [])

    log["finish"] = datetime.now().isoformat()
    log["groups"] = len(groups)
    log["output_files"] = {
        "crawled_articles": CRAWLED_ARTICLES,
        "media": MEDIA_FILE,
        "sentences": SENTENCES_FILE,
        "claims_enriched": os.path.join(DATA_DIR, "claims_enriched.json"),
        "synthesis": grouped_file
    }

    return {"ok": True, "log": log}


if __name__ == "__main__":
    print(json.dumps(run_pipeline(), ensure_ascii=False, indent=2))
