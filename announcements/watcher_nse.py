import requests
import logging  # <--- Ye check karein
from datetime import datetime, timedelta

# ✅ Ye line zaroor honi chahiye
logger = logging.getLogger(__name__) 

# ... baaki code ...

def get_nse_announcements():
    try:
        session = requests.Session()
        session.headers.update(HEADERS)
        session.get(NSE_HOME, timeout=20)

        today = datetime.now().strftime("%d-%m-%Y")
        params = {"index": "equities", "from_date": today, "to_date": today}

        response = session.get(NSE_API, params=params, timeout=20)
        response.raise_for_status()

        items = response.json()
        announcements = []
        for item in items:
            # Extract raw date (e.g., "070620261411")
            raw_dt = str(item.get("anndatetime", ""))

            # Convert to readable format: "07-Jun 14:11"
            if len(raw_dt) >= 12:
                day = raw_dt[:2]
                month = raw_dt[2:4]
                hour = raw_dt[8:10]
                minute = raw_dt[10:12]
                formatted_dt = f"{day}-{month} {hour}:{minute}"
            else:
                formatted_dt = "N/A"

            announcements.append({
                "date": formatted_dt,
                "company": item.get("symbol", "N/A"),
                "subject": item.get("desc", "N/A"),
                "source": "NSE"
            })
        return announcements
    except Exception as e:
        logger.error(f"NSE Error: {e}")
        return []
