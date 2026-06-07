"""
watcher_nse.py — NSE Corporate Announcements Fetcher

Uses multiple fallback methods:
  1. jugaad-data library (if installed)
  2. NSE RSS Feed (FeedBurner)
  3. NSE Official API with session
  4. HTML Scraper (BeautifulSoup)

Returns: List[Dict] with keys: date, company, symbol, subject, pdf_url, source
"""

import logging
import re
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────

NSE_BASE_URL = "https://www.nseindia.com"

# RSS Feed URLs (FeedBurner — most reliable)
RSS_FEEDS = {
    "announcements": "http://feeds.feedburner.com/nseindia/ann",
    "board_meetings": "http://feeds.feedburner.com/nseindia/boardmeet",
    "financial_results": "http://feeds.feedburner.com/nseindia/results",
    "corporate_actions": "http://feeds.feedburner.com/nseindia/ca",
}

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
    
    Supports:
    - 'dd-MMM-yyyy'  (07-Jun-2025)
    - 'dd MMM yyyy'  (07 Jun 2025)
    - 'DD/MM/YYYY'   (07/06/2025)
    - 'YYYY-MM-DD'   (2025-06-07)
    - 'DD-MM-YYYY'   (07-06-2025)
    - 'YYYY/MM/DD'   (2025/06/07)
    - 'DD Month YYYY' (07 June 2025)
    - RFC 2822       (Sat, 07 Jun 2025 12:00:00 +0530)
    """
    if not date_str:
        return ""

    date_str = _safe_text(date_str)

    # Try common date formats first
    formats = [
        "%d-%b-%Y",        # 07-Jun-2025
        "%d-%B-%Y",        # 07-June-2025
        "%d %b %Y",        # 07 Jun 2025
        "%d %B %Y",        # 07 June 2025
        "%d/%m/%Y",        # 07/06/2025
        "%d-%m-%Y",        # 07-06-2025
        "%Y-%m-%d",        # 2025-06-07
        "%Y/%m/%d",        # 2025/06/07
        "%Y-%m-%dT%H:%M:%S%z",  # ISO 2025-06-07T12:00:00+0530
        "%Y-%m-%dT%H:%M:%S.%f%z",  # ISO with microseconds
        "%a, %d %b %Y %H:%M:%S %z",  # RFC 2822
        "%a, %d %B %Y %H:%M:%S %z",  # RFC 2822 (full month)
    ]

    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str.strip(), fmt)
            return parsed.strftime("%d-%m-%Y")
        except (ValueError, TypeError):
            continue

    # Try to extract date pattern using regex
    patterns = [
        r"(\d{2})-(\w{3})-(\d{4})",    # 07-Jun-2025
        r"(\d{2})/(\d{2})/(\d{4})",    # 07/06/2025
        r"(\d{4})-(\d{2})-(\d{2})",    # 2025-06-07
        r"(\d{2})-(\d{2})-(\d{4})",    # 07-06-2025
    ]

    for pattern in patterns:
        match = re.search(pattern, date_str)
        if match:
            try:
                return datetime.strptime(match.group(0), pattern.replace(r"(\w{3})", "%b").replace(r"(\d{2})", "%d").replace(r"(\d{4})", "%Y")).strftime("%d-%m-%Y")
            except (ValueError, IndexError):
                continue

    # Return first 10 chars as fallback
    return date_str[:10]


def _extract_symbol(company_name: str, title: str = "") -> str:
    """Extract stock symbol from company name or title."""
    text = f"{company_name} {title}".upper().strip()
    
    # Common patterns: "SYMBOL: RELIANCE", "RELIANCE - Board Meeting", etc.
    symbol_match = re.search(r'SYMBOL[:\s]*(\w+)', text)
    if symbol_match:
        return symbol_match.group(1)
    
    # Try to extract from common NSE symbol patterns
    known_symbols = [
        "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR",
        "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK", "LT", "WIPRO", "AXISBANK",
        "BAJFINANCE", "TITAN", "ASIANPAINT", "MARUTI", "SUNPHARMA", "HCLTECH",
        "ULTRACEMCO", "NTPC", "M&M", "ONGC", "POWERGRID", "TATAMOTORS",
        "TATASTEEL", "BAJAJFINSV", "JSWSTEEL", "ADANIPORTS", "NESTLEIND",
        "DMART", "TRENT", "ADANIENT", "HAL", "ZOMATO", "ICICIPRULI",
        "COLPAL", "HAVELLS", "DLF", "BPCL", "HINDALCO", "GODREJCP",
        "EICHERMOT", "BRITANNIA", "SHREECEM", "HEROMOTOCO", "PIDILITIND",
        "TATACONSUM", "DIVISLAB", "SBILIFE", "DRREDDY", "BAJAJ-AUTO",
        "GRASIM", "HDFCLIFE", "INDUSINDBK", "CIPLA", "ABHIBOT",
    ]
    
    for sym in known_symbols:
        if sym in text:
            return sym
    
    # Try to extract first alphanumeric word as symbol
    words = text.split()
    for word in words:
        if word.isupper() and len(word) >= 2 and not word.startswith("THE"):
            return word
    
    return ""


def _build_pdf_url(link: str) -> str:
    """Build full PDF URL from various link formats."""
    if not link or not _safe_text(link):
        return ""
    
    link = _safe_text(link)
    
    # Already a full URL
    if link.startswith("http://") or link.startswith("https://"):
        return link
    
    # Relative URL
    if link.startswith("/"):
        return f"{NSE_BASE_URL}{link}"
    
    # NSE archive file path
    if link.startswith("corporate/") or link.startswith("xml-data/"):
        return f"{NSE_BASE_URL}/{link}"
    
    # Just filename
    return f"{NSE_BASE_URL}/corporates/xml-data/corpfiling/Announcements/{link}"


def _get_nse_session() -> Optional[object]:
    """Create a requests session with NSE cookies."""
    try:
        session = __import__("requests").Session()
        session.headers.update(HEADERS)
        
        # Visit main site to get cookies
        resp = session.get(NSE_BASE_URL, timeout=15)
        resp.raise_for_status()
        time.sleep(1)
        
        return session
    except Exception as e:
        logger.debug(f"NSE session creation failed: {e}")
        return None


# ═════════════════════════════════════════════════════════════
# METHOD 1: jugaad-data Library (Most Reliable)
# ═════════════════════════════════════════════════════════════

def fetch_jugaad_data() -> List[Dict]:
    """
    Fetch corporate announcements using jugaad-data library.
    
    Install: pip install jugaad-data
    """
    try:
        from jugaad_data.nse import NSELive
    except ImportError:
        logger.info("jugaad-data not installed. Skipping Method 1.")
        return []

    raw = []
    try:
        logger.info("📦 Method 1: Trying jugaad-data library...")
        n = NSELive()
        announcements = n.corporate_announcements()

        if not announcements:
            logger.warning("jugaad-data: No announcements returned.")
            return []

        logger.info(f"jugaad-data: Got {len(announcements)} announcements.")

        for item in announcements[:100]:
            if not isinstance(item, dict):
                continue

            date = _parse_date(
                item.get("date") or 
                item.get("dt") or 
                item.get("ann_date") or 
                ""
            )
            
            company = _safe_text(
                item.get("company") or 
                item.get("comp_name") or 
                item.get("symbol") or 
                item.get("name") or 
                "N/A"
            )
            
            symbol = _safe_text(
                item.get("symbol") or 
                item.get("sym") or 
                item.get("ticker") or 
                ""
            )
            
            subject = _safe_text(
                item.get("subject") or 
                item.get("desc") or 
                item.get("description") or 
                item.get("title") or 
                "N/A"
            )
            
            pdf_url = _build_pdf_url(
                item.get("pdf_url") or 
                item.get("attachment") or 
                item.get("link") or 
                item.get("url") or 
                ""
            )

            # Extract symbol from company name if not found
            if not symbol:
                symbol = _extract_symbol(company, subject)

            if not date:
                continue

            raw.append({
                "date": date,
                "company": company,
                "symbol": symbol,
                "subject": subject,
                "pdf_url": pdf_url,
                "source": "NSE",
            })

        logger.info(f"✅ Method 1 (jugaad-data): {len(raw)} items parsed.")
    except Exception as e:
        logger.debug(f"Method 1 (jugaad-data) failed: {e}")

    return raw


# ═════════════════════════════════════════════════════════════
# METHOD 2: NSE RSS Feed (FeedBurner)
# ═════════════════════════════════════════════════════════════

def fetch_rss_feed(feed_type: str = "announcements") -> List[Dict]:
    """
    Fetch corporate announcements from NSE RSS Feed.
    
    Args:
        feed_type: 'announcements', 'board_meetings', 'financial_results', 'corporate_actions'
    """
    try:
        import feedparser
    except ImportError:
        logger.info("feedparser not installed. Try: pip install feedparser")
        return []

    rss_url = RSS_FEEDS.get(feed_type, RSS_FEEDS["announcements"])
    raw = []

    try:
        logger.info(f"📡 Method 2: Trying RSS Feed ({feed_type})...")
        logger.info(f"   URL: {rss_url}")

        feed = feedparser.parse(rss_url)

        if not feed.entries:
            logger.warning(f"RSS Feed ({feed_type}): No entries found.")
            return []

        logger.info(f"RSS Feed ({feed_type}): Got {len(feed.entries)} entries.")

        for entry in feed.entries[:50]:
            title = _safe_text(entry.get("title", ""))
            link = _safe_text(entry.get("link", ""))
            published = _safe_text(entry.get("published", entry.get("pubDate", "")))
            summary = _safe_text(entry.get("summary", entry.get("description", "")))

            # Parse date
            date = _parse_date(published)

            # Extract company from title
            company = title
            symbol = ""

            # Title format: "Company Name - Subject"
            if " - " in title:
                parts = title.split(" - ", 1)
                company = parts[0].strip()
                subject = parts[1].strip()
            else:
                subject = title

            # Extract symbol
            symbol = _extract_symbol(company, subject)

            if not date:
                continue

            raw.append({
                "date": date,
                "company": company,
                "symbol": symbol,
                "subject": subject,
                "pdf_url": link if ("nseindia" in link or "nsearchives" in link) else "",
                "source": "NSE",
            })

        logger.info(f"✅ Method 2 (RSS Feed): {len(raw)} items parsed.")
    except Exception as e:
        logger.debug(f"Method 2 (RSS Feed) failed: {e}")

    return raw


# ═════════════════════════════════════════════════════════════
# METHOD 3: NSE Official API
# ═════════════════════════════════════════════════════════════

def fetch_nse_api() -> List[Dict]:
    """Fetch from NSE official corporate announcements API."""
    raw = []

    api_urls = [
        "https://www.nseindia.com/api/corporate-announcements",
        "https://www.nseindia.com/api/board-meetings",
        "https://www.nseindia.com/api/corporate-filings",
    ]

    session = _get_nse_session()
    if not session:
        return []

    try:
        for api_url in api_urls:
            try:
                logger.info(f"🌐 Method 3: Trying NSE API ({api_url.split('/')[-1]})...")
                
                resp = session.get(api_url, timeout=20)
                resp.raise_for_status()

                if not resp.text.strip():
                    logger.warning(f"NSE API: Empty response from {api_url}")
                    continue

                try:
                    data = resp.json()
                except ValueError:
                    logger.warning(f"NSE API: Invalid JSON from {api_url}")
                    continue

                # Handle various response structures
                items = []
                if isinstance(data, list):
                    items = data
                elif isinstance(data, dict):
                    items = data.get("data", data.get("announcements", data.get("records", data.get("items", []))))

                logger.info(f"NSE API: Parsing {len(items)} items...")

                for item in items[:100]:
                    if not isinstance(item, dict):
                        continue

                    date = _parse_date(
                        item.get("date") or 
                        item.get("announcementDate") or 
                        item.get("dt") or 
                        ""
                    )
                    
                    company = _safe_text(
                        item.get("company") or 
                        item.get("companyName") or 
                        item.get("comp_name") or 
                        item.get("name") or 
                        "N/A"
                    )
                    
                    symbol = _safe_text(
                        item.get("symbol") or 
                        item.get("sym") or 
                        item.get("ticker") or 
                        ""
                    )
                    
                    subject = _safe_text(
                        item.get("subject") or 
                        item.get("announcement") or 
                        item.get("desc") or 
                        item.get("description") or 
                        "N/A"
                    )
                    
                    pdf_url = _build_pdf_url(
                        item.get("attachmentName") or 
                        item.get("attachment") or 
                        item.get("pdf") or 
                        item.get("file") or 
                        item.get("pdf_url") or 
                        ""
                    )

                    if not symbol:
                        symbol = _extract_symbol(company, subject)

                    if not date:
                        continue

                    raw.append({
                        "date": date,
                        "company": company,
                        "symbol": symbol,
                        "subject": subject,
                        "pdf_url": pdf_url,
                        "source": "NSE",
                    })

                if raw:
                    logger.info(f"✅ Method 3 (NSE API): {len(raw)} items parsed.")
                    return raw  # Return on first successful API

            except Exception as e:
                logger.debug(f"NSE API {api_url} failed: {e}")
                time.sleep(1)
                continue

    except Exception as e:
        logger.debug(f"Method 3 (NSE API) all failed: {e}")
    finally:
        try:
            session.close()
        except Exception:
            pass

    return raw


# ═════════════════════════════════════════════════════════════
# METHOD 4: HTML Scraper (BeautifulSoup)
# ═════════════════════════════════════════════════════════════

def fetch_nse_scraper() -> List[Dict]:
    """Scrape NSE announcements page using BeautifulSoup."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.info("BeautifulSoup not installed. Try: pip install beautifulsoup4")
        return []

    raw = []
    
    urls = [
        "https://www.nseindia.com/companies-listing/corporate-filings-announcements",
        "https://www.nseindia.com/corporate/boardMeetings.jsp",
        "https://www.nseindia.com/corporates/announcements.jsp",
    ]

    for url in urls:
        try:
            logger.info(f"🕸️  Method 4: Scraping {url.split('/')[-1]}...")
            
            session = _get_nse_session()
            if not session:
                continue

            resp = session.get(url, timeout=25)
            resp.raise_for_status()
            resp.encoding = 'utf-8'

            soup = BeautifulSoup(resp.text, "html.parser")

            # Try multiple table/row selectors
            rows = []
            
            # Modern NSE page — look for announcement cards/rows
            for selector in [
                "tr[class*='row']",
                "tr[class*='announce']",
                "div[class*='announce']",
                "div[class*='card']",
                "li[class*='announce']",
                "table tbody tr",
                "table tr",
            ]:
                elements = soup.select(selector)
                if elements:
                    rows = elements
                    break

            # Also try finding table by content
            if not rows:
                tables = soup.find_all("table")
                for table in tables:
                    trs = table.find_all("tr")
                    if len(trs) > 1:
                        rows = trs[1:101]  # Skip header
                        break

            if not rows:
                logger.debug(f"No rows found at {url}")
                try:
                    session.close()
                except Exception:
                    pass
                continue

            logger.info(f"Scraper: Found {len(rows)} rows.")

            for row in rows:
                try:
                    # Get all text cells
                    cols = row.find_all("td") if row.name == "tr" else row.find_all(["div", "span"])
                    if not cols:
                        continue

                    texts = [c.get_text(strip=True) for c in cols if c.get_text(strip=True)]

                    if len(texts) < 2:
                        continue

                    # Determine fields based on position
                    date_str = texts[0] if len(texts) > 0 else ""
                    company_str = texts[1] if len(texts) > 1 else ""
                    subject_str = texts[2] if len(texts) > 2 else ""

                    # Try to find PDF link
                    pdf_url = ""
                    links = row.find_all("a", href=True)
                    for link in links:
                        href = link.get("href", "")
                        if "nseindia" in href or "nsearchives" in href or href.endswith(".pdf"):
                            pdf_url = href if href.startswith("http") else f"{NSE_BASE_URL}{href}"
                            break

                    date = _parse_date(date_str)
                    if not date:
                        continue

                    symbol = _extract_symbol(company_str, subject_str)

                    raw.append({
                        "date": date,
                        "company": company_str,
                        "symbol": symbol,
                        "subject": subject_str or "N/A",
                        "pdf_url": pdf_url,
                        "source": "NSE",
                    })

                except Exception as e:
                    logger.debug(f"Row parsing error: {e}")
                    continue

            if raw:
                logger.info(f"✅ Method 4 (Scraper): {len(raw)} items parsed from {url.split('/')[-1]}.")
                try:
                    session.close()
                except Exception:
                    pass
                return raw

            try:
                session.close()
            except Exception:
                pass
            time.sleep(2)

        except Exception as e:
            logger.debug(f"Scraper failed for {url}: {e}")
            time.sleep(2)
            continue

    return raw


