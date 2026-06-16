# notifier_telegram.py
import requests
import os

def send_telegram_alert(message, subject=None, source=None, ann_datetime=None):
    """
    Flexible function:
    - Agar sirf message diya toh woh use hoga
    - Agar saare arguments diye toh formatted message banta hai
    """
    # Agar subject, source, ann_datetime diye hain toh formatted message banao
    if subject and source and ann_datetime:
        full_message = f"*{subject}*\nSource: {source}\nTime: {ann_datetime}\n\n{message}"
    else:
        full_message = message

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID_HERE")
    
    # Agar token set nahi hai toh local print karo
    if bot_token == "YOUR_BOT_TOKEN_HERE":
        print("\n" + "="*50)
        print("📢 TELEGRAM ALERT (Printed locally - Token not set):")
        print(full_message)
        print("="*50 + "\n")
        return
        
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": full_message,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("✅ Telegram alert sent successfully!")
        else:
            print(f"❌ Telegram error: {response.text}")
    except Exception as e:
        print(f"❌ Failed to send Telegram message: {e}")
