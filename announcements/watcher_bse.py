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
from webdriver_manager.chrome import ChromeDriverManager

from announcements.filters import process_announcements

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.bseindia.com/",
    "Accept-Language": "en-US,en;q=0.9",
}

BSE_API_URL = (
    "https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w"
    "?strCat=-1&strPrevDate=&strScrip=&strSearch=P"
    "&strToDate=&strType=C&subcategory=-1"
)

BSE_FALLBACK_URL = "https://www.bseindia.com/corporates/announcements.aspx"


def _safe_text(value) -> str:
    return str(value).strip() if value is not None else ""


def fetch_bse_via_api() -> List[Dict]:
    raw_data = []

    try:
        response = requests.get(BSE_API_URL, headers=HEADERS, timeout=20)
        response.raise_for_status()

        try:
            data = response.json()
        except ValueError:
            logger.warning("BSE API returned non-JSON response.")
            return []

        if isinstance(data, dict):
            items = data.get("Table", data.get("data", []))
        elif isinstance(data, list):
            items = data
        else:
            logger.warning(f"BSE API returned unexpected format: {type(data)}")
            return []

        if not items:
            logger.info("BSE API returned empty results.")
            return []

        for item in items[:50]:
            if not isinstance(item, dict):
                continue

            attachment = _safe_text(item.get("ATTACHMENTNAME", item.get("attachment", "")))
            pdf_url = ""
            if attachment:
                pdf_url = (
                    "https://www.bseindia.com/xml-data/corpfiling/AttachLive/"
                    f"{attachment}"
                )

            raw_data.append({
                "date": _safe_text(item.get("NEWS_DT", item.get("date", "")))[:10],
                "company": _safe_text(item.get("SLONGNAME", item.get("companyName", "N/A"))),
                "subject": _safe_text(item.get("NEWSSUB", item.get("subject", "N/A"))),
                "symbol": _safe_text(item.get("SCRIP_CD", item.get("symbol", "N/A"))),
                "pdf_url": pdf_url,
                "source": "BSE",
            })

        logger.info(f"BSE API fetched {len(raw_data)} items.")

    except requests.exceptions.HTTPError as e:
        logger.error(f"BSE API HTTP error: {e}")
    except requests.exceptions.Timeout:
        logger.error("BSE API timed out.")
    except requests.exceptions.ConnectionError:
        logger.error("BSE API connection error.")
    except Exception as e:
        logger.error(f"BSE API unexpected error: {e}", exc_info=False)

    return raw_data


def fetch_bse_via_alternative_api() -> List[Dict]:
    raw_data = []
    alt_url = "https://www.bseindia.com/api/announcements"

    try:
        response = requests.get(alt_url, headers=HEADERS, timeout=20)
        response.raise_for_status()

        try:
            data = response.json()
        except ValueError:
            logger.warning("BSE alternative API returned non-JSON response.")
            return []

        if isinstance(data, dict):
            items = data.get("data", data.get("announcements", []))
        elif isinstance(data, list):
            items = data
        else:
            logger.warning(f"BSE alternative API returned unexpected format: {type(data)}")
            return []

        if not items:
            return []

        for item in items[:50]:
            if not isinstance(item, dict):
                continue

            raw_data.append({
                "date": _safe_text(item.get("date", ""))[:10],
                "company": _safe_text(item.get("company", "N/A")),
                "subject": _safe_text(item.get("subject", "N/A")),
                "symbol": _safe_text(item.get("symbol", "N/A")),
                "pdf_url": _safe_text(item.get("url", "")),
                "source": "BSE",
            })

        logger.info(f"BSE alternative API fetched {len(raw_data)} items.")

    except requests.exceptions.HTTPError as e:
        logger.debug(f"BSE alternative API HTTP error: {e}")
    except requests.exceptions.Timeout:
        logger.debug("BSE alternative API timed out.")
    except requests.exceptions.ConnectionError:
        logger.debug("BSE alternative API connection error.")
    except Exception as e:
        logger.debug(f"BSE alternative API failed: {e}")

    return raw_data


