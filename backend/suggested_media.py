import os, re, uuid, base64, requests, cv2, yt_dlp, torch, json
from bs4 import BeautifulSoup
from PIL import Image
from transformers import (
    BlipProcessor,
    BlipForConditionalGeneration,
    MarianMTModel,
    MarianTokenizer
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(TEMP_DIR, exist_ok=True)

device = "cuda" if torch.cuda.is_available() else "cpu"

blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-large")
blip_model = BlipForConditionalGeneration.from_pretrained(
    "Salesforce/blip-image-captioning-large"
).to(device)

trans_model_name = "Helsinki-NLP/opus-mt-en-vi"
trans_tokenizer = MarianTokenizer.from_pretrained(trans_model_name)
trans_model = MarianMTModel.from_pretrained(trans_model_name).to(device)


# ============================================================
# 🔧 HELPERS
# ============================================================
def load_grouped_claims():
    path = os.path.join(TEMP_DIR, "claims_grouped_summary.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("JSON load error:", e)
        return []

def safe_remove(path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except:
        pass


def to_data_url(image_path):
    """Convert image file → Base64 data URL."""
    try:
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return f"data:image/jpeg;base64,{b64}"
    except:
        return None


def clean_caption(text: str):
    """Remove repeated consecutive tokens like 'cục cục cục'."""
    words = text.split()
    cleaned = []
    for w in words:
        if not cleaned or cleaned[-1] != w:
            cleaned.append(w)
    return " ".join(cleaned)


# ============================================================
# 🧠 TRANSLATION + CAPTIONING
# ============================================================
def translate_en_to_vi(text: str):
    try:
        tokens = trans_tokenizer([text], return_tensors="pt", padding=True).to(device)
        output = trans_model.generate(**tokens, max_new_tokens=60)
        out = trans_tokenizer.decode(output[0], skip_special_tokens=True)
        return clean_caption(out.strip())
    except:
        return text


def caption_vn(path: str):
    """Caption a local image → Vietnamese description."""
    try:
        image = Image.open(path).convert("RGB")
        inputs = blip_processor(image, return_tensors="pt").to(device)

        with torch.no_grad():
            out = blip_model.generate(**inputs, max_new_tokens=40, num_beams=4)

        caption_en = blip_processor.tokenizer.decode(out[0], skip_special_tokens=True)
        caption_en = clean_caption(caption_en)

        caption_vi = translate_en_to_vi(caption_en)
        return caption_vi
    except:
        return ""


# ============================================================
# 📰 ARTICLE IMAGE EXTRACTION
# ============================================================
def extract_images_from_article(url, max_images=1):
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")

        images, seen = [], set()

        def add(src):
            if not src:
                return

            src = src.strip()

            if src.startswith("//"):
                src = "https:" + src
            elif src.startswith("/"):
                from urllib.parse import urljoin
                src = urljoin(url, src)

            low = src.lower()
            if any(bad in low for bad in ["logo", "icon", "avatar", "sprite", ".gif", ".svg"]):
                return

            if any(ext in low for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                if src not in seen:
                    seen.add(src)
                    images.append(src)

        # Parse HTML tags
        for img in soup.find_all("img"):
            add(img.get("src"))
            add(img.get("data-src"))
            add(img.get("data-original"))

        for source in soup.find_all("source"):
            srcset = source.get("srcset")
            if srcset:
                first = srcset.split(",")[0].split()[0]
                add(first)

        return images[:max_images]

    except:
        return []


# ============================================================
# 🎥 VIDEO FRAME EXTRACTION
# ============================================================
def extract_frame(video_url, second):
    try:
        uid = uuid.uuid4().hex[:8]
        tmp_video = os.path.join(TEMP_DIR, f"vid_{uid}.mp4")
        out_img = os.path.join(TEMP_DIR, f"frame_{uid}.jpg")

        ydl_opts = {
            "outtmpl": tmp_video,
            "quiet": True,
            "format": "best[height<=720]"
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
        except:
            safe_remove(tmp_video)
            return None

        cap = cv2.VideoCapture(tmp_video)
        if not cap.isOpened():
            safe_remove(tmp_video)
            return None

        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(fps * second))
        ret, frame = cap.read()
        cap.release()
        safe_remove(tmp_video)

        if not ret:
            return None

        cv2.imwrite(out_img, frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return out_img

    except:
        return None


def extract_three_frames(video_url):
    frames = []
    for s in (5, 15, 25):
        f = extract_frame(video_url, s)
        if f:
            frames.append(f)
    return frames


# ============================================================
# 🎁 MAIN FUNCTION — RETURN MEDIA LIST
# ============================================================
def _ensure_list(x):
    if x is None:
        return []
    if isinstance(x, str):
        return [x]
    return list(x)


def generate_suggested_media(cluster: dict):
    article_urls = _ensure_list(cluster.get("sources"))
    video_urls = _ensure_list(cluster.get("videos"))

    collected = []

    for url in article_urls:
        for img in extract_images_from_article(url, max_images=2):
            collected.append({"type": "remote", "value": img, "origin": url})

    for v in video_urls:
        for f in extract_three_frames(v):
            collected.append({"type": "local_frame", "value": f, "origin": v})

    results = []

    for item in collected:
        itype = item["type"]
        origin = item["origin"]
        path = item["value"]

        if itype == "remote":
            try:
                r = requests.get(path, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
                if r.status_code != 200:
                    continue

                tmp = os.path.join(TEMP_DIR, uuid.uuid4().hex[:8] + ".jpg")
                with open(tmp, "wb") as f:
                    f.write(r.content)

                caption = caption_vn(tmp)
                data_url = to_data_url(tmp)
                safe_remove(tmp)

                results.append({
                    "path": data_url or path,
                    "caption": caption,
                    "source": origin
                })

            except:
                continue

        elif itype == "local_frame":
            caption = caption_vn(path)
            data_url = to_data_url(path)
            safe_remove(path)

            results.append({
                "path": data_url or path,
                "caption": caption,
                "source": origin
            })

    return results

def generate_media_all_groups():
    json_path = os.path.join(TEMP_DIR, "claims_grouped_summary.json")

    # Load JSON list
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            groups = json.load(f)
    except Exception as e:
        print("ERROR: Cannot read", json_path, e)
        return []

    results = []

    # Loop through each group in the JSON file
    for group in groups:
        group_id = group.get("group_id")
        print(f"Processing group {group_id}...")

        media = generate_suggested_media(group)

        results.append({
            "group_id": group_id,
            "media": media
        })

    return results

if __name__ == "__main__":
    output = generate_media_all_groups()
    print(json.dumps(output, ensure_ascii=False, indent=2))
