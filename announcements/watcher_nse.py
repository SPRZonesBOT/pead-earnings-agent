import logging
import time
from datetime import datetime
from typing import List, Dict

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# NSE Configuration
# ─────────────────────────────────────────────────────────────

NSE_BASE_URL = "https://www.nseindia.com"
NSE_ANNOUNCEMENTS_URL = f"{NSE_BASE_URL}/corporate/boardMeetings.jsp"
NSE_API_URL = "https://www.nseindia.com/api/corporate-announcements"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": NSE_BASE_URL,
}


# ─────────────────────────────────────────────────────────────
# Utility Functions
# ─────────────────────────────────────────────────────────────

def _safe_text(val) -> str:
    """Safely convert any value to trimmed string."""
    if val is None:
        return ""
    return str(val).strip()


def _parse_date(date_str: str) -> str:
    """
    Parse various date formats to DD-MM-YYYY.
    
    Tries:
    - 'dd-MMM-yyyy'  (e.g., '07-Jun-2025')
    - 'DD/MM/YYYY'   (e.g., '07/06/2025')
    - 'YYYY-MM-DD'   (e.g., '2025-06-07')
    - ISO format
    
    Returns DD-MM-YYYY or original string if parsing fails.
    """
    if not date_str:
        return ""

    date_str = _safe_text(date_str)
    formats = [
        "%d-%b-%Y",      # 07-Jun-2025
        "%d-%B-%Y",      # 07-June-2025
        "%d/%m/%Y",      # 07/06/2025
        "%d-%m-%Y",      # 07-06-2025
        "%Y-%m-%d",      # 2025-06-07
        "%Y/%m/%d",      # 2025/06/07
        "%d %b %Y",      # 07 Jun 2025
    ]

    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str, fmt)
            return parsed.strftime("%d-%m-%Y")
        except ValueError:
            continue

    # Return original if nothing matched
    return date_str[:10]


def _build_pdf_url(attachment: str) -> str:
    """Build full PDF URL from attachment reference."""
    if not attachment or not _safe_text(attachment):
        return ""
    
    attachment = _safe_text(attachment)
    
    # If already a full URL, return as is
    if attachment.startswith("http"):
        return attachment
    
    # Common NSE PDF URL patterns
    patterns = [
        f"{NSE_BASE_URL}/corporates/xml-data/corpfiling/Announcements/{attachment}",
        f"{NSE_BASE_URL}/corporates/xml-data/corpfiling/{attachment}",
        f"{NSE_BASE_URL}/corporate/boardMeetings/{attachment}",
    ]
    
    return patterns[0]


# ─────────────────────────────────────────────────────────────
# METHOD 1: NSE Official API
# ─────────────────────────────────────────────────────────────

def fetch_nse_api() -> List[Dict]:
    """Fetch from NSE official corporate announcements API."""
    raw = []
    try:
        session = requests.Session()
        session.headers.update(HEADERS)
        
        # Get cookies from main site first
        session.get(NSE_BASE_URL, timeout=10)
        time.sleep(1)

        # Try API endpoint
        logger.info("NSE API: Attempting official API...")
        resp = session.get(NSE_API_URL, timeout=20)
        resp.raise_for_status()

        if not resp.text.strip():
            logger.warning("NSE API: Empty response.")
            return []

        try:
            data = resp.json()
        except ValueError:
            logger.warning("NSE API: Invalid JSON response.")
            return []

        # Handle various response structures
        items = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("data", data.get("announcements", data.get("records", [])))

        logger.info(f"NSE API: Parsing {len(items)} items...")

        for item in items[:100]:
            if not isinstance(item, dict):
                continue

            # Map common field names
            date = _parse_date(
                item.get("date") or 
                item.get("announcementDate") or 
                item.get("DATE") or 
                ""
            )
            
            company = _safe_text(
                item.get("company") or 
                item.get("companyName") or 
                item.get("COMPANY_NAME") or 
                item.get("NAME") or 
                "N/A"
            )
            
            symbol = _safe_text(
                item.get("symbol") or 
                item.get("Symbol") or 
                item.get("SYMBOL") or 
                item.get("isin_code") or 
                ""
            )
            
            subject = _safe_text(
                item.get("subject") or 
                item.get("announcement") or 
                item.get("SUBJECT") or 
                item.get("subject_of_communication") or 
                "N/A"
            )
            
            pdf_url = _build_pdf_url(
                item.get("attachmentName") or 
                item.get("attachment") or 
                item.get("file") or 
                item.get("pdf") or 
                ""
            )

            if not date or not company:
                continue

            raw.append({
                "date": date,
                "company": company,
                "symbol": symbol,
                "subject": subject,
                "pdf_url": pdf_url,
                "source": "NSE",
            })

        logger.info(f"NSE API: Successfully parsed {len(raw)} items.")
    except Exception as e:
        logger.debug(f"NSE API failed: {e}")

    return raw


# ─────────────────────────────────────────────────────────────
# METHOD 2: NSE HTML Scraper (BeautifulSoup)
# ─────────────────────────────────────────────────────────────

