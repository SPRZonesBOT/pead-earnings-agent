import logging
import time
from typing import List, Dict

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from announcements.filters import process_announcements

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.bseindia.com/",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "application/json, text/plain, */*",
    "Host": "api.bseindia.com",
    "Origin": "https://www.bseindia.com",
}

BSE_API_URL = (
    "https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w"
    "?strCat=-1&strPrevDate=&strScrip=&strSearch=P"
    "&strToDate=&strType=C&subcategory=-1"
)

ALT_API_URL = "https://www.bseindia.com/api/announcements"
BSE_PAGE_URL = "https://www.bseindia.com/corporates/announcements.aspx"


def _safe_text(val) -> str:
    return str(val).strip() if val is not None else ""


# ──────────────────────────────────────────────
# METHOD 1: Primary BSE JSON API
# ──────────────────────────────────────────────
def fetch_bse_api() -> List[Dict]:
    raw = []
    try:
        session = requests.Session()
        # Get cookies from main site first
        session.get("https://www.bseindia.com", headers=HEADERS, timeout=10)

        resp = session.get(BSE_API_URL, headers=HEADERS, timeout=20)
        resp.raise_for_status()

        if not resp.text.strip():
            logger.warning("BSE API returned empty response.")
            return []

        try:
            data = resp.json()
        except ValueError:
            logger.warning("BSE API returned non-JSON (likely blocked).")
            return []

        items = data if isinstance(data, list) else data.get("Table", data.get("data", []))

        for item in items[:50]:
            if not isinstance(item, dict):
                continue
            attach = _safe_text(item.get("ATTACHMENTNAME", ""))
            pdf = f"https://www.bseindia.com/xml-data/corpfiling/AttachLive/{attach}" if attach else ""
            raw.append({
                "date": _safe_text(item.get("NEWS_DT", ""))[:10],
                "company": _safe_text(item.get("SLONGNAME", "N/A")),
                "subject": _safe_text(item.get("NEWSSUB", "N/A")),
                "symbol": _safe_text(item.get("SCRIP_CD", "N/A")),
                "pdf_url": pdf,
                "source": "BSE",
            })

        logger.info(f"BSE API → {len(raw)} items fetched.")
    except Exception as e:
        logger.warning(f"BSE API failed: {e}")
    return raw


# ──────────────────────────────────────────────
# METHOD 2: Alternative BSE API
# ──────────────────────────────────────────────
def fetch_bse_alt_api() -> List[Dict]:
    raw = []
    try:
        resp = requests.get(ALT_API_URL, headers=HEADERS, timeout=20)
        resp.raise_for_status()

        if not resp.text.strip():
            return []

        try:
            data = resp.json()
        except ValueError:
            return []

        items = data if isinstance(data, list) else data.get("data", data.get("announcements", []))

        for item in items[:50]:
            if not isinstance(item, dict):
                continue
            raw.append({
                "date": _safe_text(item.get("date", ""))[:10],
                "company": _safe_text(item.get("company", "N/A")),
                "subject": _safe_text(item.get("subject", "N/A")),
                "symbol": _safe_text(item.get("symbol", "N/A")),
                "pdf_url": _safe_text(item.get("url", "")),
                "source": "BSE",
            })

        logger.info(f"BSE Alt API → {len(raw)} items fetched.")
    except Exception as e:
        logger.debug(f"BSE Alt API failed: {e}")
    return raw


# ──────────────────────────────────────────────
# METHOD 3: HTML Scraper (BeautifulSoup)
# ──────────────────────────────────────────────
def fetch_bse_scraper() -> List[Dict]:
    raw = []
    for attempt in range(2):
        try:
            resp = requests.get(BSE_PAGE_URL, headers=HEADERS, timeout=25)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # Try multiple table selectors (BSE changes class/IDs sometimes)
            table = None
            for sel in [
                {"id": "ctl00_ContentPlaceHolder1_gvAnn"},
                {"class": "announcement-table"},
                {"summary": "Announcements"},
            ]:
                table = soup.find("table", sel)
                if table:
                    break

            if not table:
                logger.warning("BSE Scraper: table not found.")
                time.sleep(2)
                continue

            rows = table.find_all("tr")[1:51]
            for row in rows:
                cols = row.find_all("td")
                if len(cols) < 4:
                    continue
                link = cols[2].find("a")
                href = link["href"] if link and link.get("href") else ""
                pdf = href if href.startswith("http") else f"https://www.bseindia.com{href}"
                raw.append({
                    "date": cols[3].get_text(strip=True)[:10],
                    "company": cols[1].get_text(strip=True),
                    "subject": cols[2].get_text(strip=True),
                    "symbol": cols[0].get_text(strip=True),
                    "pdf_url": pdf,
                    "source": "BSE",
                })

            if raw:
                logger.info(f"BSE Scraper → {len(raw)} items fetched.")
                break
        except Exception as e:
            logger.debug(f"BSE Scraper attempt {attempt+1} failed: {e}")
            time.sleep(2)
    return raw


# ──────────────────────────────────────────────
# METHOD 4: Selenium (JavaScript rendering)
# ──────────────────────────────────────────────
def _try_get_driver():
    """
    Attempts to create a Chrome driver.
    Tries webdriver_manager first, then common paths.
    """
    driver = None

    # 1) Try webdriver-manager
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        service = Service(ChromeDriverManager().install())
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument(f"user-agent={HEADERS['User-Agent']}")
        driver = webdriver.Chrome(service=service, options=options)
        logger.info("BSE Selenium: driver created via webdriver-manager")
        return driver
    except Exception as e:
        logger.debug(f"webdriver-manager failed: {e}")

    # 2) Try common manual paths
    common_paths = [
        "/usr/local/bin/chromedriver",
        "/usr/bin/chromedriver",
        "C:\\chromedriver\\chromedriver.exe",
        "C:\\Program Files\\Chrome Driver\\chromedriver.exe",
    ]
    for path in common_paths:
        try:
            import os
            if not os.path.exists(path):
                continue
            service = Service(path)
            options = webdriver.ChromeOptions()
            options.add_argument("--headless")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument(f"user-agent={HEADERS['User-Agent']}")
            driver = webdriver.Chrome(service=service, options=options)
            logger.info(f"BSE Selenium: driver created from {path}")
            return driver
        except Exception as e:
            logger.debug(f"ChromeDriver at {path} failed: {e}")

    return None


def fetch_bse_selenium() -> List[Dict]:
    raw = []
    driver = None
    try:
        driver = _try_get_driver()
        if not driver:
            logger.warning("BSE Selenium: could not create any driver.")
            return []

        driver.get(BSE_PAGE_URL)
        WebDriverWait(driver, 25).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "table#ctl00_ContentPlaceHolder1_gvAnn")
            )
        )

        table = driver.find_element(By.CSS_SELECTOR, "table#ctl00_ContentPlaceHolder1_gvAnn")
        rows = table.find_elements(By.TAG_NAME, "tr")[1:51]

        for row in rows:
            try:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) < 4:
                    continue
                pdf = ""
                try:
                    pdf = cols[2].find_element(By.TAG_NAME, "a").get_attribute("href") or ""
                except:
                    pass
                raw.append({
                    "date": cols[3].text.strip()[:10],
                    "company": cols[1].text.strip(),
                    "subject": cols[2].text.strip(),
                    "symbol": cols[0].text.strip(),
                    "pdf_url": pdf,
                    "source": "BSE",
                })
            except Exception:
                continue

        logger.info(f"BSE Selenium → {len(raw)} items fetched.")
    except Exception as e:
        logger.error(f"BSE Selenium failed: {e}")
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass
    return raw


# ──────────────────────────────────────────────
# Main entry point — tries all methods
# ──────────────────────────────────────────────
def get_bse_announcements() -> List[Dict]:
    logger.info("=== BSE Announcement Fetch Started ===")

    # Try methods in order of reliability
    methods = [
        ("API", fetch_bse_api),
        ("Alt API", fetch_bse_alt_api),
        ("Scraper", fetch_bse_scraper),
        ("Selenium", fetch_bse_selenium),
    ]

    all_raw = []
    for name, method in methods:
        logger.info(f"Trying BSE {name}...")
        result = method()
        if result:
            all_raw = result
            logger.info(f"BSE {name} succeeded → {len(result)} items.")
            break
        logger.info(f"BSE {name} returned nothing.")

    if not all_raw:
        logger.warning("ALL BSE methods failed. Returning empty.")
        return []

    filtered = process_announcements(all_raw)
    logger.info(f"BSE: {len(all_raw)} fetched, {len(filtered)} passed filters.")
    return filtered


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    results = get_bse_announcements()
    print(f"\n✅ BSE Results: {len(results)} items\n")
    for r in results[:10]:
        print(f"[{r['date']}] {r['company']} ({r['symbol']})")
        print(f"  → {r['subject']}")
        if r.get("pdf_url"):
            print(f"  📄 {r['pdf_url']}")
        print()