def fetch_bse_via_selenium() -> List[Dict]:
    raw_data = []
    url = "https://www.bseindia.com/corporates/announcements.aspx"

    try:
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument(f"user-agent={HEADERS['User-Agent']}")

        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )

        logger.info("BSE Selenium: Opening browser...")
        driver.get(url)

        logger.info("BSE Selenium: Waiting for table to load...")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "table#ctl00_ContentPlaceHolder1_gvAnn")
            )
        )

        table = driver.find_element(By.CSS_SELECTOR, "table#ctl00_ContentPlaceHolder1_gvAnn")
        rows = table.find_elements(By.TAG_NAME, "tr")[1:51]

        logger.info(f"BSE Selenium: Found {len(rows)} rows to process.")

        for row in rows:
            try:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) < 4:
                    continue

                pdf_url = ""
                try:
                    link = cols[2].find_element(By.TAG_NAME, "a")
                    pdf_url = link.get_attribute("href") or ""
                except:
                    pass

                date_text = cols[3].text.strip()[:10] if len(cols) > 3 else ""
                company_text = cols[1].text.strip() if len(cols) > 1 else ""
                subject_text = cols[2].text.strip() if len(cols) > 2 else ""
                symbol_text = cols[0].text.strip() if len(cols) > 0 else ""

                if not date_text or not company_text:
                    continue

                raw_data.append({
                    "date": date_text,
                    "company": company_text,
                    "subject": subject_text,
                    "symbol": symbol_text,
                    "pdf_url": pdf_url,
                    "source": "BSE",
                })

            except Exception as row_error:
                logger.debug(f"BSE Selenium: Error processing row: {row_error}")
                continue

        driver.quit()
        logger.info(f"BSE Selenium: Successfully fetched {len(raw_data)} items.")

    except Exception as e:
        logger.error(f"BSE Selenium scraper failed: {e}")
        try:
            driver.quit()
        except:
            pass

    return raw_data


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
                    logger.info(f"BSE scraper found table using selector: {attrs}")
                    break

            if not table:
                logger.warning("BSE scraper: announcement table not found.")
                if attempt == 0:
                    logger.info("BSE scraper: Retrying in 2 seconds...")
                    time.sleep(2)
                continue

            rows = table.find_all("tr")[1:51]
            for row in rows:
                cols = row.find_all("td")
                if len(cols) < 4:
                    continue

                pdf_url = ""
                link_tag = cols[2].find("a")
                if link_tag and link_tag.get("href"):
                    href = link_tag["href"]
                    pdf_url = href if href.startswith("http") else f"https://www.bseindia.com{href}"

                date_text = cols[3].get_text(strip=True)[:10]
                company_text = cols[1].get_text(strip=True)
                subject_text = cols[2].get_text(strip=True)
                symbol_text = cols[0].get_text(strip=True)

                if not date_text or not company_text:
                    continue

                raw_data.append({
                    "date": date_text,
                    "company": company_text,
                    "subject": subject_text,
                    "symbol": symbol_text,
                    "pdf_url": pdf_url,
                    "source": "BSE",
                })

            if raw_data:
                logger.info(f"BSE scraper fetched {len(raw_data)} items.")
                break

        except Exception as e:
            if attempt == 0:
                logger.warning(f"BSE scraper attempt 1 failed: {e}. Retrying...")
                time.sleep(2)
            else:
                logger.error(f"BSE scraper failed after 2 attempts: {e}")

    return raw_data


def get_bse_announcements() -> List[Dict]:
    logger.info("Attempting BSE API fetch...")
    raw = fetch_bse_via_api()

    if not raw:
        logger.info("Attempting BSE alternative API...")
        raw = fetch_bse_via_alternative_api()

    if not raw:
        logger.info("Attempting BSE HTML scraper...")
        raw = fetch_bse_via_scraper()

    if not raw:
        logger.info("Attempting BSE Selenium scraper (JavaScript rendering)...")
        raw = fetch_bse_via_selenium()

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
            print(f"[{r['date']}] {r['company']} ({r['symbol']})")
            print(f"  {r['subject']}")
            if r.get("pdf_url"):
                print(f"  {r['pdf_url']}")
            print()
    else:
        print("No relevant BSE announcements found.")