def fetch_nse_scraper() -> List[Dict]:
    """Scrape NSE announcements page using BeautifulSoup."""
    raw = []
    
    urls = [
        "https://www.nseindia.com/corporate/boardMeetings.jsp",
        "https://www.nseindia.com/corporates/announcements.jsp",
    ]

    for url in urls:
        try:
            logger.info(f"NSE Scraper: Trying {url}...")
            session = requests.Session()
            session.headers.update(HEADERS)
            session.get(NSE_BASE_URL, timeout=10)
            time.sleep(1)

            resp = session.get(url, timeout=25)
            resp.raise_for_status()
            resp.encoding = 'utf-8'

            soup = BeautifulSoup(resp.text, "html.parser")

            # Try multiple table selectors
            table = None
            for selector in [
                "table.announce-table",
                "table#corporateAnnouncement",
                "table[class*='announce']",
                "table[class*='board']",
                "table",
            ]:
                tables = soup.select(selector)
                if tables:
                    table = tables[0]
                    break

            if not table:
                logger.debug(f"NSE Scraper: No table found at {url}")
                continue

            rows = table.find_all("tr")[1:101]  # Skip header, max 100 rows
            logger.info(f"NSE Scraper: Found {len(rows)} rows.")

            for row in rows:
                try:
                    cols = row.find_all("td")
                    if len(cols) < 3:
                        continue

                    # Extract fields
                    date_cell = cols[0].get_text(strip=True) if len(cols) > 0 else ""
                    symbol_cell = cols[1].get_text(strip=True) if len(cols) > 1 else ""
                    company_cell = cols[2].get_text(strip=True) if len(cols) > 2 else ""
                    subject_cell = cols[3].get_text(strip=True) if len(cols) > 3 else ""

                    # Try to find PDF link
                    pdf_url = ""
                    link = row.find("a")
                    if link and link.get("href"):
                        href = link.get("href")
                        if href.startswith("http"):
                            pdf_url = href
                        else:
                            pdf_url = f"{NSE_BASE_URL}{href}"

                    date = _parse_date(date_cell)
                    if not date:
                        continue

                    raw.append({
                        "date": date,
                        "company": company_cell or "N/A",
                        "symbol": symbol_cell or "",
                        "subject": subject_cell or "N/A",
                        "pdf_url": pdf_url,
                        "source": "NSE",
                    })

                except Exception as e:
                    logger.debug(f"NSE Scraper: Row parsing error: {e}")
                    continue

            if raw:
                logger.info(f"NSE Scraper: Successfully parsed {len(raw)} items from {url}.")
                break

        except Exception as e:
            logger.debug(f"NSE Scraper failed for {url}: {e}")
            time.sleep(2)
            continue

    return raw


# ─────────────────────────────────────────────────────────────
# Main Entry Point
# ─────────────────────────────────────────────────────────────

def get_nse_announcements() -> List[Dict]:
    """
    Fetch NSE announcements using multiple fallback methods.
    
    Returns: List of dicts with keys:
        - date (DD-MM-YYYY)
        - company
        - symbol
        - subject
        - pdf_url
        - source ('NSE')
    """
    logger.info("=" * 60)
    logger.info("NSE Announcement Fetch Started")
    logger.info("=" * 60)

    all_results: List[Dict] = []

    # Try API first
    logger.info("NSE: Trying official API...")
    api_results = fetch_nse_api()
    if api_results:
        all_results = api_results
        logger.info(f"✅ NSE API succeeded: {len(api_results)} items")
    else:
        logger.info("⚠️  NSE API returned nothing, trying scraper...")
        scraper_results = fetch_nse_scraper()
        if scraper_results:
            all_results = scraper_results
            logger.info(f"✅ NSE Scraper succeeded: {len(scraper_results)} items")
        else:
            logger.error("❌ NSE: All methods failed, returning empty.")

    if not all_results:
        logger.warning("NSE: No data fetched from any source.")
        return []

    # Import and apply filters
    try:
        from announcements.filters import process_announcements
        filtered = process_announcements(all_results)
        logger.info(f"NSE: {len(all_results)} fetched → {len(filtered)} passed filters")
        return filtered
    except ImportError:
        logger.warning("NSE: filters module not found, returning raw results.")
        return all_results


# ─────────────────────────────────────────────────────────────
# Test/Debug
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    results = get_nse_announcements()
    
    print("\n" + "=" * 80)
    print(f"{'NSE TEST RESULTS':^80}")
    print("=" * 80)
    
    for idx, item in enumerate(results[:10], 1):
        print(f"\n#{idx}")
        print(f"  Date    : {item.get('date', 'N/A')}")
        print(f"  Company : {item.get('company', 'N/A')}")
        print(f"  Symbol  : {item.get('symbol', 'N/A')}")
        print(f"  Subject : {item.get('subject', 'N/A')}")
        if item.get('pdf_url'):
            print(f"  PDF     : {item.get('pdf_url', 'N/A')}")
