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

# Page configuration
st.set_page_config(
    page_title="Pinterest Scraper v5",
    page_icon="📌",
    layout="wide"
)

# Custom CSS for styling
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
        background-color: #E60023;
        color: white;
        border: none;
        border-radius: 24px;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #ad081b;
        color: white;
    }
    .download-card {
        border: 1px solid #e1e1e1;
        border-radius: 12px;
        padding: 10px;
        margin-bottom: 10px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# Main App Layout
st.title("📌 Pinterest Image Scraper v5")
st.markdown("Download high-quality images from Pinterest with ease.")

# Initialize session state for downloaded files
if 'downloaded_files' not in st.session_state:
    st.session_state.downloaded_files = []

# Helper functions (adapted from v4)
def setup_driver(headless=True):
    """Set up Chrome WebDriver with optimized options."""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    chrome_options.add_argument("--log-level=3")  # Suppress logs
    
    try:
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except Exception as e:
        st.error(f"Error setting up Chrome driver: {str(e)}")
        return None

def is_valid_image_url(url):
    """Check if URL points to a valid image."""
    if not url or not url.startswith('http'):
        return False
    
    skip_patterns = ['data:image', 'placeholder', '1x1', 'loading', 'avatar', 'profile']
    return not any(pattern in url.lower() for pattern in skip_patterns)

def download_image(url, folder_name, image_name, min_size=(200, 200)):
    """Download an image with quality checks."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            try:
                img = Image.open(BytesIO(response.content))
                if img.size[0] < min_size[0] or img.size[1] < min_size[1]:
                    return False, f"Image too small ({img.size})"
            except Exception:
                return False, "Invalid image format"
            
            file_path = os.path.join(folder_name, image_name)
            with open(file_path, "wb") as file:
                file.write(response.content)
            
            return True, file_path
        return False, f"HTTP {response.status_code}"
    except Exception as e:
        return False, str(e)

def create_zip(file_paths):
    """Create a zip file from a list of file paths."""
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for file_path in file_paths:
            if os.path.exists(file_path):
                zip_file.write(file_path, os.path.basename(file_path))
    return zip_buffer.getvalue()

# Sidebar controls
with st.sidebar:
    st.header("Configuration")
    query = st.text_input("Search Query", placeholder="e.g., Cyberpunk City")
    num_images = st.slider("Number of Images", 1, 100, 10)
    folder_name = st.text_input("Download Folder", value="pinterest_downloads")
    
    quality_options = {"Standard (200x200)": (200, 200), "High (400x400)": (400, 400), "HD (800x600)": (800, 600)}
    quality_label = st.selectbox("Minimum Image Quality", list(quality_options.keys()))
    min_size = quality_options[quality_label]
    
    headless_mode = st.checkbox("Headless Mode (Hidden Browser)", value=True)

# Main content area
if st.button("Start Scraping"):
    if not query:
        st.warning("Please enter a search query.")
    else:
        # Create folder
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
        
        # Reset previous downloads in session state
        st.session_state.downloaded_files = []
        
        # Initialize status containers
        status_text = st.empty()
        progress_bar = st.progress(0)
        
        status_text.info(f"Initializing scraper for '{query}'...")
        
        driver = setup_driver(headless=headless_mode)
        
        if driver:
            try:
                # Search
                search_url = f"https://www.pinterest.com/search/pins/?q={query.replace(' ', '%20')}"
                driver.get(search_url)
                status_text.info("Searching Pinterest...")
                time.sleep(3)  # Wait for load
                
                downloaded_count = 0
                processed_urls = set()
                scroll_attempts = 0
                max_scrolls = 20
                
                # Scraping Loop
                while downloaded_count < num_images and scroll_attempts < max_scrolls:
                    images = driver.find_elements(By.TAG_NAME, "img")
                    status_text.info(f"Found {len(images)} images on page. Processing...")
                    
                    for img in images:
                        if downloaded_count >= num_images:
                            break
                            
                        try:
                            img_url = img.get_attribute("src")
                            if not img_url or not is_valid_image_url(img_url) or img_url in processed_urls:
                                continue
                            
                            processed_urls.add(img_url)
                            
                            # Determine extension
                            ext = "jpg"
                            if ".png" in img_url: ext = "png"
                            elif ".webp" in img_url: ext = "webp"
                            
                            filename = f"{query.replace(' ', '_')}_{downloaded_count + 1}.{ext}"
                            
                            success, result = download_image(img_url, folder_name, filename, min_size)
                            
                            if success:
                                downloaded_count += 1
                                st.session_state.downloaded_files.append(result)
                                # Update progress
                                progress = downloaded_count / num_images
                                progress_bar.progress(progress)
                                status_text.success(f"Downloaded {downloaded_count}/{num_images}: {filename}")
                            
                        except Exception as e:
                            continue
                            
                    # Scroll if needed
                    if downloaded_count < num_images:
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(2)
                        scroll_attempts += 1
                        
                if downloaded_count >= num_images:
                    st.success(f"✅ Successfully downloaded {downloaded_count} images!")
                else:
                    st.warning(f"⚠️ Stopped after downloading {downloaded_count} images (couldn't find more).")
                            
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
            finally:
                driver.quit()

# Display Results and Download Options
if st.session_state.downloaded_files:
    st.markdown("---")
    st.subheader("Downloaded Images")
    
    # Selection Form
    # Selection Form
    with st.form("selection_form"):
        st.write("Select images to download:")
        
        cols = st.columns(4)
        selected_images = []
        
        # Display images in grid with checkboxes
        for idx, file_path in enumerate(st.session_state.downloaded_files):
            col = cols[idx % 4]
            with col:
                try:
                    image = Image.open(file_path)
                    st.image(image, use_column_width=True)
                    # Use unique key for each checkbox
                    if st.checkbox(f"Select {os.path.basename(file_path)}", key=f"select_{file_path}", value=True):
                        selected_images.append(file_path)
                except:
                    st.error(f"Error loading {os.path.basename(file_path)}")

        submitted = st.form_submit_button("Prepare Download")
        
    if submitted:
        if selected_images:
            zip_data = create_zip(selected_images)
            st.session_state['prepared_zip'] = zip_data
            st.success(f"Ready to download {len(selected_images)} images!")
        else:
            st.session_state['prepared_zip'] = None
            st.warning("No images selected.")

    if st.session_state.get('prepared_zip'):
        st.download_button(
            label="⬇️ Download Selected Images (ZIP)",
            data=st.session_state['prepared_zip'],
            file_name="pinterest_images.zip",
            mime="application/zip"
        )

# Instructions
st.markdown("---")
with st.expander("How to use"):
    st.markdown("""
    1. Enter a search term (e.g., 'Cats', 'Modern Architecture').
    2. Select how many images you want.
    3. (Optional) Adjust quality and folder name.
    4. Click **Start Scraping**.
    5. Once finished, you can select specific images and download them as a ZIP file.
    """)
