import requests
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Unofficial API jo reliably kaam karta hai
NSE_API_URL = "https://api.stockanalysis.com/api/v1/news/nse"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

TIMEOUT = 30


def get_nse_announcements():
    """
    Fetch NSE announcements from reliable API.
    """
    try:
        response = requests.get(
            NSE_API_URL,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        
        announcements = []
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        # Parse response based on API structure
        items = data.get("data", data.get("news", []))
        
        for item in items:
            try:
                date_str = item.get("date", item.get("published", ""))
                company = item.get("symbol", item.get("company", ""))
                subject = item.get("title", item.get("subject", ""))

                if not date_str or not company:
                    continue

                # Parse date
                for fmt in ["%Y-%m-%d", "%d-%m-%Y", "%d-%b-%Y"]:
                    try:
                        ann_date = datetime.strptime(date_str[:10], fmt).date()
                        break
                    except ValueError:
                        continue
                else:
                    continue

                if ann_date in [today, yesterday]:
                    announcements.append({
                        "date": str(ann_date),
                        "company": company,
                        "subject": subject,
                        "source": "NSE"
                    })

            except Exception as e:
                logger.warning(f"NSE parse error: {e}")
                continue

        logger.info(f"NSE: Fetched {len(announcements)} announcements")
        return announcements

    except Exception as e:
        logger.error(f"NSE fetch failed: {e}")
        return []


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    data = get_nse_announcements()
    for row in data:
        print(f"{row['date']} | {row['company']} | {row['subject']}")
