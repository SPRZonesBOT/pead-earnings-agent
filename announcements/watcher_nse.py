import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Constants
NSE_HOME = "https://www.nseindia.com"
NSE_API = "https://www.nseindia.com/api/corporate-announcements"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}

def get_nse_announcements():
    try:
        session = requests.Session()
        session.headers.update(HEADERS)
        
        # Pehle home page visit karna padta hai cookies ke liye
        session.get(NSE_HOME, timeout=15)

        today = datetime.now().strftime("%d-%m-%Y")
        params = {"index": "equities", "from_date": today, "to_date": today}
        
        response = session.get(NSE_API, params=params, timeout=15)
        response.raise_for_status()
        
        items = response.json()
        announcements = []
        for item in items:
            raw_dt = str(item.get("anndatetime", ""))
            # Formatting Date: 070620241430 -> 07-06 14:30
            formatted_dt = f"{raw_dt[:2]}-{raw_dt[2:4]} {raw_dt[8:10]}:{raw_dt[10:12]}" if len(raw_dt) >= 12 else "N/A"

            announcements.append({
                "date": formatted_dt,
                "company": item.get("symbol", "N/A"),
                "subject": item.get("desc", "N/A"),
                "source": "NSE"
            })
        return announcements
    except Exception as e:
        logger.error(f"NSE Error: {e}")
        return []
