import requests
from datetime import datetime, timedelta
import logging
import json
from tenacity import retry, stop_after_attempt, wait_fixed

# Logger setup
logger = logging.getLogger(__name__)

# NSE API URL (Updated - official API endpoint)
NSE_API_URL = "https://www.nseindia.com/api/corporate-announcements"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
    "Origin": "https://www.nseindia.com",
    "Connection": "keep-alive",
}

TIMEOUT = 30
SESSION_COOKIES = {}


def get_nse_session():
    """
    Establish a session with NSE by visiting homepage first (required for cookies).
    """
    global SESSION_COOKIES
    session = requests.Session()
    session.headers.update(HEADERS)

    try:
        # Step 1: Visit homepage to get cookies
        home_resp = session.get(
            "https://www.nseindia.com",
            timeout=TIMEOUT
        )
        home_resp.raise_for_status()

        # Store cookies
        SESSION_COOKIES = session.cookies.get_dict()
        logger.info("NSE session established successfully")
        return session
    except Exception as e:
        logger.warning(f"NSE session init failed (will try without session): {e}")
        return session


@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
def fetch_nse_announcements():
    """
    Fetch corporate announcements from NSE API.
    Retries up to 3 times with 5 sec gap if failed.
    """
    try:
        # Establish session first
        session = get_nse_session()

        # Set date range (last 2 days)
        today = datetime.now()
        two_days_ago = today - timedelta(days=2)

        params = {
            "index": "equities",
            "from_date": two_days_ago.strftime("%d-%m-%Y"),
            "to_date": today.strftime("%d-%m-%Y"),
        }

        response = session.get(
            NSE_API_URL,
            params=params,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        response.raise_for_status()
        return response.json()

    except requests.exceptions.HTTPError as e:
        if response.status_code == 404:
            logger.error(f"NSE API URL not found: {NSE_API_URL}")
            # Fallback to alternative endpoint
            return fetch_nse_announcements_fallback()
        logger.error(f"NSE HTTP error: {e}")
        raise
    except Exception as e:
        logger.error(f"NSE fetch failed: {e}")
        raise


@retry(stop=stop_after_attempt(2), wait=wait_fixed(5))
def fetch_nse_announcements_fallback():
    """
    Fallback: Try alternative NSE endpoint if primary fails.
    """
    fallback_url = "https://www.nseindia.com/api/corp-info"

    session = get_nse_session()
    today = datetime.now()
    two_days_ago = today - timedelta(days=2)

    params = {
        "from_date": two_days_ago.strftime("%d-%m-%Y"),
        "to_date": today.strftime("%d-%m-%Y"),
    }

    try:
        response = session.get(
            fallback_url,
            params=params,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"NSE fallback also failed: {e}")
        raise


def parse_nse_announcements(api_response):
    """
    Parse NSE API JSON response and extract announcements.
    """
    announcements = []
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    if not api_response:
        return announcements

    # NSE API returns data in different structures
    data = api_response.get("data", api_response.get("announcements", api_response.get("items", [])))

    if isinstance(data, dict):
        data = [data]

    for item in data:
        try:
            if isinstance(item, str):
                continue

            # Extract fields (handle multiple possible key names)
            date_str = item.get("date", item.get("anndate", item.get("ann_dt", "")))
            company = item.get("symbol", item.get("compName", item.get("company", item.get("sm", ""))))
            subject = item.get("subject", item.get("desc", item.get("description", item.get("head", ""))))

            if not date_str or not company:
                continue

            # Parse date
            for fmt in ["%d-%m-%Y", "%Y-%m-%d", "%d-%b-%Y", "%d/%m/%Y"]:
                try:
                    ann_date = datetime.strptime(date_str, fmt).date()
                    break
                except ValueError:
                    continue
            else:
                continue  # Skip if no date format matched

            # Only keep today's or yesterday's announcements
            if ann_date in [today, yesterday]:
                announcements.append({
                    "date": str(ann_date),
                    "company": company,
                    "subject": subject,
                    "source": "NSE"
                })

        except Exception as e:
            logger.warning(f"NSE: Skipping item due to error: {e}")
            continue

    logger.info(f"NSE: Fetched {len(announcements)} announcements")
    return announcements


def get_nse_announcements():
    """
    Main function to get NSE announcements with error handling.
    """
    try:
        api_response = fetch_nse_announcements()
        announcements = parse_nse_announcements(api_response)
        return announcements
    except Exception as e:
        logger.error(f"NSE announcements fetch failed after retries: {e}")
        return []


# ----------------------------
# For Direct Testing
# ----------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    announcements = get_nse_announcements()
    for ann in announcements:
        print(f"{ann['date']} | {ann['company']} | {ann['subject']} | {ann['source']}")

