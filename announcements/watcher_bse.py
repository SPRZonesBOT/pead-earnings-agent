import logging
import time
from typing import List, Dict
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from announcements.filters import process_announcements

logger = logging.getLogger(__name__)


def fetch_bse_via_selenium() -> List[Dict]:
    """
    Uses Selenium to fetch BSE announcements (handles JavaScript).
    """
    raw_data = []
    url = "https://www.bseindia.com/corporates/announcements.aspx"

    driver = None
    try:
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        )

        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )

        logger.info("BSE Selenium: Loading page...")
        driver.get(url)

        # Wait for the announcement table to load
        WebDriverWait(driver, 25).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "table#ctl00_ContentPlaceHolder1_gvAnn")
            )
        )

        table = driver.find_element(By.CSS_SELECTOR, "table#ctl00_ContentPlaceHolder1_gvAnn")
        rows = table.find_elements(By.TAG_NAME, "tr")[1:51]  # Skip header, max 50 rows

        logger.info(f"BSE Selenium: Found {len(rows)} rows.")

        for row in rows:
            try:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) < 4:
                    continue

                # Extract PDF link
                pdf_url = ""
                try:
                    link = cols[2].find_element(By.TAG_NAME, "a")
                    pdf_url = link.get_attribute("href") or ""
                except:
                    pass

                date_text = cols[3].text.strip()[:10]
                company_text = cols[1].text.strip()
                subject_text = cols[2].text.strip()
                symbol_text = cols[0].text.strip()

                if not date_text or not company_text:
                    continue

                raw_data.append({
                    "date": date_text,
                    "company": company_text,
                    "subject": subject_text,
                    "symbol": symbol_text,
                    "pdf_url": pdf_url,
                    "source": "BSE"
                })

            except Exception as row_err:
                logger.debug(f"BSE row error: {row_err}")
                continue

        logger.info(f"BSE Selenium: Fetched {len(raw_data)} items.")

    except Exception as e:
        logger.error(f"BSE Selenium failed: {e}")

    finally:
        if driver:
            driver.quit()

    return raw_data


def get_bse_announcements() -> List[Dict]:
    logger.info("Fetching BSE announcements via Selenium...")
    raw = fetch_bse_via_selenium()

    if not raw:
        logger.warning("BSE: No data fetched via Selenium.")
        return []

    filtered = process_announcements(raw)
    logger.info(f"BSE: {len(raw)} fetched, {len(filtered)} passed filter.")
    return filtered


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = get_bse_announcements()
    print(f"\nBSE Results: {len(results)} items\n")
    for r in results[:5]:
        print(f"{r['date']} | {r['company']} ({r['symbol']}) | {r['subject']}")
