# Pinterest Image Scraper v4

A powerful and reusable Pinterest image scraper with both command-line and web interfaces. Built with Python, Selenium, and Flask for enhanced functionality and user experience.

## 🚀 Features

- **Enhanced Image Quality Detection**: Automatically filters out low-quality and placeholder images
- **Modern Web Interface**: Beautiful, responsive UI with real-time progress tracking
- **Multiple Image Formats**: Supports JPG, PNG, and WebP formats
- **Smart Filtering**: Skips duplicate and invalid images
- **Progress Tracking**: Real-time download progress with detailed status updates
- **Flexible Configuration**: Customizable image quality, folder names, and download limits
- **Error Handling**: Robust error handling with detailed logging

## 📁 Project Structure

- `Pinterst-Scrapping-v4.ipynb` - Enhanced Jupyter notebook with improved scraping functionality
- `index_v4.html` - Modern web interface for Pinterest scraping
- `scraper_backend.py` - Flask backend server for web interface integration
- `requirements.txt` - Python dependencies
- `pinterest_downloads/` - Default download folder for images

## 🛠️ Installation

1. Clone the repository:
```bash
git clone https://github.com/your-username/Reusable-Pinterest-Image-Scraper.git
cd Reusable-Pinterest-Image-Scraper
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install Chrome WebDriver:
   - Download ChromeDriver from https://chromedriver.chromium.org/
   - Add ChromeDriver to your system PATH

## 🎯 Usage

### Web Interface (Recommended)

1. Start the Flask server:
```bash
python scraper_backend.py
```

2. Open your browser and go to `http://localhost:5000`

3. Enter your search query, number of images, and preferences

4. Click "Start Scraping" and watch the real-time progress

### Jupyter Notebook

1. Open `Pinterst-Scrapping-v4.ipynb` in Jupyter
2. Run the cells to execute the scraper
3. Follow the interactive prompts

### Command Line

```python
from scraper_backend import pinterest_image_search_v4

# Download 20 nature images
pinterest_image_search_v4("nature landscapes", num_images=20, save_folder="nature_images")
```

## ⚙️ Configuration Options

- **Search Query**: Any Pinterest search term
- **Number of Images**: 1-100 images per session
- **Download Folder**: Custom folder name for saving images
- **Image Quality**: Minimum image size (200x200 to 800x800)
- **Headless Mode**: Run browser in background (default: True)

## 📋 Requirements

- Python 3.7+
- Chrome/Chromium browser
- ChromeDriver
- Internet connection

## 🔧 Dependencies

- selenium==4.15.0
- requests==2.31.0
- Pillow==10.0.1
- flask==2.3.3
- flask-cors==4.0.0
- webdriver-manager==4.0.1

## 🚨 Important Notes

- Respect Pinterest's terms of service and robots.txt
- Use responsibly and avoid excessive scraping
- Images are downloaded for personal use only
- Some images may be protected by copyright

## 🆕 Version History

- **v4**: Modern web interface, enhanced image quality detection, Flask backend
- **v2**: Basic Selenium implementation with download functionality
- **v1**: Initial version with basic scraping
- **v0**: Prototype version
