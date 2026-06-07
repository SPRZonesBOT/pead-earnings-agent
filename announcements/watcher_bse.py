import requests
import logging
from bs4 import BeautifulSoup
import time

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.bseindia.com/",
}

def get_bse_announcements():
    try:
        # 2 retries with longer timeout
        for attempt in range(2):
            try:
                response = requests.get(
                    "https://www.bseindia.com/corporates/announcements.aspx",
                    headers=HEADERS,
                    timeout=25
                )
                soup = BeautifulSoup(response.text, "html.parser")
                table = soup.find("table", {"id": "ctl00_ContentPlaceHolder1_gvAnn"})
                
                announcements = []
                if table:
                    rows = table.find_all("tr")[1:11]
                    for row in rows:
                        cols = row.find_all("td")
                        if len(cols) >= 4:
                            announcements.append({
                                "date": cols[3].get_text(strip=True)[:11],
                                "company": cols[1].get_text(strip=True),
                                "subject": cols[2].get_text(strip=True),
                                "source": "BSE"
                            })
                return announcements
            except Exception as e:
                if attempt == 1:
                    logger.error(f"BSE Error: {e}")
                    return []
                time.sleep(2)  # wait 2 sec before retry
    except Exception as e:
        logger.error(f"BSE Error: {e}")
        return []