# ═════════════════════════════════════════════════════════════
# Main Entry Point
# ═════════════════════════════════════════════════════════════

def get_nse_announcements() -> List[Dict]:
    """
    Fetch NSE announcements using multiple fallback methods.
    
    Returns: List[Dict] with keys:
        - date (DD-MM-YYYY)
        - company
        - symbol
        - subject
        - pdf_url
        - source ('NSE')
    """
    logger.info("=" * 60)
    logger.info("📢 NSE Announcement Fetch Started")
    logger.info("=" * 60)

    all_results: List[Dict] = []

    # ─── Method 1: jugaad-data (Most Reliable) ────────────────
    results = fetch_jugaad_data()
    if results:
        all_results = results
        logger.info(f"✅ Used Method 1 (jugaad-data): {len(results)} items")
    else:
        # ─── Method 2: RSS Feed ────────────────────────────────
        for feed_type in ["announcements", "board_meetings", "financial_results"]:
            results = fetch_rss_feed(feed_type)
            if results:
                all_results.extend(results)
                logger.info(f"✅ Used Method 2 (RSS/{feed_type}): {len(results)} items")
                break  # Success with first feed

    if not all_results:
        # ─── Method 3: NSE API ─────────────────────────────────
        results = fetch_nse_api()
        if results:
            all_results = results
            logger.info(f"✅ Used Method 3 (NSE API): {len(results)} items")

    if not all_results:
        # ─── Method 4: HTML Scraper ────────────────────────────
        results = fetch_nse_scraper()
        if results:
            all_results = results
            logger.info(f"✅ Used Method 4 (Scraper): {len(results)} items")

    if not all_results:
        logger.error("❌ NSE: All methods failed. Returning empty list.")
        return []

    logger.info(f"📊 NSE: Total unique items: {len(all_results)}")

    # Deduplicate by (date, company, subject)
    seen = set()
    unique_results = []
    for item in all_results:
        key = (item["date"], item["company"], item["subject"][:50])
        if key not in seen:
            seen.add(key)
            unique_results.append(item)

    logger.info(f"📊 NSE: After dedup: {len(unique_results)} items")

    # Apply filters
    try:
        from announcements.filters import process_announcements
        filtered = process_announcements(unique_results)
        logger.info(f"📊 NSE: {len(unique_results)} fetched → {len(filtered)} passed filters")
        return filtered
    except ImportError:
        logger.warning("NSE: filters module not found, returning deduped results.")
        return unique_results
    except Exception as e:
        logger.warning(f"NSE: Filter error: {e}, returning deduped results.")
        return unique_results


# ═════════════════════════════════════════════════════════════
# Test/Debug
# ═════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    results = get_nse_announcements()
    
    print("\n" + "=" * 80)
    print(f"{'📢 NSE TEST RESULTS':^80}")
    print("=" * 80)
    print(f"Total items: {len(results)}")
    print("=" * 80)
    
    for idx, item in enumerate(results[:15], 1):
        print(f"\n{'─' * 70}")
        print(f"  #{idx}")
        print(f"  📅 Date    : {item.get('date', 'N/A')}")
        print(f"  🏢 Company : {item.get('company', 'N/A')}")
        print(f"  🔖 Symbol  : {item.get('symbol', 'N/A')}")
        print(f"  📝 Subject : {item.get('subject', 'N/A')}")
        if item.get('pdf_url'):
            print(f"  📄 PDF     : {item.get('pdf_url', 'N/A')}")
    
    print(f"\n{'─' * 70}")
    print(f"✅ DONE — {len(results)} announcements fetched.")
