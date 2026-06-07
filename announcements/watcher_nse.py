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
    """
    Fetch corporate announcements from NSE India official API.
    Returns list of dicts with keys: date, company, subject, source.
    """
    try:
        session = requests.Session()
        session.headers.update(HEADERS)

        # Step 1: Visit homepage to get cookies/session
        session.get(NSE_HOME, timeout=TIMEOUT)

        # Step 2: Fetch announcements for today
        today = datetime.now().strftime("%d-%m-%Y")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%d-%m-%Y")

        params = {
            "index": "equities",
            "from_date": yesterday,
            "to_date": today,
        }

        response = session.get(NSE_API, params=params, timeout=TIMEOUT)
        response.raise_for_status()

        data = response.json()

        # Handle both list and dict responses
        items = data if isinstance(data, list) else data.get("data") or []

        announcements = []
        for item in items:
            if not isinstance(item, dict):
                continue

            company = (
                item.get("symbol")
                or item.get("companyName")
                or item.get("compName")
                or ""
            )
            subject = (
                item.get("desc")
                or item.get("subject")
                or item.get("title")
                or ""
            )
            date_str = (
                item.get("anndate")
                or item.get("date")
                or item.get("announcementDate")
                or ""
            )

            if not company:
                continue

            announcements.append({
                "date": date_str,
                "company": company.strip(),
                "subject": subject.strip(),
                "source": "NSE",
            })

        logger.info(f"NSE: {len(announcements)} announcements fetched")
        return announcements

    except requests.exceptions.RequestException as e:
        logger.error(f"NSE request failed: {e}")
        return []
    except Exception as e:
        logger.error(f"NSE unexpected error: {e}")
        return []
