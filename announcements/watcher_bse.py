import requests
import logging
import time
from bs4 import BeautifulSoup
from typing import List, Dict
from announcements.filters import process_announcements

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.bseindia.com/",
    "Accept-Language": "en-US,en;q=0.9",
}

BSE_API_URL = (
    "https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w"
    "?strCat=-1&strPrevDate=&strScrip=&strSearch=P"
    "&strToDate=&strType=C&subcategory=-1"
)

BSE_FALLBACK_URL = "https://www.bseindia.com/corporates/announcements.aspx"

# ─────────────────────────────────────────────
# STEP 1: Try BSE JSON API
# ─────────────────────────────────────────────
def fetch_bse_via_api() -> List[Dict]:
    raw_data = []
    try:
        response = requests.get(BSE_API_URL, headers=HEADERS, timeout=20)
        response.raise_for_status()

        try:
            data = response.json()
        except ValueError as e:
            logger.error(f"BSE API did not return valid JSON: {e}")
            logger.debug(f"First 100 chars: {response.text[:100]}")
            return []

        if isinstance(data, dict):
            items = data.get("Table", [])
        elif isinstance(data, list):
            items = data
        else:
            logger.error(f"Unexpected BSE API response format: {type(data)}")
            return []

        if not items:
            logger.warning("BSE API returned empty results.")
            return []

        for item in items[:50]:
            if not isinstance(item, dict):
                continue

            attachment = str(item.get("ATTACHMENTNAME", "")).strip()
            pdf_url = ""
            if attachment:
                pdf_url = f"https://www.bseindia.com/xml-data/corpfiling/AttachLive/{attachment}"

            raw_data.append({
                "date":    str(item.get("NEWS_DT", ""))[:10],
                "company": str(item.get("SLONGNAME", "N/A")).strip(),
                "subject": str(item.get("NEWSSUB", "N/A")).strip(),
                "symbol":  str(item.get("SCRIP_CD", "N/A")),
                "pdf_url": pdf_url,
                "source":  "BSE"
            })

    except requests.exceptions.HTTPError as e:
        logger.error(f"BSE API HTTP error: {e}")
    except requests.exceptions.Timeout:
        logger.error("BSE API timed out.")
    except Exception as e:
        logger.error(f"BSE API unexpected error: {e}", exc_info=False)

    return raw_data


# ─────────────────────────────────────────────
# STEP 2: Fallback — Scrape BSE HTML page
# ─────────────────────────────────────────────
def fetch_bse_via_scraper() -> List[Dict]:
    raw_data = []
    for attempt in range(2):
        try:
            response = requests.get(BSE_FALLBACK_URL, headers=HEADERS, timeout=25)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            table = None
            selectors = [
                ("table", {"id": "ctl00_ContentPlaceHolder1_gvAnn"}),
                ("table", {"class": "announcement-table"}),
                ("table", {"summary": "Announcements"}),
            ]

            for tag, attrs in selectors:
                table = soup.find(tag, attrs)
                if table:
                    logger.info(f"Found table with selector: {attrs}")
                    break

            if table:
                rows = table.find_all("tr")[1:51]
                for row in rows:
                    cols = row.find_all("td")
                    if len(cols) >= 4:
                        pdf_url = ""
                        link_tag = cols[2].find("a")
                        if link_tag and link_tag.get("href"):
                            href = link_tag["href"]
                            pdf_url = href if href.startswith("http") else f"https://www.bseindia.com{href}"

                        raw_data.append({
                            "date":    cols[3].get_text(strip=True)[:10],
                            "company": cols[1].get_text(strip=True),
                            "subject": cols[2].get_text(strip=True),
                            "symbol":  cols[0].get_text(strip=True),
                            "pdf_url": pdf_url,
                            "source":  "BSE"
                        })
                break
            else:
                logger.warning("BSE scraper: Announcement table not found.")
                if attempt == 0:
                    logger.warning("Retrying with different selectors...")
                    time.sleep(2)

        except Exception as e:
            if attempt == 0:
                logger.warning(f"BSE scraper attempt 1 failed: {e}. Retrying...")
                time.sleep(2)
            else:
                logger.error(f"BSE scraper failed after 2 attempts: {e}")

    return raw_data


# ─────────────────────────────────────────────
# STEP 3: Main entry point
# ─────────────────────────────────────────────
def get_bse_announcements() -> List[Dict]:
    logger.info("Attempting BSE API fetch...")
    raw = fetch_bse_via_api()

    if not raw:
        logger.warning("BSE API returned nothing. Falling back to HTML scraper...")
        raw = fetch_bse_via_scraper()

    if not raw:
        logger.warning("BSE: No announcements fetched from any source.")
        return []

    filtered = process_announcements(raw)
    logger.info(f"BSE: {len(raw)} fetched, {len(filtered)} passed filter.")
    return filtered


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = get_bse_announcements()
    if results:
        print(f"\nBSE Filtered Results ({len(results)}):\n")
        for r in results:
            print(f"  [{r['date']}] {r['company']} ({r['symbol']})")
            print(f"           {r['subject']}")
            if r['pdf_url']:
                print(f"           {r['pdf_url']}")
            print()
    else:
        print("No relevant BSE announcements found.")
