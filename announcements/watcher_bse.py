import requests
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Constants
BSE_URL = "https://www.bseindia.com/corporates/announcements.aspx"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.bseindia.com/",
}

def get_bse_announcements():
    try:
        response = requests.get(BSE_URL, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")
        
        # BSE table logic
        table = soup.find("table", {"id": "ctl00_ContentPlaceHolder1_gvAnn"})
        
        announcements = []
        if table:
            rows = table.find_all("tr")[1:11] # Top 10 rows
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 4:
                    announcements.append({
                        "date": cols[3].get_text(strip=True)[:11], # Date column
                        "company": cols[1].get_text(strip=True),
                        "subject": cols[2].get_text(strip=True),
                        "source": "BSE"
                    })
        
        return announcements
    except Exception as e:
        logger.error(f"BSE Error: {e}")
        return []
