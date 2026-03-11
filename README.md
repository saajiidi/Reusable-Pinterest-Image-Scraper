# Pinterest Image Scraper (Streamlit)

A reusable, multi-source image scraper with a modern Streamlit UI. Scrape images from Pinterest and other sources with quality filters, live preview, and exportable metadata.

## Features

- Multi-source scraping: Pinterest, Unsplash, Pexels, Pixabay, Imgur, DeviantArt
- Quality filters: minimum resolution, file size, orientation, and file type
- Perceptual dedupe to avoid near-duplicates
- Live preview + progress tracking
- Export metadata to JSON/CSV
- Resume last run (skip already downloaded)
- URL cache for cross-session dedupe
- Maintenance tools to clear history/cache/metadata
- Run report export with retries and duration
- Per-site rate limiting (Gentle/Normal/Aggressive)
- Thumbnail cache for faster galleries
- Clear downloads folder from the UI
- One-click ZIP download of selected images

## Project Structure

- `streamlit_app.py` - Main Streamlit app
- `manifest.json` - PWA metadata
- `requirements.txt` - Python dependencies
- `packages.txt` - System packages (for hosted environments)

## Requirements

- Python 3.8+
- Chrome/Chromium browser + ChromeDriver
- Internet connection

## Installation

```bash
pip install -r requirements.txt
```

## Run

```bash
streamlit run streamlit_app.py
```

## Usage

1. Select one or more sources.
2. Enter a search query and choose image count.
3. Tune quality filters if needed, then click **Start scraping**.
4. Download the ZIP or export metadata.

## Notes

- Respect each site's terms of service and robots.txt.
- Use responsibly and avoid excessive scraping.
- Images may be copyrighted; use only as permitted.
