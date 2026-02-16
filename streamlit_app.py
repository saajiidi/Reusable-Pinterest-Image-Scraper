import streamlit as st
import os
import time
import requests
import zipfile
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from PIL import Image
from io import BytesIO

# Page configuration - Mobile optimized
st.set_page_config(
    page_title="Pinterest Scraper",
    page_icon="📌",
    layout="centered", # Centered is often better for mobile focus than 'wide'
    initial_sidebar_state="collapsed"
)

# Custom CSS for Mobile & Clean UI
st.markdown("""
<style>
    /* Clean up default Streamlit padding */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Modern Button Styling */
    .stButton>button {
        width: 100%;
        background-color: #E60023;
        color: white;
        border: none;
        border-radius: 24px;
        font-weight: 600;
        padding: 0.5rem 1rem;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        background-color: #ad081b;
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* Hide default menu and footer for cleaner app look */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Improve image gallery spacing */
    div[data-testid="column"] {
        background-color: #f9f9f9;
        border-radius: 8px;
        padding: 5px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Helper functions
def setup_driver(headless=True):
    chrome_options = Options()
    if headless:
        chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument("--log-level=3")
    
    try:
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except Exception as e:
        st.error(f"Driver Error: {str(e)}")
        return None

def is_valid_image_url(url):
    if not url or not url.startswith('http'): return False
    skip = ['data:image', 'placeholder', '1x1', 'loading', 'avatar', 'profile']
    return not any(p in url.lower() for p in skip)

def download_image(url, folder_name, image_name, min_size=(200, 200)):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            if img.size[0] < min_size[0] or img.size[1] < min_size[1]:
                return False, None
            
            file_path = os.path.join(folder_name, image_name)
            with open(file_path, "wb") as file:
                file.write(response.content)
            return True, file_path
        return False, None
    except:
        return False, None

def create_zip(file_paths):
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for file_path in file_paths:
            if os.path.exists(file_path):
                zip_file.write(file_path, os.path.basename(file_path))
    return zip_buffer.getvalue()

# Session State
if 'downloaded_files' not in st.session_state:
    st.session_state.downloaded_files = []
if 'scraping_active' not in st.session_state:
    st.session_state.scraping_active = False

# Header
st.title("📌 Pinterest Scraper")

# Config Section (Clean & Minimal)
with st.container():
    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("Search", placeholder="Search topics...", label_visibility="collapsed")
    with col2:
        num_images = st.number_input("Count", min_value=1, max_value=50, value=10, label_visibility="collapsed")

# Advanced Options (Hidden by default to reduce noise)
with st.expander("⚙️ Settings"):
    # smart default: Users/Downloads/Pinterest_Images
    default_path = os.path.join(os.path.expanduser("~"), "Downloads", "Pinterest_Images")
    folder_name = st.text_input("Save Location", value=default_path)
    
    quality = st.select_slider("Quality", options=["Low", "Medium", "High"], value="Medium")
    min_size = (200, 200) if quality == "Low" else (400, 400) if quality == "Medium" else (800, 600)

# Action Button
if st.button("🔍 Find Images"):
    if not query:
        st.toast("⚠️ Please enter a search topic")
    else:
        if not os.path.exists(folder_name): os.makedirs(folder_name)
        st.session_state.downloaded_files = []
        
        status = st.status("Starting scraper...", expanded=True)
        driver = setup_driver(headless=True)
        
        if driver:
            try:
                search_url = f"https://www.pinterest.com/search/pins/?q={query.replace(' ', '%20')}"
                driver.get(search_url)
                time.sleep(2)
                
                downloaded = 0
                processed = set()
                scrolls = 0
                
                progress_bar = status.progress(0, text="Searching...")
                
                while downloaded < num_images and scrolls < 15:
                    images = driver.find_elements(By.TAG_NAME, "img")
                    
                    for img in images:
                        if downloaded >= num_images: break
                        try:
                            src = img.get_attribute("src")
                            if not src or src in processed or not is_valid_image_url(src): continue
                            
                            processed.add(src)
                            ext = "png" if ".png" in src else "jpg"
                            fname = f"{query.replace(' ', '_')}_{downloaded+1}.{ext}"
                            
                            success, path = download_image(src, folder_name, fname, min_size)
                            if success:
                                downloaded += 1
                                st.session_state.downloaded_files.append(path)
                                progress_bar.progress(downloaded/num_images, text=f"Found: {fname}")
                        except: continue
                    
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1)
                    scrolls += 1
                
                status.update(label=f"✅ Complete! Found {downloaded} images", state="complete", expanded=False)
                
            except Exception as e:
                status.update(label="❌ Error occurred", state="error")
                st.error(str(e))
            finally:
                driver.quit()

# Results Gallery
if st.session_state.downloaded_files:
    st.divider()
    
    # Selection Form
    with st.form("gallery_form"):
        st.caption("Select images to include in ZIP")
        
        # Responsive Grid
        cols = st.columns(2) # 2 columns is better for mobile than 4
        selected = []
        
        for idx, path in enumerate(st.session_state.downloaded_files):
            with cols[idx % 2]:
                st.image(path, use_column_width=True)
                if st.checkbox("Select", key=f"sel_{path}", value=True, label_visibility="collapsed"):
                    selected.append(path)
        
        st.markdown("")
        if st.form_submit_button("📦 Prepare ZIP"):
            if selected:
                zip_data = create_zip(selected)
                st.session_state['ready_zip'] = zip_data
            else:
                st.toast("⚠️ No images selected")

    # Download Button (Outside Form)
    if 'ready_zip' in st.session_state:
        st.download_button(
            label="⬇️ Download ZIP",
            data=st.session_state['ready_zip'],
            file_name="images.zip",
            mime="application/zip",
            type="primary"
        )
