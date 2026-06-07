"""
watcher_nse.py — NSE Corporate Announcements Fetcher

Uses multiple fallback methods:
  1. jugaad-data library (most reliable — preferred)
  2. NSE RSS Feed (FeedBurner)
  3. NSE Official API with session
  4. HTML Scraper (BeautifulSoup)

Returns: List[Dict] with keys: date, company, symbol, subject, pdf_url, source
"""

import logging
import re
import time
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────

NSE_BASE_URL = "https://www.nseindia.com"

# RSS Feed URLs — confirmed from www.nseindia.com/static/rss-feed
RSS_FEEDS = {
    "announcements":     "http://feeds.feedburner.com/nseindia/ann",
    "board_meetings":    "http://feeds.feedburner.com/nseindia/boardmeet",
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
      - jugaad-data : DDMMYYYYHH  (e.g. 0706202612 → 07-06-2026)
      - dd-MMM-yyyy : 07-Jun-2025
      - dd/MM/yyyy  : 07/06/2025
      - yyyy-MM-dd  : 2025-06-07
      - RFC 2822    : Sat, 07 Jun 2025 12:00:00 +0530
    """
    if not date_str:
        return ""

    date_str = _safe_text(date_str).strip()

    # ── jugaad-data format: DDMMYYYYHH or DDMMYYYY (8–11 digits) ──
    if date_str.isdigit() and len(date_str) >= 8:
        try:
            day   = date_str[0:2]
            month = date_str[2:4]
            year  = date_str[4:8]
            d, m, y = int(day), int(month), int(year)
            if 1 <= d <= 31 and 1 <= m <= 12 and 1990 <= y <= 2100:
                return f"{day}-{month}-{year}"
        except (ValueError, IndexError):
            pass

    # ── Standard text-based date formats ──
    formats = [
        "%d-%b-%Y",               # 07-Jun-2025
        "%d-%B-%Y",               # 07-June-2025
        "%d %b %Y",               # 07 Jun 2025
        "%d %B %Y",               # 07 June 2025
        "%d/%m/%Y",               # 07/06/2025
        "%d-%m-%Y",               # 07-06-2025
        "%Y-%m-%d",               # 2025-06-07
        "%Y/%m/%d",               # 2025/06/07
        "%d %m %Y",               # 07 06 2025
        "%a, %d %b %Y %H:%M:%S %z",      # RFC 2822
        "%a, %d %B %Y %H:%M:%S %z",      # RFC 2822 full month
        "%d %b %Y %H:%M:%S",             # 07 Jun 2025 12:00:00
        "%Y-%m-%dT%H:%M:%S%z",           # ISO 8601
        "%Y-%m-%dT%H:%M:%S.%f%z",        # ISO with microseconds
    ]

    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str[:25].strip(), fmt)
            return parsed.strftime("%d-%m-%Y")
        except (ValueError, TypeError, IndexError):
            continue

    # ── Fallback: extract YYYY-MM-DD via regex ──
    match = re.search(r"(\d{4})-(\d{2})-(\d{2})", date_str)
    if match:
        return f"{match.group(3)}-{match.group(2)}-{match.group(1)}"

    # ── Last resort ──
    return date_str[:10]


def _extract_symbol(company_name: str, title: str = "") -> str:
    """Extract stock symbol from company name or title."""
    text = f"{company_name} {title}".upper().strip()

    # Direct symbol mention
    sym_match = re.search(r'SYMBOL[:\s]*(\w+)', text)
    if sym_match:
        return sym_match.group(1)

    # Isin code
    isin_match = re.search(r'[A-Z]{2}\d{2}[A-Z]{2}\d{7}', text)
    if isin_match:
        pass

    # Known symbols (top NSE 200)
    known = [
        "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
        "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK",
        "LT", "WIPRO", "AXISBANK", "BAJFINANCE", "TITAN",
        "ASIANPAINT", "MARUTI", "SUNPHARMA", "HCLTECH", "ULTRACEMCO",
        "NTPC", "M&M", "ONGC", "POWERGRID", "TATAMOTORS",
        "TATASTEEL", "BAJAJFINSV", "JSWSTEEL", "ADANIPORTS", "NESTLEIND",
        "DMART", "TRENT", "ADANIENT", "HAL", "ZOMATO",
        "COLPAL", "HAVELLS", "DLF", "BPCL", "HINDALCO",
        "GODREJCP", "EICHERMOT", "BRITANNIA", "HEROMOTOCO", "PIDILITIND",
        "TATACONSUM", "DIVISLAB", "SBILIFE", "DRREDDY", "BAJAJ-AUTO",
        "GRASIM", "HDFCLIFE", "INDUSINDBK", "CIPLA", "OLAELEC",
        "IRCTC", "VEDL", "IOC", "GAIL", "BEL",
        "RELINFRA", "INFRAINVEST", "RIL",
    ]

    for sym in known:
        if sym in text:
            return sym

    # First uppercase word (min 2 chars, not THE / LTD / LIMITED / NSE / BSE)
    skip = {"THE", "LTD", "LIMITED", "NSE", "BSE", "AND", "FOR", "OF", "IN", "COMPANY", "CORPORATION"}
    for word in text.split():
        if word.isupper() and len(word) >= 2 and word not in skip:
            return word

    return ""


def _build_pdf_url(link: str) -> str:
    """Build full PDF URL from various link formats."""
    if not link:
        return ""
    link = _safe_text(link)
    if link.startswith("http://") or link.startswith("https://"):
        return link
    if link.startswith("/"):
        return f"{NSE_BASE_URL}{link}"
    return f"{NSE_BASE_URL}/corporates/xml-data/corpfiling/Announcements/{link}"


def _get_nse_session() -> Optional[object]:
    """Create a requests session with NSE cookies."""
    import requests
    try:
        session = requests.Session()
        session.headers.update(HEADERS)
        resp = session.get(NSE_BASE_URL, timeout=15)
        resp.raise_for_status()
        time.sleep(1)
        return session
    except Exception as e:
        logger.debug(f"NSE session creation failed: {e}")
        return None


# ═════════════════════════════════════════════════════════════
# METHOD 1: jugaad-data Library ★★★★★ (Most Reliable)
# ═════════════════════════════════════════════════════════════

def fetch_jugaad_data() -> List[Dict]:
    """
    Fetch corporate announcements using jugaad-data library.

    Install: pip install jugaad-data
    
    jugaad-data returns dict with keys:
      - symbol/sym: Stock symbol
      - company/companyName/compName: Company name
      - desc: Description/Subject
      - dt/date: Date in DDMMYYYYHH format
      - att/attachment/pdf_url: PDF link
    """
    try:
        from jugaad_data.nse import NSELive
    except ImportError:
        logger.info("jugaad-data not installed. Install with: pip install jugaad-data")
        return []

    raw = []
    try:
        logger.info("📦 Method 1 (jugaad-data): Fetching...")
        n = NSELive()
        announcements = n.corporate_announcements()

        if not announcements:
            logger.warning("jugaad-data: No announcements returned.")
            return []

        logger.info(f"jugaad-data: Got {len(announcements)} items.")

        for item in announcements[:150]:
            if not isinstance(item, dict):
                continue

            # ⭐ Extract fields from jugaad-data
            symbol = _safe_text(item.get("symbol", item.get("sym", "")))
            
            # Company name — try multiple fields
            company = _safe_text(
                item.get("company", 
                item.get("companyName", 
                item.get("compName", 
                item.get("comp_name", symbol))))  # Fallback to symbol
            )
            
            # If company still empty, skip
            if not company or company == "":
                company = symbol if symbol else "Unknown"
            
            subject = _safe_text(item.get("desc", item.get("description", item.get("subject", "N/A"))))
            date_str = str(item.get("dt", item.get("date", "")))
            pdf_url = _build_pdf_url(item.get("att", item.get("attachment", item.get("pdf_url", ""))))

            date = _parse_date(date_str)
            if not date or date == date_str[:10]:
                continue

            if not symbol:
                symbol = _extract_symbol(company, subject)

            raw.append({
                "date": date,
                "company": company,
                "symbol": symbol if symbol else "N/A",
                "subject": subject,
                "pdf_url": pdf_url,
                "source": "NSE",
            })

        logger.info(f"✅ Method 1 (jugaad-data): {len(raw)} items parsed.")
    except Exception as e:
        logger.debug(f"Method 1 (jugaad-data) failed: {e}")

    return raw


# ═════════════════════════════════════════════════════════════
# METHOD 2: NSE RSS Feed (FeedBurner) ★★★★☆
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
        logger.info("feedparser not installed. Install with: pip install feedparser")
        return []

    rss_url = RSS_FEEDS.get(feed_type, RSS_FEEDS["announcements"])
    raw = []

    try:
        logger.info(f"📡 Method 2 (RSS/{feed_type}): Fetching...")
        feed = feedparser.parse(rss_url)

        if not feed.entries:
            logger.warning(f"RSS Feed ({feed_type}): No entries found.")
            return []

        logger.info(f"RSS Feed ({feed_type}): {len(feed.entries)} entries.")

        for entry in feed.entries[:50]:
            title     = _safe_text(entry.get("title", ""))
            link      = _safe_text(entry.get("link", ""))
            published = _safe_text(entry.get("published", entry.get("pubDate", "")))
            summary   = _safe_text(entry.get("summary", entry.get("description", "")))

            date = _parse_date(published)

            # Title format: "Company Name - Subject"
            if " - " in title:
                parts   = title.split(" - ", 1)
                company = parts[0].strip()
                subject = parts[1].strip()
            else:
                company = title
                subject = title

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

        logger.info(f"✅ Method 2 (RSS/{feed_type}): {len(raw)} items parsed.")
    except Exception as e:
        logger.debug(f"Method 2 (RSS Feed) failed: {e}")

    return raw


# ═════════════════════════════════════════════════════════════
# METHOD 3: NSE Official API ★★★☆☆
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
                api_name = api_url.split("/")[-1]
                logger.info(f"🌐 Method 3 (API/{api_name}): Fetching...")

                resp = session.get(api_url, timeout=20)
                resp.raise_for_status()

                if not resp.text.strip():
                    logger.warning(f"NSE API: Empty response.")
                    continue

                try:
                    data = resp.json()
                except ValueError:
                    logger.warning(f"NSE API: Invalid JSON.")
                    continue

                items = []
                if isinstance(data, list):
                    items = data
                elif isinstance(data, dict):
                    items = data.get("data",
                            data.get("announcements",
                                data.get("records",
                                    data.get("items", []))))

                if not items:
                    continue

                logger.info(f"NSE API: {len(items)} items.")

                for item in items[:100]:
                    if not isinstance(item, dict):
                        continue

                    date    = _parse_date(item.get("date", item.get("announcementDate", "")))
                    company = _safe_text(item.get("company", item.get("companyName", "N/A")))
                    symbol  = _safe_text(item.get("symbol", item.get("sym", "")))
                    subject = _safe_text(item.get("subject", item.get("announcement", "N/A")))
                    pdf_url = _build_pdf_url(item.get("attachmentName", item.get("attachment", "")))

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
                    logger.info(f"✅ Method 3 (API/{api_name}): {len(raw)} items.")
                    return raw

            except Exception as e:
                logger.debug(f"NSE API attempt failed: {e}")
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
# METHOD 4: HTML Scraper (BeautifulSoup) ★★☆☆☆
# ═════════════════════════════════════════════════════════════

def fetch_nse_scraper() -> List[Dict]:
    """Scrape NSE announcements page using BeautifulSoup."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.info("BeautifulSoup not installed. Install with: pip install beautifulsoup4")
        return []

    raw = []

    urls = [
        "https://www.nseindia.com/companies-listing/corporate-filings-announcements",
        "https://www.nseindia.com/corporate/boardMeetings.jsp",
    ]

    for url in urls:
        try:
            page_name = url.split("/")[-1].split(".")[0]
            logger.info(f"🕸️  Method 4 (Scraper/{page_name}): Fetching...")

            session = _get_nse_session()
            if not session:
                continue

            resp = session.get(url, timeout=25)
            resp.raise_for_status()
            resp.encoding = 'utf-8'

            soup = BeautifulSoup(resp.text, "html.parser")

            rows = []
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

            if not rows:
                for table in soup.find_all("table"):
                    trs = table.find_all("tr")
                    if len(trs) > 1:
                        rows = trs[1:101]
                        break

            if not rows:
                logger.debug(f"No rows found at {url}")
                session.close()
                continue

            logger.info(f"Scraper: {len(rows)} rows found.")

            for row in rows:
                try:
                    cols = row.find_all("td") if row.name == "tr" else row.find_all(["div", "span"])
                    texts = [c.get_text(strip=True) for c in cols if c.get_text(strip=True)]
                    if len(texts) < 2:
                        continue

                    date_str    = texts[0] if len(texts) > 0 else ""
                    company_str = texts[1] if len(texts) > 1 else ""
                    subject_str = texts[2] if len(texts) > 2 else ""

                    pdf_url = ""
                    for link in row.find_all("a", href=True):
                        href = link["href"]
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
                    logger.debug(f"Row parse error: {e}")
                    continue

            session.close()

            if raw:
                logger.info(f"✅ Method 4 (Scraper/{page_name}): {len(raw)} items.")
                return raw

            time.sleep(2)

        except Exception as e:
            logger.debug(f"Scraper failed for {url}: {e}")
            time.sleep(2)
            continue

    return raw


# ═════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
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

    # ── Method 1: jugaad-data ★★★★★ ──
    results = fetch_jugaad_data()
    if results:
        all_results = results
        logger.info(f"✅ Used Method 1 (jugaad-data): {len(results)} items")
    else:
        # ── Method 2: RSS Feed ★★★★ ──
        for feed_type in ["announcements", "board_meetings", "financial_results"]:
            results = fetch_rss_feed(feed_type)
            if results:
                all_results = results
                logger.info(f"✅ Used Method 2 (RSS/{feed_type}): {len(results)} items")
                break

    if not all_results:
        # ── Method 3: NSE API ★★★ ──
        results = fetch_nse_api()
        if results:
            all_results = results
            logger.info(f"✅ Used Method 3 (NSE API): {len(results)} items")

    if not all_results:
        # ── Method 4: Scraper ★★ ──
        results = fetch_nse_scraper()
        if results:
            all_results = results
            logger.info(f"✅ Used Method 4 (Scraper): {len(results)} items")

    if not all_results:
        logger.error("❌ NSE: All methods failed. Returning empty list.")
        return []

    # ── Deduplicate ──
    seen = set()
    unique = []
    for item in all_results:
        key = (item["date"], item["company"].upper(), item["subject"][:50].upper())
        if key not in seen:
            seen.add(key)
            unique.append(item)

    logger.info(f"📊 NSE: {len(all_results)} fetched → {len(unique)} after dedup")

    # ── Apply filters ──
    try:
        from announcements.filters import process_announcements
        filtered = process_announcements(unique)
        logger.info(f"📊 NSE: {len(unique)} → {len(filtered)} after filters")
        return filtered
    except ImportError:
        logger.warning("filters module not found; returning deduped results.")
        return unique
    except Exception as e:
        logger.warning(f"Filter error: {e}; returning deduped results.")
        return unique


# ═════════════════════════════════════════════════════════════
# TEST/DEBUG
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

    for idx, item in enumerate(results[:20], 1):
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
