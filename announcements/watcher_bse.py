import requests
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Direct URL for announcements
BSE_URL = "https://www.bseindia.com/corporates/announcements.aspx"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Referer": "https://www.bseindia.com/",
}

def get_bse_announcements():
    try:
        session = requests.Session()
        response = session.get(BSE_URL, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(response.content, "html.parser")

        announcements = []
        # BSE uses a specific table for announcements
        # We look for rows that contain corporate filings
        table = soup.find("table", {"id": "ctl00_ContentPlaceHolder1_gvAnn"})
        
        if not table:
            # Fallback: search for any table rows if ID is dynamic
            rows = soup.find_all("tr", class_="td00001") or soup.find_all("tr")[5:25]
        else:
            rows = table.find_all("tr")[1:] # Skip header

        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 3:
                # BSE Column structure: 0: Scrip Code, 1: Company Name, 2: Subject, 3: Date
                company = cols[1].get_text(strip=True)
                subject = cols[2].get_text(strip=True)
                date = cols[3].get_text(strip=True) if len(cols) > 3 else "N/A"

                if company and subject:
                    announcements.append({
                        "date": date[:11],
                        "company": company[:25],
                        "subject": subject[:60] + "...",
                        "source": "BSE"
                    })

        logger.info(f"BSE: Extracted {len(announcements)} announcements")
        return announcements
    except Exception as e:
        logger.error(f"BSE Error: {e}")
        return []
