# announcements/bse_watcher.py
import time
import re
import requests
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager

class BSEWatcher:
    def __init__(self):
        self.options = Options()
        # Headless mode - background mein chalega (comment karke dekh sakte ho agar debug karna ho)
        # self.options.add_argument('--headless')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--disable-gpu')
        self.options.add_argument('--window-size=1920,1080')
        self.options.add_argument('--disable-blink-features=AutomationControlled')
        self.options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.options.add_experimental_option('useAutomationExtension', False)
        
        # BSE Scrip Code to NSE Symbol mapping (commonly known stocks)
        self.symbol_map = {
            '500325': 'RELIANCE',
            '500570': 'TCS',
            '500180': 'HDFCBANK',
            '500875': 'ITC',
            '500696': 'HINDUNILVR',
            '500247': 'KOTAKBANK',
            '532174': 'ICICIBANK',
            '500209': 'INFY',
            '532540': 'SBIN',
            '500010': 'HDFC',
            '500111': 'BAJAJFINSV',
            '532977': 'BHARTIARTL',
            '500390': 'TATAMOTORS',
            '500112': 'SBILIFE',
            '532215': 'AXISBANK',
            '500490': 'HCLTECH',
            '500820': 'ASIANPAINT',
            '532454': 'LT',
            '500875': 'ITC',
            '500247': 'KOTAKBANK',
            '532155': 'TATAPOWER',
            '532488': 'COALINDIA',
            '532500': 'MARUTI',
            '500257': 'TITAN',
            '532281': 'ADANIPORTS',
            '532343': 'ULTRACEMCO',
            '500330': 'GRASIM',
            '532921': 'NTPC',
            '532898': 'POWERGRID',
            '500775': 'TATASTEEL',
            '500087': 'HINDALCO',
            '532868': 'JSWSTEEL',
            '532755': 'BRITANNIA',
            '532432': 'BAJFINANCE',
            '532134': 'INDUSINDBK',
            '532454': 'LT',
            '532529': 'SUNPHARMA',
            '532523': 'DRREDDY',
            '532822': 'CIPLA',
            '532356': 'DIVISLAB',
            '532538': 'UPL',
            '500294': 'BAJAJ-AUTO',
            '532413': 'EICHERMOT',
            '532659': 'HEROMOTOCO',
            '500520': 'M&M',
            '532555': 'TVSMOTOR',
            '500182': 'PIDILITIND',
            '500800': 'BERGEPAINT',
            '532331': 'HAL',
            '532665': 'BEL',
            '532187': 'ONGC',
            '532483': 'VEDL',
            '532356': 'DIVISLAB',
            '532724': 'SBICARD',
            '532432': 'BAJFINANCE',
            '532454': 'LT',
        }

    def get_financial_results(self, days=7):
        """
        BSE se latest announcements fetch karein.
        Returns: List of dicts with symbol, company, pdf_url, id, etc.
        """
        driver = None
        try:
            print("🌐 Launching Chrome browser...")
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=self.options)
            
            print(f"🔍 Navigating to BSE announcements page...")
            driver.get("https://www.bseindia.com/corporates/announcements.html")
            
            # Wait for the announcements table to load
            wait = WebDriverWait(driver, 40)
            wait.until(EC.presence_of_element_located((By.XPATH, "//table//tr")))
            
            # Extra wait for dynamic content
            time.sleep(3)
            
            # Scroll down to ensure all rows load
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            announcements = []
            
            # Find all rows in the announcements table
            # BSE uses multiple tables, find the one with announcements
            tables = driver.find_elements(By.TAG_NAME, "table")
            target_table = None
            
            for table in tables:
                try:
                    # Check if table has "Date" and "Company" headers
                    header_text = table.text[:200]
                    if "Date" in header_text and "Company" in header_text and "Subject" in header_text:
                        target_table = table
                        break
                except:
                    continue
            
            if not target_table:
                # Fallback: try to find any table with announcements
                target_table = driver.find_element(By.XPATH, "//table[contains(@class, 'table')]")
            
            # Get all rows from the table body
            rows = target_table.find_elements(By.XPATH, ".//tbody/tr")
            
            if not rows:
                # Try direct rows without tbody
                rows = target_table.find_elements(By.XPATH, ".//tr")
            
            print(f"📊 Found {len(rows)} total rows in table")
            
            for idx, row in enumerate(rows):
                try:
                    # Skip header rows
                    cols = row.find_elements(By.TAG_NAME, "td")
                    if len(cols) < 4:
                        continue
                    
                    # Extract column data
                    date_text = cols[0].text.strip() if len(cols) > 0 else ""
                    company_cell = cols[1] if len(cols) > 1 else None
                    category = cols[2].text.strip() if len(cols) > 2 else ""
                    subject = cols[3].text.strip() if len(cols) > 3 else ""
                    attachment_cell = cols[4] if len(cols) > 4 else None
                    
                    # Skip if no date or company
                    if not date_text or not company_cell:
                        continue
                    
                    # Filter: Only financial results announcements
                    if "Financial Results" not in subject and "Outcome of Board Meeting" not in subject:
                        continue
                    
                    # Extract company name and BSE code
                    company_name = company_cell.text.strip()
                    
                    # Extract BSE scrip code from company link
                    scrip_code = None
                    symbol = None
                    
                    try:
                        link = company_cell.find_element(By.TAG_NAME, "a")
                        href = link.get_attribute("href")
                        # Extract scrip code from URL pattern: .../stock-name/500325/
                        code_match = re.search(r'/(\d+)/?$', href)
                        if code_match:
                            scrip_code = code_match.group(1)
                            # Map to NSE symbol if available
                            symbol = self.symbol_map.get(scrip_code, scrip_code)
                    except:
                        # If no link, use company name as fallback
                        symbol = company_name[:10].upper().replace(" ", "_")
                        scrip_code = symbol
                    
                    # Extract PDF link
                    pdf_url = None
                    try:
                        if attachment_cell:
                            pdf_elem = attachment_cell.find_element(By.TAG_NAME, "a")
                            pdf_url = pdf_elem.get_attribute("href")
                            if pdf_url and not pdf_url.startswith("http"):
                                pdf_url = "https://www.bseindia.com" + pdf_url
                    except:
                        pass
                    
                    # Create unique ID
                    unique_id = f"{symbol}_{date_text.replace('/', '_')}_{idx}"
                    
                    announcements.append({
                        'symbol': symbol,
                        'company': company_name,
                        'scrip_code': scrip_code,
                        'pdf_url': pdf_url,
                        'id': unique_id,
                        'date': date_text,
                        'subject': subject,
                        'category': category
                    })
                    
                    print(f"  ✅ Found: {company_name} ({symbol}) - {subject[:30]}...")
                    
                except StaleElementReferenceException:
                    continue
                except Exception as e:
                    print(f"  ⚠️ Row parsing error: {e}")
                    continue
            
            driver.quit()
            
            # Remove duplicates based on symbol + date
            seen = set()
            unique_announcements = []
            for ann in announcements:
                key = f"{ann['symbol']}_{ann['date']}"
                if key not in seen:
                    seen.add(key)
                    unique_announcements.append(ann)
            
            print(f"✅ Found {len(unique_announcements)} unique financial result announcements.")
            
            # Limit to top 10 latest announcements (to avoid overloading)
            if len(unique_announcements) > 10:
                unique_announcements = unique_announcements[:10]
            
            # If no announcements found, return mock data
            if not unique_announcements:
                print("⚠️ No announcements found on BSE. Returning mock data for testing.")
                return self._get_mock_data()
            
            return unique_announcements
            
        except TimeoutException:
            print("❌ Page load timeout. BSE website might be slow or blocked.")
            if driver:
                driver.quit()
            return self._get_mock_data()
        except Exception as e:
            print(f"❌ BSE scraping failed: {e}")
            if driver:
                driver.quit()
            return self._get_mock_data()

    def download_pdf(self, pdf_url):
        """
        PDF download karo aur local path return karo.
        """
        if not pdf_url:
            print("⚠️ No PDF URL provided")
            return None
            
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(pdf_url, headers=headers, timeout=30)
            
            if response.status_code == 200 and response.headers.get('content-type', '').startswith('application/pdf'):
                filename = f"temp_{int(time.time())}.pdf"
                with open(filename, 'wb') as f:
                    f.write(response.content)
                print(f"✅ PDF downloaded: {filename}")
                return filename
            else:
                print(f"❌ Failed to download PDF from {pdf_url} (Status: {response.status_code})")
                return None
                
        except Exception as e:
            print(f"❌ Download error: {e}")
            return None

    def _get_mock_data(self):
        """Fallback mock data - same as before for testing"""
        print("🔄 Using mock data for testing...")
        return [
            {
                'symbol': 'RELIANCE',
                'company': 'Reliance Industries Ltd',
                'pdf_url': 'https://www.bseindia.com/xml-data/corpfiling/AttachHis/RELIANCE_Q3.pdf',
                'id': 'REL_Q3_2025',
                'close_price': 2850,
                'volume': 1500000,
                'avg_volume': 1200000,
                'date': '16-Jun-2025'
            },
            {
                'symbol': 'TCS',
                'company': 'Tata Consultancy Services',
                'pdf_url': 'https://www.bseindia.com/xml-data/corpfiling/AttachHis/TCS_Q3.pdf',
                'id': 'TCS_Q3_2025',
                'close_price': 4200,
                'volume': 800000,
                'avg_volume': 650000,
                'date': '16-Jun-2025'
            },
            {
                'symbol': 'HDFC',
                'company': 'HDFC Bank Ltd',
                'pdf_url': 'https://www.bseindia.com/xml-data/corpfiling/AttachHis/HDFC_Q3.pdf',
                'id': 'HDFC_Q3_2025',
                'close_price': 1650,
                'volume': 2000000,
                'avg_volume': 1800000,
                'date': '16-Jun-2025'
            }
        ]
