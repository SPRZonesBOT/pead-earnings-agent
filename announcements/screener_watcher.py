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
        """Fetch top Nifty stocks from Screener.in using HTML parsing of the quarters table"""
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
                    print(f"  ✅ {symbol}: Revenue={data['revenue']:,.0f}, PAT={data['pat']:,.0f}, EBITDA Margin={data.get('ebitda_margin', 0):.1f}%, PAT Margin={data.get('pat_margin', 0):.1f}%")
                else:
                    print(f"  ⚠️ No data for {symbol}")
                time.sleep(1.5)  # Be gentle
            except Exception as e:
                print(f"  ❌ Error {symbol}: {e}")

        if announcements:
            print(f"✅ Fetched {len(announcements)} stocks from Screener.in")
            return announcements
        else:
            print("⚠️ No data from Screener. Will use fallback.")
            return []

    def _fetch_quarterly_data(self, symbol):
        """
        Scrape the 'quarters' table from the company page.
        The table has metrics in rows and quarters in columns.
        We extract the latest quarter (last column).
        """
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

            # Find the quarters section
            quarter_section = soup.find('section', id='quarters')
            if not quarter_section:
                return None

            # Find the table inside it (class "data-table")
            table = quarter_section.find('table', class_='data-table')
            if not table:
                return None

            rows = table.find_all('tr')
            if len(rows) < 2:
                return None

            # Skip header row (index 0)
            for row in rows[1:]:
                cells = row.find_all('td')
                if len(cells) < 2:
                    continue

                # First cell is the metric name (may contain a button)
                metric_cell = cells[0]
                metric_text = metric_cell.get_text(strip=True).lower()

                # Get all data cells (quarters) after the first one
                quarter_cells = cells[1:]
                if not quarter_cells:
                    continue

                # The latest quarter is the last non-empty cell (rightmost)
                latest_value = None
                for cell in reversed(quarter_cells):
                    text = cell.get_text(strip=True)
                    if text and text != '-' and text != '':
                        latest_value = text
                        break

                if latest_value is None:
                    continue

                # Map metric name to our fields
                if 'sales' in metric_text:
                    data['revenue'] = self._clean_number(latest_value)
                elif 'operating profit' in metric_text and 'opm' not in metric_text:
                    data['ebitda'] = self._clean_number(latest_value)
                elif 'net profit' in metric_text:
                    data['pat'] = self._clean_number(latest_value)
                elif 'eps' in metric_text:
                    data['eps'] = self._clean_number(latest_value)
                elif 'opm %' in metric_text:
                    data['ebitda_margin'] = self._clean_percent(latest_value)
                elif 'pat margin' in metric_text:
                    data['pat_margin'] = self._clean_percent(latest_value)
                # You can add more fields if needed (e.g., Interest, Other Income)

            # If we didn't get revenue, fail
            if 'revenue' not in data or data['revenue'] == 0:
                return None

            # Compute margins if not directly provided
            if 'ebitda_margin' not in data and 'ebitda' in data and data['revenue'] > 0:
                data['ebitda_margin'] = (data['ebitda'] / data['revenue']) * 100
            if 'pat_margin' not in data and 'pat' in data and data['revenue'] > 0:
                data['pat_margin'] = (data['pat'] / data['revenue']) * 100

            # We don't have a specific quarter date, but we can set a placeholder
            data['quarter'] = 'Latest Quarter'

            return data

        except Exception as e:
            print(f"  Scrape error for {symbol}: {e}")
            return None

    def _clean_number(self, text):
        if not text:
            return 0
        # Remove commas and plus signs
        text = text.replace(',', '').strip()
        text = text.replace('+', '').strip()
        # Handle crores
        if 'Cr' in text:
            text = text.replace('Cr', '').strip()
            try:
                return float(text) * 10000000
            except:
                return 0
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
