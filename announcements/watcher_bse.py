import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import logging
import time
from tenacity import retry, stop_after_attempt, wait_fixed

# Logger setup
logger = logging.getLogger(__name__)

# BSE Announcements URL
BSE_URL = "https://www.bseindia.com/corporate/ann.html"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.bseindia.com/",
    "Connection": "keep-alive",
}

TIMEOUT = 30  # Increased timeout


@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
def fetch_bse_announcements():
    """
    Fetch corporate announcements from BSE website.
    Retries up to 3 times with 5 sec gap if failed.
    """
    try:
        response = requests.get(
            BSE_URL,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        logger.error(f"BSE fetch failed: {e}")
        raise


def parse_bse_announcements(html_content):
    """
    Parse BSE announcements HTML and extract relevant data.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    announcements = []

    # Try multiple table selectors (BSE changes structure sometimes)
    table = soup.find("table", {"id": "tblAnnouncements"})
    if not table:
        table = soup.find("table", {"class": "announcements"})
    if not table:
        table = soup.find("table")

    if not table:
        logger.warning("BSE: No announcement table found in HTML")
        return announcements

    rows = table.find_all("tr")[1:]  # Skip header row
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 3:
            continue

        try:
            date_text = cols[0].get_text(strip=True)
            company = cols[1].get_text(strip=True)
            subject = cols[2].get_text(strip=True)

            # Parse date
            announcement_date = datetime.strptime(date_text, "%d-%b-%Y").date()

            # Only keep today's or yesterday's announcements
            if announcement_date in [today, yesterday]:
                announcements.append({
                    "date": str(announcement_date),
                    "company": company,
                    "subject": subject,
                    "source": "BSE"
                })
        except (ValueError, IndexError) as e:
            logger.warning(f"BSE: Skipping row due to error: {e}")
            continue

    logger.info(f"BSE: Fetched {len(announcements)} announcements")
    return announcements


def get_bse_announcements():
    """
    Main function to get BSE announcements with error handling.
    """
    try:
        html = fetch_bse_announcements()
        announcements = parse_bse_announcements(html)
        return announcements
    except Exception as e:
        logger.error(f"BSE announcements fetch failed after retries: {e}")
        return []


# ----------------------------
# For Direct Testing
# ----------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    announcements = get_bse_announcements()
    for ann in announcements:
        print(f"{ann['date']} | {ann['company']} | {ann['subject']} | {ann['source']}")

