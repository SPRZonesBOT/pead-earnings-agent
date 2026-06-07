import requests
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Official BSE API endpoint
BSE_API_URL = "https://api.bseindia.com/CorporateAPI/api/GetCorporateActions"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.bseindia.com/",
}

TIMEOUT = 30

def get_bse_announcements():
    try:
        session = requests.Session()
        session.headers.update(HEADERS)

        # Get today's date in required format
        today = datetime.now().strftime("%d%%2F%m%%2F%Y")

        params = {
            "type": "Announcements",
            "from_date": today,
            "to_date": today,
        }

        response = session.get(
            BSE_API_URL,
            params=params,
            timeout=TIMEOUT
        )

        if response.status_code == 403:
            logger.error("BSE API blocked access (403 Forbidden). Trying alternative method...")
            return []

        response.raise_for_status()
        data = response.json()

        announcements = []
        for item in data:
            try:
                date_str = item.get("Anndate", "")
                company = item.get("Sm", "")
                subject = item.get("Desc", "")

                if not date_str or not company:
                    continue

                announcements.append({
                    "date": date_str,
                    "company": company,
                    "subject": subject,
                    "source": "BSE"
                })

            except Exception as e:
                logger.warning(f"BSE parse error: {e}")
                continue

        logger.info(f"BSE: Fetched {len(announcements)} announcements")
        return announcements

    except Exception as e:
        logger.error(f"BSE fetch failed: {e}")
        return []

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    data = get_bse_announcements()
    for row in data:
        print(f"{row['date']} | {row['company']} | {row['subject']}")
