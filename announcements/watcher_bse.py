import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import logging
from tenacity import retry, stop_after_attempt, wait_fixed

logger = logging.getLogger(__name__)

BSE_URL = "https://www.bseindia.com/corporate/ann.html"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.bseindia.com/",
    "Connection": "keep-alive",
}

TIMEOUT = 60


@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
def fetch_bse_announcements():
    response = requests.get(BSE_URL, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    return response.text


def parse_bse_announcements(html_content):
    announcements = []
    soup = BeautifulSoup(html_content, "html.parser")

    tables = soup.find_all("table")
    if not tables:
        logger.warning("BSE: No table found in HTML")
        return announcements

    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 3:
                continue

            try:
                date_text = cols[0].get_text(strip=True)
                company = cols[1].get_text(strip=True)
                subject = cols[2].get_text(strip=True)

                ann_date = None
                for fmt in ["%d-%b-%Y", "%d-%m-%Y", "%d/%m/%Y"]:
                    try:
                        ann_date = datetime.strptime(date_text, fmt).date()
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
                        "source": "BSE"
                    })

            except Exception:
                continue

    logger.info(f"BSE: Fetched {len(announcements)} announcements")
    return announcements


def get_bse_announcements():
    try:
        html = fetch_bse_announcements()
        return parse_bse_announcements(html)
    except Exception as e:
        logger.error(f"BSE fetch failed: {e}")
        return []


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    data = get_bse_announcements()
    for row in data:
        print(f"{row['date']} | {row['company']} | {row['subject']} | {row['source']}")
