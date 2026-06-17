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
        """Fetch top Nifty stocks with current and previous quarter data"""
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
                    # Calculate growth from current and previous quarter
                    self._calculate_growth(data)
                    
                    announcements.append({
                        'symbol': symbol,
                        'company': data.get('company_name', symbol),
                        'pdf_url': None,
                        'id': f"SCR_{symbol}_{data.get('quarter', '')}",
                        'date': data.get('quarter', ''),
                        'financials': data,
                        # Include previous quarter data for growth calculation
                        'previous_financials': data.get('prev_quarter', {})
                    })
                    print(f"  ✅ {symbol}: Revenue={data['revenue']:,.0f} (growth {data.get('rev_growth', 0):.1f}%), PAT={data['pat']:,.0f} (growth {data.get('pat_growth', 0):.1f}%), Margin={data.get('ebitda_margin', 0):.1f}%")
                else:
                    print(f"  ⚠️ No data for {symbol}")
                time.sleep(1.5)
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
        Scrape the 'quarters' table and extract current AND previous quarter.
        """
        url = f"https://www.screener.in/company/{symbol}/"
        try:
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, 'html.parser')
            data = {}
            prev_data = {}

            # Company name
            name_elem = soup.find('h1', class_='company-name')
            if name_elem:
                data['company_name'] = name_elem.text.strip()

            # Find the quarters section
            quarter_section = soup.find('section', id='quarters')
            if not quarter_section:
                return None

            table = quarter_section.find('table', class_='data-table')
            if not table:
                return None

            rows = table.find_all('tr')
            if len(rows) < 2:
                return None

            # Process each metric row
            for row in rows[1:]:
                cells = row.find_all('td')
                if len(cells) < 3:  # Need at least header + 2 quarters
                    continue

                # First cell is metric name
                metric_text = cells[0].get_text(strip=True).lower()

                # Get all quarter cells (after the first one)
                quarter_cells = cells[1:]
                if len(quarter_cells) < 2:
                    continue

                # Get the last two non-empty values (current and previous quarter)
                values = []
                for cell in reversed(quarter_cells):
                    text = cell.get_text(strip=True)
                    if text and text != '-' and text != '':
                        values.append(text)
                        if len(values) == 2:
                            break

                if len(values) < 2:
                    continue

                latest_value = values[0]  # Most recent quarter
                prev_value = values[1]    # Previous quarter

                # Map metric name to our fields
                if 'sales' in metric_text:
                    data['revenue'] = self._clean_number(latest_value)
                    prev_data['revenue'] = self._clean_number(prev_value)
                elif 'operating profit' in metric_text and 'opm' not in metric_text:
                    data['ebitda'] = self._clean_number(latest_value)
                    prev_data['ebitda'] = self._clean_number(prev_value)
                elif 'net profit' in metric_text:
                    data['pat'] = self._clean_number(latest_value)
                    prev_data['pat'] = self._clean_number(prev_value)
                elif 'eps' in metric_text:
                    data['eps'] = self._clean_number(latest_value)
                    prev_data['eps'] = self._clean_number(prev_value)
                elif 'opm %' in metric_text:
                    data['ebitda_margin'] = self._clean_percent(latest_value)
                    prev_data['ebitda_margin'] = self._clean_percent(prev_value)
                elif 'pat margin' in metric_text:
                    data['pat_margin'] = self._clean_percent(latest_value)
                    prev_data['pat_margin'] = self._clean_percent(prev_value)

            # If we didn't get revenue, fail
            if 'revenue' not in data or data['revenue'] == 0:
                return None

            # Compute margins if not provided
            if 'ebitda_margin' not in data and 'ebitda' in data and data['revenue'] > 0:
                data['ebitda_margin'] = (data['ebitda'] / data['revenue']) * 100
            if 'pat_margin' not in data and 'pat' in data and data['revenue'] > 0:
                data['pat_margin'] = (data['pat'] / data['revenue']) * 100

            # Store previous quarter data for growth calculation
            data['prev_quarter'] = prev_data
            data['quarter'] = 'Latest Quarter'

            return data

        except Exception as e:
            print(f"  Scrape error for {symbol}: {e}")
            return None

    def _calculate_growth(self, data):
        """
        Calculate revenue and PAT growth from current vs previous quarter.
        Store in data dict as 'rev_growth' and 'pat_growth'.
        """
        prev = data.get('prev_quarter', {})
        
        # Revenue growth
        if prev.get('revenue', 0) > 0 and data.get('revenue', 0) > 0:
            rev_growth = ((data['revenue'] - prev['revenue']) / prev['revenue']) * 100
        else:
            rev_growth = 0
        data['rev_growth'] = round(rev_growth, 1)

        # PAT growth
        if prev.get('pat', 0) > 0 and data.get('pat', 0) > 0:
            pat_growth = ((data['pat'] - prev['pat']) / prev['pat']) * 100
        else:
            pat_growth = 0
        data['pat_growth'] = round(pat_growth, 1)

    def _clean_number(self, text):
        if not text:
            return 0
        text = text.replace(',', '').strip()
        text = text.replace('+', '').strip()
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
