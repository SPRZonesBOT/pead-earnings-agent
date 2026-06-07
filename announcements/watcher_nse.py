import requests
from datetime import datetime, timedelta
import logging
from tenacity import retry, stop_after_attempt, wait_fixed

logger = logging.getLogger(__name__)

NSE_HOME_URL = "https://www.nseindia.com"
NSE_API_URL = "https://www.nseindia.com/api/corporate-announcements"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
    "Connection": "keep-alive",
    "Origin": "https://www.nseindia.com",
}

TIMEOUT = 30


def get_nse_session():
    session = requests.Session()
    session.headers.update(HEADERS)

    try:
        resp = session.get(NSE_HOME_URL, timeout=TIMEOUT)
        resp.raise_for_status()
        logger.info("NSE session established")
    except Exception as e:
        logger.warning(f"NSE session init failed: {e}")

    return session


@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
def fetch_nse_announcements():
    session = get_nse_session()

    today = datetime.now()
    from_date = (today - timedelta(days=2)).strftime("%d-%m-%Y")
    to_date = today.strftime("%d-%m-%Y")

    params = {
        "index": "equities",
        "from_date": from_date,
        "to_date": to_date,
    }

    response = session.get(
        NSE_API_URL,
        params=params,
        timeout=TIMEOUT
    )

    if response.status_code == 403:
        logger.error("NSE returned 403 Forbidden")
        return []

    response.raise_for_status()

    try:
        return response.json()
    except Exception as e:
        logger.error(f"NSE JSON parse failed: {e}")
        return []


def parse_nse_announcements(api_response):
    announcements = []
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    if not api_response:
        return announcements

    # NSE can return either list or dict
    if isinstance(api_response, list):
        data = api_response
    elif isinstance(api_response, dict):
        data = (
            api_response.get("data")
            or api_response.get("announcements")
            or api_response.get("items")
            or []
        )
    else:
        return announcements

    if isinstance(data, dict):
        data = [data]

    for item in data:
        try:
            if not isinstance(item, dict):
                continue

            date_str = (
                item.get("date")
                or item.get("anndate")
                or item.get("ann_dt")
                or item.get("announcementDate")
                or ""
            )

            company = (
                item.get("symbol")
                or item.get("compName")
                or item.get("company")
                or item.get("sm")
                or item.get("companyName")
                or ""
            )

            subject = (
                item.get("subject")
                or item.get("desc")
                or item.get("description")
                or item.get("head")
                or item.get("title")
                or ""
            )

            if not date_str or not company:
                continue

            ann_date = None
            for fmt in ["%d-%m-%Y", "%Y-%m-%d", "%d-%b-%Y", "%d/%m/%Y", "%d-%m-%Y %H:%M:%S"]:
                try:
                    ann_date = datetime.strptime(date_str, fmt).date()
                    break
                except ValueError:
                    continue

            if not ann_date:
                continue

            if ann_date in [today, yesterday]:
                announcements.append({
                    "date": str(ann_date),
                    "company": company,
                    "subject": subject,
                    "source": "NSE"
                })

        except Exception as e:
            logger.warning(f"Skipping NSE item: {e}")

    logger.info(f"NSE: Fetched {len(announcements)} announcements")
    return announcements


def get_nse_announcements():
    try:
        api_response = fetch_nse_announcements()
        return parse_nse_announcements(api_response)
    except Exception as e:
        logger.error(f"NSE announcements fetch failed after retries: {e}")
        return []


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    data = get_nse_announcements()
    for row in data:
        print(f"{row['date']} | {row['company']} | {row['subject']} | {row['source']}")
