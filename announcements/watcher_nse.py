import requests
import logging
from bs4 import BeautifulSoup
from typing import List, Dict
from announcements.filters import process_announcements

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.nseindia.com/",
    "Accept-Language": "en-US,en;q=0.9",
}

NSE_URL = "https://www.nseindia.com/api/corporates-corporateActions?index=equities"

# ─────────────────────────────────────────────
# STEP 1: Establish NSE session with cookies
# ─────────────────────────────────────────────
def get_nse_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS)
    # NSE requires visiting the homepage first to set cookies
    session.get("https://www.nseindia.com", timeout=15)
    return session


# ─────────────────────────────────────────────
# STEP 2: Fetch raw announcements from NSE API
# ─────────────────────────────────────────────
def fetch_raw_nse_announcements(session: requests.Session) -> List[Dict]:
    raw_data = []
    try:
        response = session.get(NSE_URL, timeout=20)
        response.raise_for_status()
        data = response.json()

        for item in data[:50]:  # limit to latest 50
            attachment = item.get("attachment", "")
            pdf_url = ""
            if attachment:
                pdf_url = f"https://www.nseindia.com{attachment}"

            raw_data.append({
                "date":    str(item.get("date", ""))[:10],
                "company": str(item.get("companyName", item.get("symbol", "N/A"))).strip(),
                "subject": str(item.get("subject", "N/A")).strip(),
                "symbol":  str(item.get("symbol", "N/A")).strip(),
                "pdf_url": pdf_url,
                "source":  "NSE"
            })

    except requests.exceptions.HTTPError as e:
        logger.error(f"NSE API HTTP error: {e}")
    except requests.exceptions.Timeout:
        logger.error("NSE API timed out.")
    except Exception as e:
        logger.error(f"NSE API unexpected error: {e}", exc_info=False)

    return raw_data


# ─────────────────────────────────────────────
# STEP 3: Fallback — Scrape NSE HTML page
# ─────────────────────────────────────────────
def fetch_raw_nse_announcements_html(session: requests.Session) -> List[Dict]:
    raw_data = []
    html_url = "https://www.nseindia.com/companies-listing/corporate-filing-compressed"
    try:
        response = session.get(html_url, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        rows = soup.select("table tbody tr")
        for row in rows[:50]:
            cols = row.find_all("td")
            if len(cols) >= 4:
                pdf_url = ""
                link = cols[2].find("a")
                if link and link.get("href"):
                    href = link["href"]
                    pdf_url = href if href.startswith("http") else f"https://www.nseindia.com{href}"

                raw_data.append({
                    "date":    cols[3].get_text(strip=True)[:10],
                    "company": cols[1].get_text(strip=True),
                    "subject": cols[2].get_text(strip=True),
                    "symbol":  cols[0].get_text(strip=True),
                    "pdf_url": pdf_url,
                    "source":  "NSE"
                })

    except Exception as e:
        logger.error(f"NSE HTML scraper error: {e}")

    return raw_data


# ─────────────────────────────────────────────
# STEP 4: Main entry point
# ─────────────────────────────────────────────
def get_nse_announcements() -> List[Dict]:
    session = get_nse_session()
    raw = fetch_raw_nse_announcements(session)

    if not raw:
        logger.warning("NSE API returned nothing. Trying HTML scraper...")
        raw = fetch_raw_nse_announcements_html(session)

    if not raw:
        logger.warning("NSE: No announcements fetched from any source.")
        return []

    filtered = process_announcements(raw)
    logger.info(f"NSE: {len(raw)} fetched, {len(filtered)} passed filter.")
    return filtered


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = get_nse_announcements()
    if results:
        print(f"\nNSE Filtered Results ({len(results)}):\n")
        for r in results:
            print(f"  [{r['date']}] {r['company']} ({r['symbol']})")
            print(f"           {r['subject']}")
            if r['pdf_url']:
                print(f"           {r['pdf_url']}")
            print()
    else:
        print("No relevant NSE announcements found.")
