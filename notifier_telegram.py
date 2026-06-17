# notifier_telegram.py
import requests
import os
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

def send_telegram_alert(message):
    if TELEGRAM_BOT_TOKEN == '8944262472:AAF8IOk8si-_hMNxvRs588evNZWe1gEwQ_o':
        print("\n" + "="*50)
        print("📢 TELEGRAM ALERT (Token not set):")
        print(message)
        print("="*50 + "\n")
        return
    url = f"https://api.telegram.org/bot8944262472:AAF8IOk8si-_hMNxvRs588evNZWe1gEwQ_o/sendMessage"
    payload = {
        "chat_id": 1715733436,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("✅ Telegram alert sent!")
        else:
            print(f"❌ Telegram error: {response.text}")
    except Exception as e:
        print(f"❌ Failed: {e}")
