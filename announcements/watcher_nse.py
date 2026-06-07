import requests
import logging
import time
from typing import List, Dict
from announcements.filters import process_announcements

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/companies-listing/corporate-filings-announcements",
}

NSE_API_URL = (
    "https://www.nseindia.com/api/corporate-announcements"
    "?index=equities&limit=50"
)

# ─────────────────────────────────────────────
# STEP 1: Get NSE session (cookies required)
# ─────────────────────────────────────────────
def get_nse_session() -> requests.Session:
    """
    NSE requires a valid browser session / cookies.
    We hit the homepage first to grab cookies.
    """
    session = requests.Session()
    try:
        session.get(
            "https://www.nseindia.com",
            headers=HEADERS,
            timeout=15
        )
        time.sleep(1)  # slight delay to mimic browser
    except Exception as e:
        logger.error(f"NSE session error: {e}")
    return session


# ─────────────────────────────────────────────
# STEP 2: Fetch raw announcements from NSE API
# ─────────────────────────────────────────────
def fetch_raw_nse_announcements(session: requests.Session) -> List[Dict]:
    """
    Hit NSE announcements API and return raw list.
    """
    raw_data = []
    try:
        response = session.get(
            NSE_API_URL,
            headers=HEADERS,
            timeout=20
        )
        response.raise_for_status()
        data = response.json()

        # NSE returns either a list or a dict with a key
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("data", [])
        else:
            items = []

        for item in items:
            raw_data.append({
                "date":    item.get("an_dt", "")[:10],
                "company": item.get("sm_name", "N/A").strip(),
                "subject": item.get("desc", "N/A").strip(),
                "symbol":  item.get("symbol", "N/A").strip(),
                "pdf_url": item.get("attchmntFile", ""),   # PDF link if available
                "source":  "NSE"
            })

    except requests.exceptions.HTTPError as e:
        logger.error(f"NSE HTTP error: {e}")
    except requests.exceptions.Timeout:
        logger.error("NSE request timed out.")
    except Exception as e:
        logger.error(f"NSE unexpected error: {e}")

    return raw_data


# ─────────────────────────────────────────────
# STEP 3: Main function (used by main.py)
# ─────────────────────────────────────────────
def get_nse_announcements() -> List[Dict]:
    """
    Full pipeline:
    1. Create session
    2. Fetch raw announcements
    3. Apply keyword filter + duplicate filter
    4. Return only relevant, fresh announcements
    """
    session = get_nse_session()
    raw = fetch_raw_nse_announcements(session)

    if not raw:
        logger.warning("NSE: No announcements fetched.")
        return []

    filtered = process_announcements(raw)

    logger.info(f"NSE: {len(raw)} fetched → {len(filtered)} passed filter.")
    return filtered


# ─────────────────────────────────────────────
# Quick standalone test
# ─────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = get_nse_announcements()
    if results:
        print(f"\n✅ NSE Filtered Results ({len(results)}):\n")
        for r in results:
            print(f"  [{r['date']}] {r['company']} ({r['symbol']})")
            print(f"           📄 {r['subject']}")
            if r['pdf_url']:
                print(f"           🔗 {r['pdf_url']}")
            print()
    else:
        print("⚠️  No relevant NSE announcements found.")
