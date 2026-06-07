import requests
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

NSE_HOME = "https://www.nseindia.com"
NSE_API = "https://www.nseindia.com/api/corporate-announcements"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Referer": "https://www.nseindia.com/",
}

def get_nse_announcements():
    try:
        session = requests.Session()
        session.headers.update(HEADERS)
        session.get(NSE_HOME, timeout=20) 

        today = datetime.now().strftime("%d-%m-%Y")
        params = {"index": "equities", "from_date": today, "to_date": today}
        
        response = session.get(NSE_API, params=params, timeout=20)
        response.raise_for_status()
        
        items = response.json()
        announcements = []
        for item in items:
            raw_dt = str(item.get("anndatetime", "")) # Format: 070620261411
            
            # Format date: 070620261411 -> 07-Jun 14:11
            try:
                if len(raw_dt) >= 12:
                    formatted_dt = f"{raw_dt[:2]}-{raw_dt[2:4]} {raw_dt[8:10]}:{raw_dt[10:12]}"
                else:
                    formatted_dt = raw_dt
            except:
                formatted_dt = raw_dt

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
