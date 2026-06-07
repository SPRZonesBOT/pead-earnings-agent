import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

def send_telegram_alert(company, subject, source, ann_datetime, pdf_link=None):
    """Telegram pe alert bhejo"""
    
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram config missing")
        return
    
    message = f"""
🚨 **NEW RESULT ANNOUNCEMENT**

📊 Company: {company}
🏢 Source: {source}
📅 Date: {ann_datetime}
📝 Subject: {subject[:100]}...

"""
    
    if pdf_link:
        message += f"📎 PDF: {pdf_link}\n"
    
    message += "\n#PEAD #Results #BSE #NSE"
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"✅ Telegram alert sent: {company}")
        else:
            print(f"❌ Telegram error: {response.text}")
    except Exception as e:
        print(f"❌ Telegram send failed: {e}")

def send_daily_summary(summary_text):
    """Daily summary bhejo"""
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": summary_text,
        "parse_mode": "Markdown"
    }
    
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"❌ Summary send failed: {e}")
