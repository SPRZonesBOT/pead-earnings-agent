import requests
import logging
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BSE_CORPORATES_URL = "https://www.bseindia.com/corporates/announcements"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.bseindia.com/",
    "Connection": "keep-alive",
}

TIMEOUT = 30


def get_bse_announcements():
    """
    Fetch corporate announcements from BSE official website.
    Returns list of dicts with keys: date, company, subject, source.
    """
    try:
        session = requests.Session()
        session.headers.update(HEADERS)

        # Step 1: Visit BSE home to get cookies
        session.get("https://www.bseindia.com/", timeout=TIMEOUT)

        # Step 2: Fetch announcements page
        response = session.get(BSE_CORPORATES_URL, timeout=TIMEOUT)
        response.raise_for_status()

        logger.info(f"BSE status: {response.status_code}")

        # Parse HTML
        soup = BeautifulSoup(response.content, "html.parser")

        announcements = []

        # Look for announcement rows in the table
        # BSE typically uses table rows with announcement data
        rows = soup.find_all("tr")

        for row in rows:
            try:
                cells = row.find_all("td")
                if len(cells) < 3:
                    continue

                # Extract date, company, subject from cells
                date_str = cells[0].get_text(strip=True) if len(cells) > 0 else ""
                company = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                subject = cells[2].get_text(strip=True) if len(cells) > 2 else ""

                if not company:
                    continue

                # Skip header rows
                if "Company" in company or "Date" in date_str:
                    continue

                announcements.append({
                    "date": date_str,
                    "company": company.strip(),
                    "subject": subject.strip(),
                    "source": "BSE",
                })

            except Exception as e:
                logger.debug(f"BSE row parse error: {e}")
                continue

        logger.info(f"BSE: {len(announcements)} announcements fetched")
        return announcements

    except requests.exceptions.RequestException as e:
        logger.error(f"BSE request failed: {e}")
        return []
    except Exception as e:
        logger.error(f"BSE unexpected error: {e}")
        return []
