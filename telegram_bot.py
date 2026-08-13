import os
import time
import json
import threading
import requests
from typing import Callable, Optional, List, Dict, Any

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(BASE_DIR, ".scraper_data")
TELEGRAM_CONFIG_PATH = os.path.join(BASE_DIR, "telegram_config.json")

SOURCE_SYNONYMS = {
    "pinterest": "Pinterest",
    "unsplash": "Unsplash",
    "pexels": "Pexels",
    "pixabay": "Pixabay",
    "imgur": "Imgur",
    "deviantart": "DeviantArt",
    "flickr": "Flickr",
    "wallhaven": "Wallhaven",
    "wikimedia": "Wikimedia Commons",
    "commons": "Wikimedia Commons",
}

def ensure_app_dir():
    if not os.path.exists(APP_DIR):
        os.makedirs(APP_DIR, exist_ok=True)

def load_telegram_config() -> dict:
    ensure_app_dir()
    config = {"token": "", "allowed_chat_ids": [], "enabled": False}
    if os.path.exists(TELEGRAM_CONFIG_PATH):
        try:
            with open(TELEGRAM_CONFIG_PATH, "r", encoding="utf-8") as f:
                config.update(json.load(f))
        except Exception:
            pass

    # Fallback to Streamlit Secrets (for Streamlit Community Cloud)
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "telegram" in st.secrets:
            sec = st.secrets["telegram"]
            if not config.get("token") and "token" in sec:
                config["token"] = str(sec["token"]).strip()
            if not config.get("allowed_chat_ids") and "allowed_chat_ids" in sec:
                config["allowed_chat_ids"] = list(sec["allowed_chat_ids"])
            if "enabled" in sec and not config.get("enabled"):
                config["enabled"] = bool(sec["enabled"])
    except Exception:
        pass

    return config

