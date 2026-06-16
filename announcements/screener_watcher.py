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
                    print(f"  ✅ {symbol}: Revenue={data['revenue']:,.0f}, PAT={data['pat']:,.0f}, EBITDA Margin={data['ebitda_margin']:.1f}%, PAT Margin={data['pat_margin']:.1f}%")
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
        """Scrape quarterly results with dynamic header mapping"""
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

            # Find the quarters table
            quarter_section = soup.find('section', id='quarters')
            if not quarter_section:
                quarter_section = soup.find('table', class_='data-table')
                if not quarter_section:
                    return None

            # Get all rows
            rows = quarter_section.find_all('tr')
            if len(rows) < 2:
                return None

            # ---------- Header mapping ----------
            header_row = rows[0]
            headers = [th.get_text(strip=True) for th in header_row.find_all('th')]
            # Expected columns: Quarter, Sales, EBITDA, PAT, EPS, EBIT Margin, PAT Margin
            # Map column names to indices
            col_map = {}
            for idx, col in enumerate(headers):
                col_lower = col.lower()
                if 'quarter' in col_lower or 'period' in col_lower:
                    col_map['quarter'] = idx
                elif 'sales' in col_lower or 'revenue' in col_lower:
                    col_map['revenue'] = idx
                elif 'ebitda' in col_lower:
                    col_map['ebitda'] = idx
                elif 'pat' in col_lower or 'net profit' in col_lower:
                    col_map['pat'] = idx
                elif 'eps' in col_lower:
                    col_map['eps'] = idx
                elif 'ebit margin' in col_lower or 'ebitda margin' in col_lower:
                    col_map['ebitda_margin'] = idx
                elif 'pat margin' in col_lower or 'net profit margin' in col_lower:
                    col_map['pat_margin'] = idx

            # If we didn't find critical columns, try alternative mapping (some tables have different order)
            if 'revenue' not in col_map or 'pat' not in col_map:
                # Fallback: assume standard order: Quarter, Revenue, EBITDA, PAT, EPS, EBIT Margin, PAT Margin
                # But we can guess: if we have 7 columns, assume that order
                if len(headers) >= 7:
                    col_map['quarter'] = 0
                    col_map['revenue'] = 1
                    col_map['ebitda'] = 2
                    col_map['pat'] = 3
                    col_map['eps'] = 4
                    col_map['ebitda_margin'] = 5
                    col_map['pat_margin'] = 6
                else:
                    return None

            # ---------- Find latest quarter row ----------
            # The first row after header that contains a date in the quarter column
            latest_row = None
            for row in rows[1:]:
                cells = row.find_all('td')
                if len(cells) <= max(col_map.values()):
                    continue
                # Check if quarter cell looks like a date
                quarter_text = cells[col_map['quarter']].get_text(strip=True)
                if re.match(r'\d{2}\s\w{3}\s\d{2}', quarter_text):
                    latest_row = cells
                    break

            # If no date found, take the second row (might be latest)
            if not latest_row and len(rows) > 1:
                latest_row = rows[1].find_all('td')

            if not latest_row:
                return None

            # Extract values
            data['quarter'] = latest_row[col_map['quarter']].get_text(strip=True)
            data['revenue'] = self._clean_number(latest_row[col_map['revenue']].get_text(strip=True)) if 'revenue' in col_map else 0
            data['ebitda'] = self._clean_number(latest_row[col_map['ebitda']].get_text(strip=True)) if 'ebitda' in col_map else 0
            data['pat'] = self._clean_number(latest_row[col_map['pat']].get_text(strip=True)) if 'pat' in col_map else 0
            data['eps'] = self._clean_number(latest_row[col_map['eps']].get_text(strip=True)) if 'eps' in col_map else 0
            data['ebitda_margin'] = self._clean_percent(latest_row[col_map['ebitda_margin']].get_text(strip=True)) if 'ebitda_margin' in col_map else 0
            data['pat_margin'] = self._clean_percent(latest_row[col_map['pat_margin']].get_text(strip=True)) if 'pat_margin' in col_map else 0

            # If revenue is zero, scraping failed
            if data['revenue'] == 0:
                return None

            # If margins are zero but we have revenue and PAT, compute margins
            if data['ebitda_margin'] == 0 and data['ebitda'] > 0 and data['revenue'] > 0:
                data['ebitda_margin'] = (data['ebitda'] / data['revenue']) * 100
            if data['pat_margin'] == 0 and data['pat'] > 0 and data['revenue'] > 0:
                data['pat_margin'] = (data['pat'] / data['revenue']) * 100

            return data

        except Exception as e:
            print(f"  Scrape error for {symbol}: {e}")
            return None

    def _clean_number(self, text):
        if not text:
            return 0
        text = text.replace(',', '').strip()
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
