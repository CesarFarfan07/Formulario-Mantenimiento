"""Telegram notification service."""
import requests
from ..core.config import settings

BOT_TOKEN = settings.telegram_bot_token
CHAT_ID = settings.telegram_chat_id
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"


def send_telegram(message: str) -> bool:
    if not BOT_TOKEN or not CHAT_ID:
        return False
    try:
        resp = requests.post(API_URL, json={
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
        }, timeout=15)
        return resp.status_code == 200
    except Exception:
        return False
