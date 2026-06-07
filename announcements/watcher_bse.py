import requests
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

BSE_API_URL = "https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://www.bseindia.com/",
}

TIMEOUT = 30

def get_bse_announcements():
    try:
        session = requests.Session()
        session.headers.update(HEADERS)

        today = datetime.now().strftime("%d/%m/%Y")

        payload = {
            "scripcode": "",
            "strSearch": "",
            "strType": "C",
            "strToDate": today,
            "strFromDate": today,
            "strPrevDate": "",
            "segment": "E",
            "strSector": "",
            "strIndustry": "",
            "strGroup": "",
            "strSubGroup": ""
        }

        response = session.post(
            BSE_API_URL,
            json=payload,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        response.raise_for_status()

        data = response.json()

        announcements = []
        for item in data.get("Table", []):
            try:
                date_str = item.get("NewsDt", "")
                company = item.get("ScripName", "")
                subject = item.get("NewsSub", "")

                if not date_str or not company:
                    continue

                announcements.append({
                    "date": date_str,
                    "company": company,
                    "subject": subject,
                    "source": "BSE"
                })

            except Exception:
                continue

        logger.info(f"BSE: Fetched {len(announcements)} announcements")
        return announcements

    except Exception as e:
        logger.error(f"BSE fetch failed: {e}")
        return []
