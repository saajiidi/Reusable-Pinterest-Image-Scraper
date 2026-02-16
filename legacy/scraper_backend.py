#!/usr/bin/env python3
"""
Pinterest Image Scraper v4 - Backend Script
Web interface integration for the Pinterest scraper
"""

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import os
import sys
import json
import threading
import time
from datetime import datetime

# Import the scraper functions from the notebook
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
from urllib.parse import urlparse
import re
from PIL import Image
from io import BytesIO

app = Flask(__name__)
CORS(app)

# Global variables for progress tracking
current_progress = {
    'status': 'idle',
    'current': 0,
    'total': 0,
    'message': '',
    'percentage': 0,
    'downloaded_images': [],
    'error': None
}

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
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e:
        print(f"Error setting up Chrome driver: {e}")
        return None

def is_valid_image_url(url):
    """Check if URL points to a valid image."""
    if not url or not url.startswith('http'):
        return False
    
    skip_patterns = [
        'data:image',
        'placeholder',
        '1x1',
        'loading',
        'avatar',
        'profile'
    ]
    
    for pattern in skip_patterns:
        if pattern in url.lower():
            return False
    
    return True

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
            
            return True, f"Downloaded: {image_name} ({img.size})"
        else:
            return False, f"HTTP {response.status_code}"
    except Exception as e:
        return False, str(e)

def update_progress(current, total, message, error=None):
    """Update global progress state."""
    global current_progress
    current_progress.update({
        'current': current,
        'total': total,
        'message': message,
        'percentage': int((current / total) * 100) if total > 0 else 0,
        'error': error
    })

def pinterest_scraper_thread(query, num_images, save_folder, min_size):
    """Run the scraper in a separate thread."""
    global current_progress
    
    try:
        current_progress['status'] = 'running'
        current_progress['downloaded_images'] = []
        
        if not os.path.exists(save_folder):
            os.makedirs(save_folder)
        
        update_progress(0, num_images, "Setting up browser...")
        driver = setup_driver(headless=True)
        
        if not driver:
            update_progress(0, num_images, "Failed to setup browser", "Chrome driver not found")
            current_progress['status'] = 'error'
            return
        
        downloaded_count = 0
        processed_urls = set()
        
        try:
            update_progress(0, num_images, f"Searching for '{query}' on Pinterest...")
            search_url = f"https://www.pinterest.com/search/pins/?q={query.replace(' ', '%20')}"
            driver.get(search_url)
            
            time.sleep(3)
            
            scroll_attempts = 0
            max_scrolls = 10
            
            while downloaded_count < num_images and scroll_attempts < max_scrolls:
                images = driver.find_elements(By.TAG_NAME, "img")
                update_progress(downloaded_count, num_images, f"Found {len(images)} images, processing...")
                
                for img in images:
                    if downloaded_count >= num_images:
                        break
                        
                    try:
                        img_url = img.get_attribute("src")
                        if not is_valid_image_url(img_url) or img_url in processed_urls:
                            continue
                        
                        processed_urls.add(img_url)
                        
                        file_extension = "jpg"
                        if ".png" in img_url.lower():
                            file_extension = "png"
                        elif ".webp" in img_url.lower():
                            file_extension = "webp"
                        
                        image_name = f"{query.replace(' ', '_')}_{downloaded_count + 1}.{file_extension}"
                        
                        update_progress(downloaded_count, num_images, f"Downloading {image_name}...")
                        
                        success, message = download_image(img_url, save_folder, image_name, min_size)
                        if success:
                            downloaded_count += 1
                            current_progress['downloaded_images'].append({
                                'name': image_name,
                                'path': os.path.join(save_folder, image_name),
                                'url': img_url
                            })
                            update_progress(downloaded_count, num_images, f"Downloaded {downloaded_count}/{num_images} images")
                            
                    except Exception as e:
                        continue
                
                if downloaded_count < num_images:
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)
                    scroll_attempts += 1
            
            update_progress(downloaded_count, num_images, f"Download complete! {downloaded_count} images saved.")
            current_progress['status'] = 'completed'
            
        except Exception as e:
            update_progress(downloaded_count, num_images, f"Error during scraping: {str(e)}", str(e))
            current_progress['status'] = 'error'
        finally:
            driver.quit()
            
    except Exception as e:
        update_progress(0, num_images, f"Critical error: {str(e)}", str(e))
        current_progress['status'] = 'error'

@app.route('/')
def index():
    """Serve the main HTML page."""
    try:
        with open('index_v4.html', 'r') as f:
            return f.read()
    except FileNotFoundError:
        return "index_v4.html not found. Please ensure the file exists in the same directory.", 404

@app.route('/api/scrape', methods=['POST'])
def start_scrape():
    """Start the scraping process."""
    global current_progress
    
    if current_progress['status'] == 'running':
        return jsonify({'error': 'Scraping already in progress'}), 400
    
    data = request.get_json()
    
    query = data.get('searchQuery', '').strip()
    num_images = int(data.get('numImages', 10))
    folder_name = data.get('folderName', 'pinterest_downloads').strip()
    image_quality = data.get('imageQuality', '400x400')
    
    if not query:
        return jsonify({'error': 'Search query is required'}), 400
    
    if num_images < 1 or num_images > 100:
        return jsonify({'error': 'Number of images must be between 1 and 100'}), 400
    
    # Parse minimum image size
    min_size = tuple(map(int, image_quality.split('x')))
    
    # Reset progress
    current_progress = {
        'status': 'starting',
        'current': 0,
        'total': num_images,
        'message': 'Initializing...',
        'percentage': 0,
        'downloaded_images': [],
        'error': None
    }
    
    # Start scraping in a separate thread
    thread = threading.Thread(
        target=pinterest_scraper_thread,
        args=(query, num_images, folder_name, min_size)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({'message': 'Scraping started', 'status': 'started'})

@app.route('/api/progress', methods=['GET'])
def get_progress():
    """Get current scraping progress."""
    return jsonify(current_progress)

@app.route('/api/stop', methods=['POST'])
def stop_scrape():
    """Stop the current scraping process."""
    global current_progress
    current_progress['status'] = 'stopped'
    current_progress['message'] = 'Scraping stopped by user'
    return jsonify({'message': 'Scraping stopped'})

@app.route('/api/downloads', methods=['GET'])
def list_downloads():
    """List all downloaded images."""
    downloads_dir = 'pinterest_downloads'
    if not os.path.exists(downloads_dir):
        return jsonify({'images': []})
    
    images = []
    for filename in os.listdir(downloads_dir):
        if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
            images.append({
                'name': filename,
                'path': os.path.join(downloads_dir, filename),
                'size': os.path.getsize(os.path.join(downloads_dir, filename)),
                'modified': os.path.getmtime(os.path.join(downloads_dir, filename))
            })
    
    return jsonify({'images': images})

if __name__ == '__main__':
    print("Pinterest Image Scraper v4 - Backend Server")
    print("=" * 50)
    print("Starting Flask server...")
    print("Open http://localhost:5000 in your browser")
    print("Press Ctrl+C to stop the server")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
