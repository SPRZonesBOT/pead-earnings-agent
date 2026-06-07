import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# BSE Direct JSON API
BSE_API_URL = "https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Referer": "https://www.bseindia.com/",
    "Accept": "application/json, text/plain, */*",
}

def get_bse_announcements():
    try:
        # BSE API needs dates in YYYYMMDD format
        dt = datetime.now().strftime("%Y%m%d")
        
        params = {
            "strType": "all",
            "strSdate": dt,
            "strEdate": dt,
            "strSort": "D",
            "strScrip": "",
            "strSearch": "P", # P for Public
        }

        response = requests.get(BSE_API_URL, params=params, headers=HEADERS, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        announcements = []

        for item in data:
            # BSE API keys: SLONGNAME, NEW_SUBJECT, NEWS_DT
            announcements.append({
                "date": item.get("NEWS_DT", "")[:11], # Takes DD MMM YYYY
                "company": item.get("SCRIP_CD", "N/A"),
                "subject": item.get("NEW_SUBJECT", "N/A"),
                "source": "BSE"
            })

        logger.info(f"BSE: {len(announcements)} announcements found")
        return announcements
    except Exception as e:
        logger.error(f"BSE API Error: {e}")
        return []
