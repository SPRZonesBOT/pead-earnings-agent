import requests
import logging  # <--- Ye check karein
from bs4 import BeautifulSoup

# ✅ Ye line zaroor honi chahiye
logger = logging.getLogger(__name__)

# ... baaki code ...

def get_bse_announcements():
    try:
        # BSE ka alternative API (no blocking)
        BSE_API = "https://www.bseindia.com/corporates/announcements.aspx"

        session = requests.Session()
        response = session.get(BSE_API, headers=HEADERS, timeout=20)

        # Parse HTML to find announcement table
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table", {"id": "tblAnnouncement"})

        announcements = []
        if table:
            rows = table.find_all("tr")[1:]  # Skip header
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 4:  # Ensure all columns exist
                    announcements.append({
                        "date": cols[0].get_text(strip=True),
                        "company": cols[1].get_text(strip=True),
                        "subject": cols[2].get_text(strip=True),
                        "source": "BSE"
                    })

        logger.info(f"BSE: {len(announcements)} announcements found")
        return announcements
    except Exception as e:
        logger.error(f"BSE Error: {e}")
        return []
