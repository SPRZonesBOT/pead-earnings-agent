import requests
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

NSE_API_URL = "https://www.nseindia.com/api/corporate-announcements"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}

TIMEOUT = 30

def get_nse_announcements():
    try:
        session = requests.Session()
        session.headers.update(HEADERS)

        # Visit NSE home first to get cookies
        session.get("https://www.nseindia.com/", timeout=TIMEOUT)

        today = datetime.now().strftime("%d-%m-%Y")

        params = {
            "index": "equities",
            "from_date": today,
            "to_date": today,
        }

        response = session.get(
            NSE_API_URL,
            params=params,
            timeout=TIMEOUT
        )
        response.raise_for_status()

        data = response.json()

        announcements = []
        for item in data:
            try:
                date_str = item.get("anndate", "")
                company = item.get("symbol", "")
                subject = item.get("desc", "")

                if not date_str or not company:
                    continue

                announcements.append({
                    "date": date_str,
                    "company": company,
                    "subject": subject,
                    "source": "NSE"
                })

            except Exception:
                continue

        logger.info(f"NSE: Fetched {len(announcements)} announcements")
        return announcements

    except Exception as e:
        logger.error(f"NSE fetch failed: {e}")
        return []