def save_telegram_config(config: dict):
    ensure_app_dir()
    try:
        with open(TELEGRAM_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        try:
            os.chmod(TELEGRAM_CONFIG_PATH, 0o600)
        except Exception:
            pass
    except Exception:
        pass

class TelegramBotManager:
    def __init__(self, scraper_runner: Optional[Callable] = None):
        self.config = load_telegram_config()
        self.scraper_runner = scraper_runner
        self.is_running = False
        self.poll_thread: Optional[threading.Thread] = None
        self.last_update_id = 0
        self.logs: List[str] = []
        self.bot_info: Dict[str, Any] = {}
        self.current_job_cancel = False
        self.active_jobs_count = 0
        self.lock = threading.Lock()

    def log(self, message: str):
        timestamp = time.strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        with self.lock:
            self.logs.append(entry)
            if len(self.logs) > 50:
                self.logs.pop(0)

    def get_api_url(self, method: str) -> str:
        token = self.config.get("token", "").strip()
        return f"https://api.telegram.org/bot{token}/{method}"

    @staticmethod
    def get_me() -> dict:
        token = load_telegram_config().get("token", "").strip()
        if not token:
            return {"ok": False, "error": "No token configured"}
        try:
            resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=8)
            return resp.json()
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def send_message(self, chat_id: int, text: str, parse_mode: Optional[str] = "Markdown") -> bool:
        url = self.get_api_url("sendMessage")
        payload = {"chat_id": chat_id, "text": text}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        try:
            resp = requests.post(url, json=payload, timeout=10)
            data = resp.json()
            if not data.get("ok", False) and parse_mode:
                # Fallback to plain text if markdown formatting failed
                payload.pop("parse_mode", None)
                resp = requests.post(url, json=payload, timeout=10)
                return resp.json().get("ok", False)
            return data.get("ok", False)
        except Exception as e:
            self.log(f"Failed to send message: {e}")
            return False

    def send_photo(self, chat_id: int, photo_path: str, caption: str = "") -> bool:
        if not os.path.exists(photo_path):
            return False
        url = self.get_api_url("sendPhoto")
        try:
            with open(photo_path, "rb") as f:
                files = {"photo": f}
                data = {"chat_id": chat_id, "caption": caption}
                resp = requests.post(url, data=data, files=files, timeout=20)
                return resp.json().get("ok", False)
        except Exception as e:
            self.log(f"Failed to send photo {photo_path}: {e}")
            return False

    def send_media_group(self, chat_id: int, photo_paths: List[str], caption: str = "") -> bool:
        valid_paths = [p for p in photo_paths if os.path.exists(p)][:10]
        if not valid_paths:
            return False
        if len(valid_paths) == 1:
            return self.send_photo(chat_id, valid_paths[0], caption)

        url = self.get_api_url("sendMediaGroup")
        files = {}
        media = []
        file_handles = []

        try:
            for idx, path in enumerate(valid_paths):
                fh = open(path, "rb")
                file_handles.append(fh)
                field_name = f"photo_{idx}"
                files[field_name] = fh
                item = {"type": "photo", "media": f"attach://{field_name}"}
                if idx == 0 and caption:
                    item["caption"] = caption
                media.append(item)

            data = {"chat_id": chat_id, "media": json.dumps(media)}
            resp = requests.post(url, data=data, files=files, timeout=30)
            return resp.json().get("ok", False)
        except Exception as e:
            self.log(f"Failed to send media group: {e}")
            return False
        finally:
            for fh in file_handles:
                try:
                    fh.close()
                except Exception:
                    pass

    def send_document(self, chat_id: int, file_path: str, caption: str = "") -> bool:
        if not os.path.exists(file_path):
            return False
        url = self.get_api_url("sendDocument")
        try:
            with open(file_path, "rb") as f:
                files = {"document": f}
                data = {"chat_id": chat_id, "caption": caption}
                resp = requests.post(url, data=data, files=files, timeout=40)
                return resp.json().get("ok", False)
        except Exception as e:
            self.log(f"Failed to send document {file_path}: {e}")
            return False

    def is_chat_allowed(self, chat_id: int) -> bool:
        allowed = self.config.get("allowed_chat_ids", [])
        if not allowed:
            return True  # If empty, default to open access
        return chat_id in allowed or str(chat_id) in [str(c) for c in allowed]

    def start(self) -> bool:
        with self.lock:
            if self.is_running:
                return True

            token = self.config.get("token", "").strip()
            if not token:
                self.log("Cannot start: Telegram bot token is missing.")
                return False

            info = TelegramBotManager.get_me()
            if not info.get("ok"):
                self.log(f"Cannot start: Invalid bot token ({info.get('error')}).")
                return False

            self.bot_info = info.get("result", {})
            self.is_running = True
            self.config["enabled"] = True
            save_telegram_config(self.config)

            self.poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
            self.poll_thread.start()
            self.log(f"Bot started as @{self.bot_info.get('username')}")
            return True

    def stop(self):
        with self.lock:
            self.is_running = False
            self.config["enabled"] = False
            save_telegram_config(self.config)
            self.log("Bot daemon stopping...")

    def _poll_loop(self):
        url = self.get_api_url("getUpdates")
        while self.is_running:
            try:
                params = {"offset": self.last_update_id + 1, "timeout": 12}
                resp = requests.get(url, params=params, timeout=16)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("ok"):
                        for update in data.get("result", []):
                            self.last_update_id = update["update_id"]
                            self._handle_update(update)
                time.sleep(1)
            except Exception as e:
                self.log(f"Polling error: {e}")
                time.sleep(3)

    def _handle_update(self, update: dict):
        message = update.get("message")
        if not message:
            return

        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "").strip()
        if not chat_id or not text:
            return

        if not self.is_chat_allowed(chat_id):
            self.log(f"Unauthorized access attempt from chat_id {chat_id}")
            self.send_message(chat_id, "❌ *Unauthorized access.* Your Chat ID is not allowed.")
            return

        self.log(f"Received command from {chat_id}: {text}")

        if text.startswith("/start") or text.startswith("/help"):
            help_text = (
                "🤖 *Ultra Scraper Bot Command Guide*\n\n"
                "• `/scrape <query> [count] [source]` - Scrape images & receive media/ZIP\n"
                "  _Example:_ `/scrape romantic aesthetic 10 Pinterest` \n"
                "  _Example:_ `/scrape dark cyberpunk 15 Unsplash` \n\n"
                "• `/status` - Check server status & download stats\n"
                "• `/cancel` - Cancel active scraping job\n"
                "• `/sources` - List supported image sources\n"
                "• `/help` - Show this message"
            )
            self.send_message(chat_id, help_text)

        elif text.startswith("/sources"):
            sources_text = (
                "🌐 *Supported Image Sources*\n\n"
                "1. Pinterest\n2. Unsplash\n3. Pexels\n4. Pixabay\n"
                "5. Imgur\n6. DeviantArt\n7. Flickr\n8. Wallhaven\n9. Wikimedia Commons"
            )
            self.send_message(chat_id, sources_text)

        elif text.startswith("/status"):
            job_status = f"🔄 Scraping in progress ({self.active_jobs_count} active)" if self.active_jobs_count > 0 else "Idle"
            status_text = (
                f"🟢 *Bot Status*: Active\n"
                f"🤖 *Bot Handle*: @{self.bot_info.get('username', 'Bot')}\n"
                f"⚡ *Workload*: {job_status}\n"
                f"📂 *Config*: `telegram_config.json`"
            )
            self.send_message(chat_id, status_text)

        elif text.startswith("/cancel"):
            self.current_job_cancel = True
            self.log(f"Cancel signal triggered by chat {chat_id}")
            self.send_message(chat_id, "🛑 Cancelling active job...")

        elif text.startswith("/scrape"):
            raw = text[len("/scrape"):].strip()
            tokens = raw.split()
            if not tokens:
                self.send_message(chat_id, "⚠️ Usage: `/scrape <query> [count] [source]`\nExample: `/scrape Cyberpunk 10 Pinterest`")
                return

            count = 10
            source_choice = ["Pinterest"]
            query_tokens = []

            for token in tokens:
                t_lower = token.lower()
                if token.isdigit() and len(query_tokens) > 0:
                    val = int(token)
                    if 1 <= val <= 100:
                        count = max(1, min(val, 50))
                        continue
                if t_lower in SOURCE_SYNONYMS:
                    source_choice = [SOURCE_SYNONYMS[t_lower]]
                    continue
                query_tokens.append(token)

            query = " ".join(query_tokens).strip()
            if not query:
                query = raw

            # Launch scrape worker in a separate thread so polling loop is never blocked
            worker = threading.Thread(
                target=self._run_scrape_command,
                args=(chat_id, query, count, source_choice),
                daemon=True,
            )
            worker.start()

    def _run_scrape_command(self, chat_id: int, query: str, count: int, sources: List[str]):
        if not self.scraper_runner:
            self.send_message(chat_id, "⚠️ Scraper backend is not linked.")
            return

        with self.lock:
            self.active_jobs_count += 1
            self.current_job_cancel = False

        self.send_message(
            chat_id,
            f"🔍 *Starting Scrape Job*\n• *Query*: `{query}`\n• *Count*: `{count}`\n• *Sources*: `{', '.join(sources)}`"
        )

        def telegram_progress(current: int, total: int, msg: str):
            if current % 5 == 0 or current == total:
                self.log(f"Chat {chat_id} progress: {current}/{total}")

        try:
            result = self.scraper_runner(
                query=query,
                count=count,
                sources=sources,
                progress_cb=telegram_progress,
                cancel_check=lambda: self.current_job_cancel,
            )

            files = result.get("files", [])
            zip_path = result.get("zip_path")

            if self.current_job_cancel:
                self.send_message(chat_id, f"🛑 *Scrape job cancelled for:* `{query}` (Collected {len(files)} images)")
            elif not files:
                self.send_message(chat_id, f"⚠️ *No images found for query:* `{query}`")
                return
            else:
                self.send_message(chat_id, f"✅ *Scraped {len(files)} images!* Sending preview photos...")

            if files:
                # Send preview photos (max 10)
                self.send_media_group(chat_id, files[:10], caption=f"📸 Scraped {len(files)} images for '{query}'")

                # Send ZIP archive if created
                if zip_path and os.path.exists(zip_path):
                    self.send_document(chat_id, zip_path, caption=f"📦 Full Asset Package: {query}.zip")

        except Exception as e:
            self.log(f"Scrape job error: {e}")
            self.send_message(chat_id, f"❌ *Error during scraping:* {str(e)}")
        finally:
            with self.lock:
                self.active_jobs_count = max(0, self.active_jobs_count - 1)
