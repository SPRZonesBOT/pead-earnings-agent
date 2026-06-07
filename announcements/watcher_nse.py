import requests
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

NSE_HOME = "https://www.nseindia.com"
NSE_API = "https://www.nseindia.com/api/corporate-announcements"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
    "Connection": "keep-alive",
}

TIMEOUT = 30


def get_nse_announcements():
    try:
        session = requests.Session()
        session.headers.update(HEADERS)

        session.get(NSE_HOME, timeout=TIMEOUT)

        today = datetime.now().strftime("%d-%m-%Y")
        params = {
            "index": "equities",
            "from_date": today,
            "to_date": today,
        }

        response = session.get(NSE_API, params=params, timeout=TIMEOUT)

        logger.info(f"NSE status: {response.status_code}")
        logger.info(f"NSE content type: {response.headers.get('Content-Type')}")

        response.raise_for_status()

        try:
            data = response.json()
        except Exception as e:
            logger.error(f"NSE JSON parse failed: {e}")
            logger.error(f"Raw response: {response.text[:500]}")
            return []

        logger.info(f"NSE raw type: {type(data)}")

        announcements = []

        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("data") or data.get("records") or data.get("items") or []
        else:
            logger.warning("NSE response is neither list nor dict")
            return []

        logger.info(f"NSE items found: {len(items)}")

        for item in items:
            if not isinstance(item, dict):
                continue

            date_str = (
                item.get("anndate")
                or item.get("date")
                or item.get("announcementDate")
                or item.get("annDt")
                or ""
            )

            company = (
                item.get("symbol")
                or item.get("companyName")
                or item.get("compName")
                or item.get("company")
                or ""
            )

            subject = (
                item.get("desc")
                or item.get("subject")
                or item.get("title")
                or item.get("details")
                or ""
            )

            if not company:
                continue

            announcements.append({
                "date": date_str,
                "company": company,
                "subject": subject,
                "source": "NSE"
            })

        logger.info(f"NSE: Fetched {len(announcements)} announcements")
        return announcements

    except Exception as e:
        logger.error(f"NSE fetch failed: {e}")
        return []
