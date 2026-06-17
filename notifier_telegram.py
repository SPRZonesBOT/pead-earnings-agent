# notifier_telegram.py
import requests
import os

# Try to import from config, else use env
try:
    from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
except ImportError:
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8944262472:AAF8IOk8si-_hMNxvRs588evNZWe1gEwQ_o')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '1715733436')

def send_telegram_alert(message):
    """
    Send a message to Telegram bot.
    If token/chat_id not set, print locally.
    """
    if TELEGRAM_BOT_TOKEN == '8944262472:AAF8IOk8si-_hMNxvRs588evNZWe1gEwQ_o' or not TELEGRAM_BOT_TOKEN:
        print("\n" + "="*50)
        print("📢 TELEGRAM ALERT (Token not set):")
        print(message)
        print("="*50 + "\n")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("✅ Telegram alert sent successfully!")
        else:
            print(f"❌ Telegram error: {response.text}")
    except Exception as e:
        print(f"❌ Failed to send: {e}")
