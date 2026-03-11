import streamlit as st
import os
import re
import time
import json
import csv
import requests
import zipfile
import concurrent.futures
from datetime import datetime
from io import BytesIO, StringIO
from PIL import Image
try:
    import imagehash
    IMAGEHASH_AVAILABLE = True
except Exception:
    IMAGEHASH_AVAILABLE = False
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# Page configuration - Mobile optimized
st.set_page_config(
    page_title="Ultra Scraper Turbo",
    page_icon="S",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# PWA Support
st.markdown(
    """
<link rel="manifest" href="manifest.json">
<meta name="theme-color" content="#E60023">
<meta name="apple-mobile-web-app-capable" content="yes">
""",
    unsafe_allow_html=True,
)

# Custom CSS
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');

    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Outfit', sans-serif;
        background: linear-gradient(135deg, #fff5f5 0%, #fed7d7 100%);
        color: #1a202c;
    }

    .stMainBlockContainer {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(18px);
        border-radius: 32px;
        border: 1px solid rgba(255, 255, 255, 0.6);
        box-shadow: 0 20px 40px rgba(230, 0, 35, 0.12);
        padding: 1.5rem !important;
        margin-top: 1rem;
    }

    .main-title {
        font-size: 2.1rem;
        font-weight: 800;
        background: linear-gradient(to right, #E60023, #ff4d6d);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.2rem;
    }

    .status-badge {
        display: inline-block;
        padding: 2px 10px;
        background: #B0001B;
        color: white;
        border-radius: 10px;
        font-size: 0.7rem;
        font-weight: 700;
        vertical-align: middle;
        margin-left: 5px;
    }

    .stButton>button {
        width: 100%;
        background: linear-gradient(135deg, #E60023 0%, #ff4d6d 100%);
        color: white;
        border: none;
        border-radius: 18px;
        font-weight: 700;
        padding: 0.8rem;
        transition: all 0.25s ease;
    }

    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 20px rgba(230, 0, 35, 0.25);
        color: white;
    }

    [data-testid="stVerticalBlock"] > div:has(img) {
        background: white;
        padding: 8px;
        border-radius: 16px;
        border: 1px solid #fecaca;
        transition: all 0.25s;
    }

    .card {
        background: white;
        border: 1px solid #fde2e2;
        border-radius: 16px;
        padding: 12px 14px;
        margin: 8px 0 14px 0;
    }

    .muted {
        color: #4a5568;
        font-size: 0.9rem;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Constants
APP_DIR = os.path.join(os.path.expanduser("~"), ".ultra_scraper")
HISTORY_PATH = os.path.join(APP_DIR, "history.json")
META_PATH = os.path.join(APP_DIR, "last_metadata.json")
ERRORS_PATH = os.path.join(APP_DIR, "last_errors.txt")
URL_CACHE_PATH = os.path.join(APP_DIR, "url_cache.json")
THUMB_DIR = os.path.join(APP_DIR, "thumbnails")

# Helper functions
def ensure_app_dir():
    if not os.path.exists(APP_DIR):
        os.makedirs(APP_DIR, exist_ok=True)
    if not os.path.exists(THUMB_DIR):
        os.makedirs(THUMB_DIR, exist_ok=True)


def load_history():
    ensure_app_dir()
    if os.path.exists(HISTORY_PATH):
        try:
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_history(history):
    ensure_app_dir()
    try:
        with open(HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(history[:20], f, indent=2)
    except Exception:
        pass


def load_last_metadata():
    if os.path.exists(META_PATH):
        try:
            with open(META_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_last_metadata(metadata):
    ensure_app_dir()
    try:
        with open(META_PATH, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
    except Exception:
        pass


def save_errors(errors):
    ensure_app_dir()
    try:
        with open(ERRORS_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(errors))
    except Exception:
        pass


def load_url_cache():
    ensure_app_dir()
    if os.path.exists(URL_CACHE_PATH):
        try:
            with open(URL_CACHE_PATH, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()


def save_url_cache(urls):
    ensure_app_dir()
    try:
        with open(URL_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(sorted(list(urls)), f, indent=2)
    except Exception:
        pass


def clear_file(path):
    try:
        if os.path.exists(path):
            os.remove(path)
            return True
    except Exception:
        return False
    return False


def clear_folder(folder):
    try:
        if not os.path.exists(folder):
            return False, 0
        removed = 0
        for name in os.listdir(folder):
            p = os.path.join(folder, name)
            if os.path.isfile(p):
                os.remove(p)
                removed += 1
        return True, removed
    except Exception:
        return False, 0


def slugify(text):
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "query"


def resolve_high_res(url, source):
    """Bypasses blurred/sensitive thumbnails by resolving original high-res links."""
    if not url:
        return url
    try:
        if source == "Pinterest":
            if "/236x/" in url:
                return url.replace("/236x/", "/originals/")
            if "/736x/" in url:
                return url.replace("/736x/", "/originals/")
        if source == "Unsplash":
            if "?" in url:
                return url.split("?")[0]
        if source == "Pixabay":
            return url.replace("_340.", "_1280.")
        if source == "Imgur":
            return re.sub(r"([a-zA-Z0-9]{5,})[slmth]\.", r"\1.", url)
        if source == "DeviantArt":
            if "/f/" in url:
                return url.split("?")[0]
    except Exception:
        pass
    return url


def setup_driver(headless=True):
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    )

    paths = [
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/lib/chromium-browser/chromium-browser",
    ]
    for path in paths:
        if os.path.exists(path):
            chrome_options.binary_location = path
            break

    driver_path = "/usr/bin/chromedriver"
    if os.path.exists(driver_path):
        try:
            from selenium.webdriver.chrome.service import Service

            service = Service(driver_path)
            return webdriver.Chrome(service=service, options=chrome_options)
        except Exception:
            pass

    try:
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager

        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=chrome_options)
    except Exception:
        return None


def is_valid_image_url(url):
    if not url or not url.startswith("http"):
        return False
    skip = ["data:image", "1x1", "avatar", "profile", "icon", "loading"]
    return not any(p in url.lower() for p in skip)


def parse_srcset(srcset):
    if not srcset:
        return ""
    parts = [p.strip() for p in srcset.split(",") if p.strip()]
    if not parts:
        return ""
    best = parts[-1].split(" ")[0]
    return best


def extract_image_urls(driver, source):
    selectors = {
        "Pinterest": ["img[src*='pinimg.com']", "img[srcset*='pinimg.com']"],
        "Unsplash": ["img[src*='images.unsplash.com']", "img[srcset*='images.unsplash.com']"],
        "Pexels": ["img[src*='images.pexels.com']", "img[srcset*='images.pexels.com']"],
        "Pixabay": ["img[src*='cdn.pixabay.com']", "img[srcset*='cdn.pixabay.com']"],
        "Imgur": ["img[src*='i.imgur.com']", "img[srcset*='i.imgur.com']"],
        "DeviantArt": ["img[src*='wixmp.com']", "img[srcset*='wixmp.com']", "img[src*='deviantart']"],
    }
    urls = []
    fallback = ["img[src]", "img[srcset]"]
    for sel in selectors.get(source, fallback) + fallback:
        for img in driver.find_elements(By.CSS_SELECTOR, sel):
            try:
                src = img.get_attribute("src") or img.get_attribute("data-src")
                srcset = img.get_attribute("srcset")
                srcset_best = parse_srcset(srcset)
                for candidate in [srcset_best, src]:
                    if is_valid_image_url(candidate):
                        urls.append(candidate)
            except Exception:
                continue
    return urls


def extract_from_page_source(html, source):
    urls = []
    if not html:
        return urls
    if source == "Pinterest":
        urls.extend(re.findall(r"https://i\\.pinimg\\.com/originals/[^\"\\s]+", html))
    if source == "Unsplash":
        urls.extend(re.findall(r"https://images\\.unsplash\\.com/[^\"\\s]+", html))
    if source == "Pexels":
        urls.extend(re.findall(r"https://images\\.pexels\\.com/[^\"\\s]+", html))
    if source == "Pixabay":
        urls.extend(re.findall(r"https://cdn\\.pixabay\\.com/[^\"\\s]+", html))
    if source == "Imgur":
        urls.extend(re.findall(r"https://i\\.imgur\\.com/[^\"\\s]+", html))
    if source == "DeviantArt":
        urls.extend(re.findall(r"https://[^\"\\s]*wixmp\\.com/[^\"\\s]+", html))
    return urls


def request_with_retry(session, url, max_retries=3):
    last_error = None
    retries = 0
    for attempt in range(max_retries):
        try:
            response = session.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=(5, 12))
            if response.status_code in (429, 500, 502, 503, 504):
                retries += 1
                time.sleep(1.2 * (2 ** attempt))
                continue
            return response, retries
        except Exception as e:
            last_error = e
            retries += 1
            time.sleep(1.0 * (2 ** attempt))
    raise RuntimeError(f"{last_error}||retries={retries}")


def image_orientation(width, height):
    if width > height:
        return "Landscape"
    if height > width:
        return "Portrait"
    return "Square"


def thumb_path(original_path):
    base = os.path.basename(original_path)
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "_", base)
    return os.path.join(THUMB_DIR, f"thumb_{safe}")


def get_thumbnail(original_path, size=220):
    try:
        if not original_path or not os.path.exists(original_path):
            return original_path
        tpath = thumb_path(original_path)
        if os.path.exists(tpath):
            return tpath
        img = Image.open(original_path)
        img.thumbnail((size, size))
        img.save(tpath)
        return tpath
    except Exception:
        return original_path


def scroll_delay(source, mode):
    base = {
        "Pinterest": 1.8,
        "Unsplash": 1.2,
        "Pexels": 1.2,
        "Pixabay": 1.2,
        "Imgur": 1.4,
        "DeviantArt": 2.0,
    }.get(source, 1.4)
    if mode == "Gentle":
        return base * 1.6
    if mode == "Aggressive":
        return max(0.6, base * 0.7)
    return base


def fast_download(session, url, folder, name, min_size, min_bytes, allow_types, orientation, hash_list):
    try:
        response, retries = request_with_retry(session, url, max_retries=3)
        if response.status_code != 200:
            return None, "bad_status", retries
        if len(response.content) < min_bytes:
            return None, "too_small", retries

        img = Image.open(BytesIO(response.content))
        img.verify()
        img = Image.open(BytesIO(response.content))

        if img.size[0] < min_size[0] or img.size[1] < min_size[1]:
            return None, "low_res", retries
        if orientation != "Any" and image_orientation(img.size[0], img.size[1]) != orientation:
            return None, "wrong_orientation", retries

        img_format = (img.format or "JPEG").upper()
        ext = ".jpg" if img_format == "JPEG" else f".{img_format.lower()}"
        if img_format.lower() not in allow_types:
            return None, "type_filtered", retries

        phash = None
        if IMAGEHASH_AVAILABLE:
            phash = imagehash.phash(img)
            if any((phash - h) <= 5 for h in hash_list):
                return None, "perceptual_duplicate", retries
            hash_list.append(phash)
        path = os.path.join(folder, name + ext)
        with open(path, "wb") as f:
            f.write(response.content)

        meta = {
            "url": url,
            "format": img_format,
            "width": img.size[0],
            "height": img.size[1],
            "bytes": len(response.content),
            "hash": str(phash) if phash is not None else "",
            "path": path,
        }
        return meta, "ok", retries
    except Exception:
        return None, "error", 0


def create_zip(file_paths):
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in file_paths:
            if os.path.exists(p):
                z.write(p, os.path.basename(p))
    return buf.getvalue()


def metadata_to_csv(metadata):
    if not metadata:
        return ""
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=list(metadata[0].keys()))
    writer.writeheader()
    for row in metadata:
        writer.writerow(row)
    return output.getvalue()


def url_map(query, source):
    encoded = query.replace(" ", "%20")
    dashed = query.replace(" ", "-")
    return {
        "Pinterest": f"https://www.pinterest.com/search/pins/?q={encoded}",
        "Unsplash": f"https://unsplash.com/s/photos/{dashed}",
        "Pexels": f"https://www.pexels.com/search/{query}/",
        "Pixabay": f"https://pixabay.com/images/search/{query}/",
        "Imgur": f"https://imgur.com/search?q={encoded}",
        "DeviantArt": f"https://www.deviantart.com/search?q={encoded}",
    }[source]


# Session State
if "files" not in st.session_state:
    st.session_state.files = []
if "metadata" not in st.session_state:
    st.session_state.metadata = []
if "query" not in st.session_state:
    st.session_state.query = ""
if "history" not in st.session_state:
    st.session_state.history = load_history()
if "errors" not in st.session_state:
    st.session_state.errors = []
if "select_all" not in st.session_state:
    st.session_state.select_all = True
if "out_dir" not in st.session_state:
    st.session_state.out_dir = os.path.join(os.path.expanduser("~"), "Downloads", "UltraScraper")
if "last_stats" not in st.session_state:
    st.session_state.last_stats = {}

# Header
st.markdown(
    "<h1 class='main-title'>Ultra Scraper <span class='status-badge'>TURBO</span></h1>",
    unsafe_allow_html=True,
)
if not IMAGEHASH_AVAILABLE:
    st.warning("imagehash is not installed. Perceptual dedupe is disabled.")

st.markdown(
    """
    <div class="card">
        <strong>3 steps to scrape:</strong>
        <div class="muted">1) Choose sources  -  2) Enter your query  -  3) Set count + quality</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Performance Controls
with st.container():
    c1, c2, c3 = st.columns(3)
    with c1:
        turbo = st.checkbox("Turbo mode", value=True, help="Faster parallel downloads")
    with c2:
        preview = st.checkbox("Live preview", value=True)
    with c3:
        unlock = st.checkbox("Bypass blur", value=True, help="Resolve original high-res URLs")

# Config Section
with st.container():
    sources = st.multiselect(
        "Image sources",
        ["Pinterest", "Unsplash", "Pexels", "Pixabay", "Imgur", "DeviantArt"],
        default=["Pinterest"],
    )
    query = st.text_input(
        "Search query",
        value=st.session_state.query,
        placeholder="e.g. Romantic Aesthetic",
    )
    num = st.slider("Image count", 5, 200, 40)

# Quick Chips
q_chips = ["Romantic", "Dark Aesthetic", "Minimal", "Nature", "Space", "Lo-Fi"]
st.write("Hot topics")
cols = st.columns(6)
for i, c in enumerate(q_chips):
    if cols[i].button(c, key=f"q_{i}"):
        st.session_state.query = c
        st.rerun()

# Recent history
if st.session_state.history:
    st.write("Recent searches")
    h_cols = st.columns(4)
    for i, h in enumerate(st.session_state.history[:8]):
        if h_cols[i % 4].button(h, key=f"h_{i}"):
            st.session_state.query = h
            st.rerun()
else:
    st.markdown(
        """
        <div class="card">
            <strong>No recent searches.</strong>
            <div class="muted">Your recent queries will appear here.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Advanced
with st.expander("Advanced settings"):
    st.session_state.out_dir = st.text_input(
        "Download folder",
        value=st.session_state.out_dir,
        help="Where images will be saved",
    )
    quality = st.select_slider("Quality", ["Fast", "High", "Ultra"], value="High")
    min_res = (300, 300) if quality == "Fast" else (600, 600) if quality == "High" else (1000, 1000)
    min_bytes = st.slider("Minimum file size (KB)", 50, 2000, 120) * 1024
    orientation = st.selectbox("Orientation", ["Any", "Portrait", "Landscape", "Square"], index=0)
    allow_types = st.multiselect("Allowed file types", ["jpeg", "png", "webp"], default=["jpeg", "png", "webp"])
    resume_last = st.checkbox("Resume last run (skip already downloaded)", value=False)
    use_url_cache = st.checkbox("Use URL cache across sessions", value=True)
    rate_mode = st.selectbox("Rate limit", ["Normal", "Gentle", "Aggressive"], index=0)

    st.caption("High-res filtering + dedupe improves quality but can reduce total downloads.")

with st.expander("Maintenance"):
    m1, m2, m3 = st.columns(3)
    with m1:
        if st.button("Clear history"):
            if clear_file(HISTORY_PATH):
                st.session_state.history = []
                st.success("History cleared.")
            else:
                st.warning("History not found.")
    with m2:
        if st.button("Clear URL cache"):
            if clear_file(URL_CACHE_PATH):
                st.success("URL cache cleared.")
            else:
                st.warning("URL cache not found.")
    with m3:
        if st.button("Clear metadata"):
            if clear_file(META_PATH):
                st.success("Last metadata cleared.")
            else:
                st.warning("Metadata not found.")
    if st.button("Clear downloads folder"):
        ok, removed = clear_folder(st.session_state.out_dir)
        if ok:
            st.success(f"Removed {removed} files from downloads folder.")
        else:
            st.warning("Downloads folder not found.")
    if st.button("Clear thumbnail cache"):
        ok, removed = clear_folder(THUMB_DIR)
        if ok:
            st.success(f"Removed {removed} thumbnails.")
        else:
            st.warning("Thumbnail cache not found.")

# Run
run_disabled = (not query.strip()) or (not sources)
run_button = st.button("Start scraping", disabled=run_disabled)

if run_button:
    if not query.strip():
        st.warning("Enter a search query to continue.")
    elif not sources:
        st.warning("Select at least one source.")
    else:
        if query not in st.session_state.history:
            st.session_state.history.insert(0, query)
            save_history(st.session_state.history)

        if not os.path.exists(st.session_state.out_dir):
            os.makedirs(st.session_state.out_dir, exist_ok=True)

        st.session_state.files = []
        st.session_state.metadata = []
        st.session_state.errors = []

        status = st.status(f"Scraping {', '.join(sources)}...", expanded=True)
        driver = setup_driver()

        if driver:
            session = requests.Session()
            found = set()
            hash_list = []
            url_cache = load_url_cache() if use_url_cache else set()
            if url_cache:
                found.update(url_cache)

            if resume_last:
                prior = load_last_metadata()
                for item in prior:
                    url = item.get("url")
                    if url:
                        found.add(url)
                    hash_str = item.get("hash")
                    if hash_str and IMAGEHASH_AVAILABLE:
                        try:
                            hash_list.append(imagehash.hex_to_hash(hash_str))
                        except Exception:
                            pass
                st.session_state.metadata.extend(prior)
                st.session_state.files.extend(
                    [m.get("path") for m in prior if m.get("path") and os.path.exists(m.get("path"))]
                )

            downloaded = len([p for p in st.session_state.files if p])
            attempted = 0
            skipped = {
                "bad_status": 0,
                "too_small": 0,
                "low_res": 0,
                "wrong_orientation": 0,
                "type_filtered": 0,
                "perceptual_duplicate": 0,
                "error": 0,
            }
            retried = 0
            total_requests = 0
            run_started_at = time.time()

            try:
                prog = status.progress(0, text="Starting...")
                preview_area = st.empty() if preview else None

                for source in sources:
                    if downloaded >= num:
                        break

                    driver.get(url_map(query, source))
                    time.sleep(2)

                    max_scrolls = 40
                    for _ in range(max_scrolls):
                        if downloaded >= num:
                            break

                        batch_urls = []
                        for src in extract_image_urls(driver, source):
                            if unlock:
                                src = resolve_high_res(src, source)
                            if src not in found and is_valid_image_url(src):
                                found.add(src)
                                batch_urls.append(src)
                        page_urls = extract_from_page_source(driver.page_source, source)
                        for src in page_urls:
                            if unlock:
                                src = resolve_high_res(src, source)
                            if src not in found and is_valid_image_url(src):
                                found.add(src)
                                batch_urls.append(src)

                        if batch_urls:
                            max_workers = 8 if turbo else 1
                            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as exe:
                                future_map = {}
                                for i, u in enumerate(batch_urls):
                                    if downloaded + len(future_map) >= num:
                                        break
                                    name = f"{slugify(query)}_{source.lower()}_{int(time.time())}_{downloaded+len(future_map)}"
                                    future_map[exe.submit(
                                        fast_download,
                                        session,
                                        u,
                                        st.session_state.out_dir,
                                        name,
                                        min_res,
                                        min_bytes,
                                        [t.lower() for t in allow_types],
                                        orientation,
                                        hash_list,
                                    )] = u

                                for f in concurrent.futures.as_completed(future_map):
                                    attempted += 1
                                    meta, reason, retries = f.result()
                                    retried += retries
                                    total_requests += 1
                                    if meta:
                                        downloaded += 1
                                        meta.update(
                                            {
                                                "query": query,
                                                "source": source,
                                                "timestamp": datetime.utcnow().isoformat() + "Z",
                                            }
                                        )
                                        if use_url_cache and meta.get("url"):
                                            url_cache.add(meta.get("url"))
                                        st.session_state.files.append(meta.get("path"))
                                        st.session_state.metadata.append(meta)

                                        prog.progress(downloaded / num, text=f"Downloaded {downloaded}/{num}")
                                        if preview and meta.get("path"):
                                            with preview_area.container():
                                                st.image(get_thumbnail(meta.get("path")), width=160)
                                    else:
                                        skipped[reason] = skipped.get(reason, 0) + 1

                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(scroll_delay(source, rate_mode))

                status.update(
                    label=f"Completed: {downloaded} downloaded, {attempted - downloaded} skipped",
                    state="complete",
                )
                st.session_state.last_stats = {
                    "downloaded": downloaded,
                    "attempted": attempted,
                    "skipped": skipped,
                    "retried": retried,
                    "total_requests": total_requests,
                    "duration_sec": round(time.time() - run_started_at, 1),
                }

            except Exception as e:
                st.session_state.errors.append(str(e))
                status.update(label="Error during scraping", state="error")
                st.error(str(e))
            finally:
                driver.quit()

            save_last_metadata(st.session_state.metadata)
            if use_url_cache:
                save_url_cache(url_cache)
            if st.session_state.errors:
                save_errors(st.session_state.errors)
        else:
            st.error("ChromeDriver not available. Check your browser driver setup.")

# Results Summary
if st.session_state.metadata:
    st.subheader("Run summary")
    st.write(f"Downloaded: {len(st.session_state.files)}")
    st.write(f"Saved to: {st.session_state.out_dir}")
    if st.session_state.last_stats:
        st.write(f"Attempted: {st.session_state.last_stats.get('attempted', 0)}")
        st.write(f"Retries: {st.session_state.last_stats.get('retried', 0)}")
        st.write(f"Total requests: {st.session_state.last_stats.get('total_requests', 0)}")
        st.write(f"Duration (sec): {st.session_state.last_stats.get('duration_sec', 0)}")
        skipped = st.session_state.last_stats.get("skipped", {})
        if skipped:
            st.write("Skipped breakdown:")
            for k, v in skipped.items():
                st.write(f"- {k}: {v}")

        report = json.dumps(st.session_state.last_stats, indent=2)
        st.download_button("Download run report", report, "run_report.json", "application/json")

    meta_json = json.dumps(st.session_state.metadata, indent=2)
    meta_csv = metadata_to_csv(st.session_state.metadata)
    c1, c2 = st.columns(2)
    with c1:
        st.download_button("Download metadata (JSON)", meta_json, "metadata.json", "application/json")
    with c2:
        st.download_button("Download metadata (CSV)", meta_csv, "metadata.csv", "text/csv")

# Errors
if st.session_state.errors:
    st.subheader("Errors")
    st.text_area("Error log", "\n".join(st.session_state.errors), height=150)
    st.download_button("Download error log", "\n".join(st.session_state.errors), "errors.txt", "text/plain")

# Results Gallery
if st.session_state.files:
    st.divider()
    st.subheader(f"Collection ({len(st.session_state.files)})")

    gc1, gc2, gc3 = st.columns([3, 1, 1])
    with gc2:
        if st.button("Select all"):
            st.session_state.select_all = True
    with gc3:
        if st.button("Deselect all"):
            st.session_state.select_all = False

    cols = st.columns(2)
    sel = []
    for i, p in enumerate(st.session_state.files):
        with cols[i % 2]:
            st.image(get_thumbnail(p), use_container_width=True)
            if st.checkbox("Add", key=f"s_{p}", value=st.session_state.select_all, label_visibility="collapsed"):
                sel.append(p)

    if sel:
        z_data = create_zip(sel)
        st.download_button(
            f"Download {len(sel)} images",
            z_data,
            "scraped_assets.zip",
            "application/zip",
            use_container_width=True,
            type="primary",
        )
else:
    st.markdown(
        """
        <div class="card">
            <strong>No images yet.</strong>
            <div class="muted">Run a scrape to see results here.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
