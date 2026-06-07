import logging
import time
from typing import List, Dict
import requests
from announcements.filters import process_announcements

logger = logging.getLogger(__name__)

# Very specific headers to fool BSE security
BSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://www.bseindia.com",
    "Referer": "https://www.bseindia.com/",
    "Host": "api.bseindia.com",
}

def fetch_bse_announcements_api() -> List[Dict]:
    """
    Primary method: Fetches announcements using the BSE JSON API.
    """
    # Current Date filter for BSE API
    # P = Periodical (last 24 hours)
    url = "https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w?strCat=-1&strPrevDate=&strScrip=&strSearch=P&strToDate=&strType=C&subcategory=-1"
    
    raw_data = []
    
    try:
        session = requests.Session()
        # First, hit the main site to get cookies
        session.get("https://www.bseindia.com", headers={"User-Agent": BSE_HEADERS["User-Agent"]}, timeout=10)
        
        # Now call the API
        response = session.get(url, headers=BSE_HEADERS, timeout=15)
        
        if response.status_code != 200:
            logger.error(f"BSE API returned status code {response.status_code}")
            return []

        # Check if response is actually JSON
        try:
            data = response.json()
        except Exception:
            logger.error("BSE API did not return JSON. It might be blocking us.")
            return []

        # BSE API structure is usually a list of dictionaries
        if not isinstance(data, list):
            logger.warning(f"Unexpected BSE data format: {type(data)}")
            return []

        for item in data[:40]:
            # Map BSE keys to our standard format
            # BSE keys: NEWS_DT, SLONGNAME, NEWSSUB, SCRIP_CD, ATTACHMENTNAME
            
            attachment = item.get("ATTACHMENTNAME", "")
            pdf_link = ""
            if attachment:
                pdf_link = f"https://www.bseindia.com/xml-data/corpfiling/AttachLive/{attachment}"

            raw_data.append({
                "date": str(item.get("NEWS_DT", ""))[:10],
                "company": str(item.get("SLONGNAME", "N/A")).strip(),
                "subject": str(item.get("NEWSSUB", "N/A")).strip(),
                "symbol": str(item.get("SCRIP_CD", "N/A")).strip(),
                "pdf_url": pdf_link,
                "source": "BSE"
            })

        logger.info(f"BSE: Successfully fetched {len(raw_data)} items via API.")

    except Exception as e:
        logger.error(f"BSE API Error: {e}")
    
    return raw_data

def get_bse_announcements() -> List[Dict]:
    """
    Main entry point for BSE Module
    """
    logger.info("Starting BSE Fetch...")
    
    # Try API first
    raw_results = fetch_bse_announcements_api()
    
    if not raw_results:
        logger.warning("BSE API failed to return data.")
        return []

    # Filter the results
    filtered = process_announcements(raw_results)
    logger.info(f"BSE: {len(raw_results)} found, {len(filtered)} passed filters.")
    
    return filtered

if __name__ == "__main__":
    # Test run
    logging.basicConfig(level=logging.INFO)
    res = get_bse_announcements()
    for r in res:
        print(r)
