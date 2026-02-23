import streamlit as st
import os
import time
import requests
import zipfile
import concurrent.futures
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image
from io import BytesIO

# Page configuration - Mobile optimized
st.set_page_config(
    page_title="Ultra Scraper Turbo",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# PWA Support
st.markdown("""
<link rel="manifest" href="manifest.json">
<meta name="theme-color" content="#E60023">
<meta name="apple-mobile-web-app-capable" content="yes">
""", unsafe_allow_html=True)

# Custom CSS for Ultimate Red Mobile UI
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Outfit', sans-serif;
        background: linear-gradient(135deg, #fff5f5 0%, #fed7d7 100%);
        color: #1a202c;
    }

    .stMainBlockContainer {
        background: rgba(255, 255, 255, 0.9);
        backdrop-filter: blur(20px);
        border-radius: 40px;
        border: 1px solid rgba(255, 255, 255, 0.5);
        box-shadow: 0 20px 40px rgba(230, 0, 35, 0.1);
        padding: 1.5rem !important;
        margin-top: 1rem;
    }

    .main-title {
        font-size: 2.2rem;
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
        background: #E60023;
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
        border-radius: 20px;
        font-weight: 600;
        padding: 0.8rem;
        transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }
    .stButton>button:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 20px rgba(230, 0, 35, 0.3);
        color: white;
    }

    [data-testid="stVerticalBlock"] > div:has(img) {
        background: white;
        padding: 8px;
        border-radius: 20px;
        border: 1px solid #fecaca;
        transition: all 0.3s;
    }

    .download-bar {
        position: fixed;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
        width: 92%;
        max-width: 500px;
        z-index: 1000;
        background: rgba(255, 255, 255, 0.98);
        padding: 12px;
        border-radius: 25px;
        border: 2px solid #E60023;
        box-shadow: 0 10px 30px rgba(230,0,35,0.2);
    }
