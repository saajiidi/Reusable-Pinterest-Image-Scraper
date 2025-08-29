#!/usr/bin/env python3
"""
Simple Pinterest Scraper Server - No external dependencies required
Uses only Python built-in modules for basic functionality
"""

import http.server
import socketserver
import json
import os
import urllib.parse
import threading
import time
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

PORT = 8000

class PinterestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.serve_index()
        elif self.path == '/api/progress':
            self.serve_progress()
        elif self.path.startswith('/api/'):
            self.send_json_response({'error': 'API endpoint not found'}, 404)
        else:
            super().do_GET()
    
    def do_POST(self):
        if self.path == '/api/scrape':
            self.handle_scrape()
        else:
            self.send_json_response({'error': 'Endpoint not found'}, 404)
    
    def serve_index(self):
        try:
            with open('index_v4.html', 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Update the JavaScript to use the correct API endpoints
            content = content.replace('http://localhost:5000', f'http://localhost:{PORT}')
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))
        except FileNotFoundError:
            self.send_response(404)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<h1>index_v4.html not found</h1>')
    
    def serve_progress(self):
        global current_progress
        self.send_json_response(current_progress)
    
    def handle_scrape(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
            query = data.get('searchQuery', '').strip()
            num_images = int(data.get('numImages', 10))
            folder_name = data.get('folderName', 'pinterest_downloads').strip()
            
            if not query:
                self.send_json_response({'error': 'Search query is required'}, 400)
                return
            
            if num_images < 1 or num_images > 100:
                self.send_json_response({'error': 'Number of images must be between 1 and 100'}, 400)
                return
            
            # Start scraping simulation in a separate thread
            thread = threading.Thread(
                target=simulate_scraping,
                args=(query, num_images, folder_name)
            )
            thread.daemon = True
            thread.start()
            
            self.send_json_response({'message': 'Scraping started', 'status': 'started'})
            
        except json.JSONDecodeError:
            self.send_json_response({'error': 'Invalid JSON data'}, 400)
        except Exception as e:
            self.send_json_response({'error': str(e)}, 500)
    
    def send_json_response(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

# Global progress tracking
current_progress = {
    'status': 'idle',
    'current': 0,
    'total': 0,
    'message': '',
    'percentage': 0,
    'downloaded_images': [],
    'error': None
}

def simulate_scraping(query, num_images, folder_name):
    """Simulate the scraping process for demonstration"""
    global current_progress
    
    try:
        current_progress.update({
            'status': 'running',
            'current': 0,
            'total': num_images,
            'message': 'Initializing scraper...',
            'percentage': 0,
            'downloaded_images': [],
            'error': None
        })
        
        # Create download folder
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
        
        # Simulate scraping steps
        steps = [
            'Setting up browser environment...',
            f'Navigating to Pinterest search for "{query}"...',
            'Loading search results...',
            'Analyzing image quality...',
            'Starting downloads...'
        ]
        
        for i, step in enumerate(steps):
            current_progress.update({
                'current': i,
                'total': len(steps) + num_images,
                'message': step,
                'percentage': int((i / (len(steps) + num_images)) * 100)
            })
            time.sleep(1)
        
        # Simulate downloading images
        for i in range(1, num_images + 1):
            current_progress.update({
                'current': len(steps) + i,
                'total': len(steps) + num_images,
                'message': f'Downloading image {i} of {num_images}...',
                'percentage': int(((len(steps) + i) / (len(steps) + num_images)) * 100)
            })
            
            # Create a placeholder file to simulate download
            filename = f"{query.replace(' ', '_')}_{i}.jpg"
            filepath = os.path.join(folder_name, filename)
            
            # Create a small placeholder file
            with open(filepath, 'w') as f:
                f.write(f"# Placeholder for {query} image {i}\n")
                f.write(f"# This is a simulation - actual scraping requires Selenium setup\n")
                f.write(f"# File created at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            current_progress['downloaded_images'].append({
                'name': filename,
                'path': filepath,
                'url': f'https://example.com/placeholder_{i}.jpg'
            })
            
            time.sleep(0.5)  # Simulate download time
        
        current_progress.update({
            'status': 'completed',
            'message': f'Successfully downloaded {num_images} images to {folder_name}/',
            'percentage': 100
        })
        
    except Exception as e:
        current_progress.update({
            'status': 'error',
            'error': str(e),
            'message': f'Error during scraping: {str(e)}'
        })

def main():
    print("Pinterest Image Scraper v4 - Simple Server")
    print("=" * 50)
    print(f"Starting server on port {PORT}...")
    print(f"Open http://localhost:{PORT} in your browser")
    print("Note: This is a simulation server for demonstration")
    print("For actual Pinterest scraping, install the full dependencies")
    print("Press Ctrl+C to stop the server")
    print("=" * 50)
    
    try:
        with socketserver.TCPServer(("", PORT), PinterestHandler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"Port {PORT} is already in use. Try a different port or stop the existing server.")
        else:
            print(f"Error starting server: {e}")

if __name__ == "__main__":
    main()
