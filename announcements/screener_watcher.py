# announcements/screener_watcher.py
import requests
from bs4 import BeautifulSoup
import time
import re

class ScreenerWatcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.screener.in/'
        })

    def get_financial_results(self):
        """Fetch top Nifty stocks from Screener.in using HTML parsing"""
        nifty_symbols = [
            'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'HINDUNILVR',
            'ICICIBANK', 'SBIN', 'KOTAKBANK', 'LT', 'BHARTIARTL',
            'ITC', 'WIPRO', 'HCLTECH', 'ASIANPAINT', 'TITAN'
        ]
        announcements = []
        for symbol in nifty_symbols:
            try:
                data = self._fetch_quarterly_data(symbol)
                if data and data.get('revenue', 0) > 0:
                    announcements.append({
                        'symbol': symbol,
                        'company': data.get('company_name', symbol),
                        'pdf_url': None,
                        'id': f"SCR_{symbol}_{data.get('quarter', '')}",
                        'date': data.get('quarter', ''),
                        'financials': data
                    })
                    print(f"  ✅ {symbol}: Revenue={data['revenue']:,.0f}, PAT={data['pat']:,.0f}, Margin={data['ebitda_margin']:.1f}%")
                else:
                    print(f"  ⚠️ No data for {symbol}")
                time.sleep(1.5)  # Be gentle to avoid blocking
            except Exception as e:
                print(f"  ❌ Error {symbol}: {e}")

        if announcements:
            print(f"✅ Fetched {len(announcements)} stocks from Screener.in")
            return announcements
        else:
            print("⚠️ No data from Screener. Will use fallback.")
            return []

    def _fetch_quarterly_data(self, symbol):
        """Scrape quarterly results from Screener.in company page"""
        url = f"https://www.screener.in/company/{symbol}/"
        try:
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, 'html.parser')
            data = {}

            # Company name
            name_elem = soup.find('h1', class_='company-name')
            if name_elem:
                data['company_name'] = name_elem.text.strip()

            # Find the "quarters" section
            quarter_section = soup.find('section', id='quarters')
            if not quarter_section:
                # Try alternative: look for table with class 'data-table'
                quarter_section = soup.find('table', class_='data-table')
                if not quarter_section:
                    return None

            # Extract the latest quarter row (usually second row after header)
            rows = quarter_section.find_all('tr')
            if len(rows) < 2:
                return None

            # Find the first row that contains numeric data (skip header)
            for row in rows[1:]:
                cells = row.find_all('td')
                if len(cells) >= 7:
                    # Check if first cell is a date (quarter)
                    date_text = cells[0].text.strip()
                    if re.match(r'\d{2}\s\w{3}\s\d{2}', date_text):  # e.g., "31 Mar 23"
                        latest = cells
                        break
            else:
                # If no date pattern, use second row as fallback
                latest = rows[1].find_all('td')
                if len(latest) < 7:
                    return None

            # Extract values
            data['quarter'] = latest[0].text.strip()
            data['revenue'] = self._clean_number(latest[1].text)
            data['ebitda'] = self._clean_number(latest[2].text) if len(latest) > 2 else 0
            data['pat'] = self._clean_number(latest[3].text) if len(latest) > 3 else 0
            data['eps'] = self._clean_number(latest[4].text) if len(latest) > 4 else 0
            data['ebitda_margin'] = self._clean_percent(latest[5].text) if len(latest) > 5 else 0
            data['pat_margin'] = self._clean_percent(latest[6].text) if len(latest) > 6 else 0

            # If revenue is zero, scraping failed
            if data['revenue'] == 0:
                return None

            return data

        except Exception as e:
            print(f"  Scrape error for {symbol}: {e}")
            return None

    def _clean_number(self, text):
        """Convert text like '2,45,123 Cr' to float"""
        if not text:
            return 0
        # Remove commas and extra spaces
        text = text.replace(',', '').strip()
        # Handle crores
        if 'Cr' in text:
            text = text.replace('Cr', '').strip()
            try:
                return float(text) * 10000000
            except:
                return 0
        # Handle lakhs (if any)
        if 'L' in text:
            text = text.replace('L', '').strip()
            try:
                return float(text) * 100000
            except:
                return 0
        try:
            return float(text)
        except:
            return 0

    def _clean_percent(self, text):
        if not text:
            return 0
        text = text.replace('%', '').strip()
        try:
            return float(text)
        except:
            return 0

    def download_pdf(self, pdf_url):
        return None
