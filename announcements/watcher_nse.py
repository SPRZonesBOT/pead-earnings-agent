import requests
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

NSE_HOME = "https://www.nseindia.com"
NSE_API = "https://www.nseindia.com/api/corporate-announcements"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/market-data/upcoming-results",
}

def get_nse_announcements():
    try:
        session = requests.Session()
        session.headers.update(HEADERS)
        session.get(NSE_HOME, timeout=20) # Get cookies

        # Fetch for today and yesterday to be safe
        today = datetime.now().strftime("%d-%m-%Y")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%d-%m-%Y")

        params = {"index": "equities", "from_date": yesterday, "to_date": today}
        response = session.get(NSE_API, params=params, timeout=20)
        response.raise_for_status()
        
        data = response.json()
        items = data if isinstance(data, list) else data.get("data") or []

        announcements = []
        for item in items:
            # Fixing the Date Key issue
            raw_date = item.get("anndatetime") or item.get("anndate") or item.get("dt") or "N/A"
            # Trim date if it's too long (e.g. 07-Jun-2026 14:00)
            clean_date = raw_date[:11] if raw_date != "N/A" else "N/A"

            announcements.append({
                "date": clean_date,
                "company": item.get("symbol", "Unknown"),
                "subject": item.get("desc", "No Subject"),
                "source": "NSE"
            })
        return announcements
    except Exception as e:
        logger.error(f"NSE Error: {e}")
        return []