</style>
""", unsafe_allow_html=True)

# Helper functions
def resolve_high_res(url, source):
    """Bypasses blurred/sensitive thumbnails by resolving original high-res links."""
    if not url: return url
    try:
        if source == "Pinterest":
            # Pinterest: thumbnails are usually in /236x/ or /736x/. Originals are in /originals/
            if '/236x/' in url: return url.replace('/236x/', '/originals/')
            if '/736x/' in url: return url.replace('/736x/', '/originals/')
        elif source == "Unsplash":
            if '?' in url: return url.split('?')[0]
        elif source == "Pixabay":
            return url.replace('_340.', '_1280.')
        elif source == "Imgur":
            # Imgur: Remove thumbnail suffix (m, l, t, s)
            import re
            return re.sub(r'([a-zA-Z0-9]{5,})[slmth]\.', r'\1.', url)
        elif source == "DeviantArt":
            # DeviantArt: Target original path
            if '/f/' in url: return url.split('?')[0]
    except: pass
    return url

def setup_driver(headless=True):
    chrome_options = Options()
    if headless: chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument("--log-level=3")
    # Add User-Agent to avoid some 'sensitive' gates
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
    
    try:
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except:
        return None

def is_valid_image_url(url):
    if not url or not url.startswith('http'): return False
    skip = ['data:image', '1x1', 'avatar', 'profile', 'icon', 'loading']
    return not any(p in url.lower() for p in skip)

def fast_download(url, folder, name, min_size):
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            if img.size[0] >= min_size[0] and img.size[1] >= min_size[1]:
                path = os.path.join(folder, name)
                with open(path, "wb") as f: f.write(response.content)
                return path
    except: pass
    return None

def create_zip(file_paths):
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in file_paths:
            if os.path.exists(p): z.write(p, os.path.basename(p))
    return buf.getvalue()

# Session State
if 'files' not in st.session_state: st.session_state.files = []
if 'query' not in st.session_state: st.session_state.query = ""
if 'history' not in st.session_state: st.session_state.history = []

# Header
st.markdown("<h1 class='main-title'>⚡ Ultra Scraper <span class='status-badge'>TURBO</span></h1>", unsafe_allow_html=True)

# Performance Controls
with st.container():
    c1, c2, c3 = st.columns(3)
    with c1: turbo = st.checkbox("🚀 Turbo", value=True)
    with c2: preview = st.checkbox("👁️ Live", value=True)
    with c3: unlock = st.checkbox("� Bypass", value=True, help="Force original high-res (Fixes Blur/Sensitive marks)")

# Config Section
with st.container():
    source = st.selectbox("🌐 Network", ["Pinterest", "Unsplash", "Pexels", "Pixabay", "Imgur", "DeviantArt"])
    query = st.text_input("🎯 Vision", value=st.session_state.query, placeholder="e.g. Romantic Aesthetic")
    num = st.slider("📸 Count", 5, 100, 20)

# Quick Chips
q_chips = ["Romantic", "Dark Aesthetic", "Minimal", "Nature", "Space", "Lo-Fi"]
st.write("🔥 **Hot Topics**")
cols = st.columns(6)
for i, c in enumerate(q_chips):
    if cols[i].button(c, key=f"q_{i}"):
        st.session_state.query = c
        st.rerun()

# Advanced
with st.expander("⚙️ Fine-Tune Parameters"):
    out_dir = os.path.join(os.path.expanduser("~"), "Downloads", "UltraScraper")
    quality = st.select_slider("Quality", ["Fast", "High", "Ultra"], value="High")
    min_res = (300,300) if quality=="Fast" else (600,600) if quality=="High" else (1000,1000)

# Scraping Engine
if st.button("🔥 IGNITE TURBO SCRAPE"):
    if not query: st.toast("⚠️ Need a vision!")
    else:
        if query not in st.session_state.history: st.session_state.history.insert(0, query)
        if not os.path.exists(out_dir): os.makedirs(out_dir)
        st.session_state.files = []
        
        status = st.status(f"🚀 Turbo-Scraping {source}...")
        driver = setup_driver()
        
        if driver:
            try:
                urls = {
                    "Pinterest": f"https://www.pinterest.com/search/pins/?q={query.replace(' ', '%20')}",
                    "Unsplash": f"https://unsplash.com/s/photos/{query.replace(' ', '-')}",
                    "Pexels": f"https://www.pexels.com/search/{query}/",
                    "Pixabay": f"https://pixabay.com/images/search/{query}/",
                    "Imgur": f"https://imgur.com/search?q={query.replace(' ', '%20')}",
                    "DeviantArt": f"https://www.deviantart.com/search?q={query.replace(' ', '%20')}"
                }
                driver.get(urls[source])
                time.sleep(2)
                
                found = set()
                downloaded = 0
                max_scrols = 40
                
                prog = status.progress(0, text="Establishing high-speed feed...")
                preview_area = st.empty() if preview else None
                
                for scroll in range(max_scrols):
                    if downloaded >= num: break
                    images = driver.find_elements(By.TAG_NAME, "img")
                    batch_urls = []
                    
                    for img in images:
                        try:
                            src = img.get_attribute("src") or img.get_attribute("data-src")
                            if is_valid_image_url(src):
                                # Fix blurred/sensitive content by resolving original URL
                                if unlock: src = resolve_high_res(src, source)
                                
                                if src not in found:
                                    found.add(src)
                                    batch_urls.append(src)
                        except: continue
                    
                    if batch_urls:
                        with concurrent.futures.ThreadPoolExecutor(max_workers=8 if turbo else 1) as exe:
                            futures = []
                            for i, u in enumerate(batch_urls):
                                if downloaded + len(futures) >= num: break
                                name = f"{source}_{int(time.time())}_{downloaded+len(futures)}.jpg"
                                futures.append(exe.submit(fast_download, u, out_dir, name, min_res))
                            
                            for f in concurrent.futures.as_completed(futures):
                                res = f.result()
                                if res:
                                    downloaded += 1
                                    st.session_state.files.append(res)
                                    prog.progress(downloaded/num, text=f"Captured {downloaded}/{num} pins")
                                    if preview:
                                        with preview_area.container():
                                            st.image(res, width=150)

                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1.5)
                
                status.update(label=f"🎯 {downloaded} assets captured!", state="complete")
                
            except Exception as e:
                status.update(label="❌ Error", state="error")
                st.error(str(e))
            finally: driver.quit()

# Results Gallery
if st.session_state.files:
    st.divider()
    st.subheader(f"📦 Collection ({len(st.session_state.files)})")
    
    gc1, gc2 = st.columns([3, 1])
    with gc2:
        if st.button("🗑️ Clear"):
            st.session_state.files = []
            st.rerun()
    
    cols = st.columns(2)
    sel = []
    for i, p in enumerate(st.session_state.files):
        with cols[i%2]:
            st.image(p, use_container_width=True)
            if st.checkbox("Add", key=f"s_{p}", value=True, label_visibility="collapsed"):
                sel.append(p)
    
    if sel:
        st.markdown('<div style="height:80px;"></div>', unsafe_allow_html=True)
        z_data = create_zip(sel)
        st.download_button(f"⬇️ DOWNLOAD {len(sel)} IMAGES", z_data, "Scraped_Assets.zip", "application/zip", use_container_width=True, type="primary")
