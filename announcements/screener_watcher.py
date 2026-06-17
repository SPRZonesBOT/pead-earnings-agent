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

    def get_financial_results(self, stocks_list=None):
        """Fetch data for top Nifty 200 stocks (or custom list)"""
        if stocks_list is None:
            # Nifty 200 (top 20 for now, extend as needed)
            stocks_list = [
                'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'HINDUNILVR',
                'ICICIBANK', 'SBIN', 'KOTAKBANK', 'LT', 'BHARTIARTL',
                'ITC', 'WIPRO', 'HCLTECH', 'ASIANPAINT', 'TITAN',
                'MARUTI', 'TATAMOTORS', 'SUNPHARMA', 'NTPC', 'POWERGRID',
                'TATASTEEL', 'BAJFINANCE', 'AXISBANK', 'HDFC', 'ULTRACEMCO',
                'ADANIPORTS', 'GRASIM', 'JSWSTEEL', 'DIVISLAB', 'DRREDDY'
            ]
        announcements = []
        for symbol in stocks_list:
            try:
                data = self._fetch_quarterly_data(symbol)
                if data and data.get('revenue', 0) > 0:
                    announcements.append({
                        'symbol': symbol,
                        'company': data.get('company_name', symbol),
                        'pdf_url': None,
                        'id': f"SCR_{symbol}_{data.get('quarter', '')}",
                        'date': data.get('quarter', ''),
                        'financials': data,
                        'previous_financials': data.get('prev_quarter', {})
                    })
                    # Print with growth details
                    print(f"  ✅ {symbol}: Rev {data['revenue']:,.0f} (QoQ {data.get('qoq_rev_growth',0):.1f}%, YoY {data.get('yoy_rev_growth',0):.1f}%), PAT {data['pat']:,.0f} (QoQ {data.get('qoq_pat_growth',0):.1f}%, YoY {data.get('yoy_pat_growth',0):.1f}%)")
                else:
                    print(f"  ⚠️ No data for {symbol}")
                time.sleep(1.5)
            except Exception as e:
                print(f"  ❌ Error {symbol}: {e}")

        if announcements:
            print(f"✅ Fetched {len(announcements)} stocks from Screener.in")
            return announcements
        else:
            return []

    def _fetch_quarterly_data(self, symbol):
        """
        Scrape the 'quarters' table.
        Extract:
        - current quarter (latest)
        - previous quarter (QoQ)
        - same quarter last year (YoY)
        """
        url = f"https://www.screener.in/company/{symbol}/"
        try:
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, 'html.parser')
            data = {}
            prev_data = {}
            yoy_data = {}

            name_elem = soup.find('h1', class_='company-name')
            if name_elem:
                data['company_name'] = name_elem.text.strip()

            quarter_section = soup.find('section', id='quarters')
            if not quarter_section:
                return None

            table = quarter_section.find('table', class_='data-table')
            if not table:
                return None

            rows = table.find_all('tr')
            if len(rows) < 2:
                return None

            # Get all quarter column headers to identify positions
            header_row = rows[0]
            headers = [th.get_text(strip=True) for th in header_row.find_all('th')]
            # We need to know how many quarters are there
            # The last column is latest, second-last is previous, etc.
            # For YoY, we need to find the column with same month last year.

            # We'll collect all quarter data per metric
            # For each metric row, we get all quarter values
            # Then we pick last, second-last, and the one from 4 quarters ago (if available)
            # We'll store them in a dict for each metric

            # We'll iterate rows and collect all values
            all_quarters = []  # will hold list of dicts per row
            for row in rows[1:]:
                cells = row.find_all('td')
                if len(cells) < 2:
                    continue
                metric_text = cells[0].get_text(strip=True).lower()
                quarter_values = []
                for cell in cells[1:]:
                    text = cell.get_text(strip=True)
                    if text and text != '-' and text != '':
                        quarter_values.append(text)
                    else:
                        quarter_values.append(None)  # keep place
                all_quarters.append((metric_text, quarter_values))

            # Now we have list of (metric, values)
            # The values list is ordered from oldest to newest (left to right)
            # We'll get the latest non-null for current, previous non-null for prev, and 4th from last for YoY
            # We'll process each metric

            # We need to know the index of latest, prev, yoy
            # We'll find the last non-null index for each metric
            # For simplicity, we'll assume all metrics have the same number of non-null values (latest quarter same)
            # We'll find the latest index by looking at first metric with enough values

            # Better: get the list of all non-null values for a key metric (e.g., Sales) and use that to determine positions
            # Find sales row
            sales_row = None
            for metric, vals in all_quarters:
                if 'sales' in metric:
                    sales_row = vals
                    break
            if not sales_row:
                return None

            # Get indices of non-null values
            non_null_indices = [i for i, v in enumerate(sales_row) if v is not None]
            if len(non_null_indices) < 2:
                return None

            latest_idx = non_null_indices[-1]
            prev_idx = non_null_indices[-2] if len(non_null_indices) >= 2 else None
            # YoY: find the index that is 4 quarters before latest (if available)
            yoy_idx = None
            # We need to find the index that is exactly 4 positions before latest_idx in the non_null_indices list
            # If we have at least 4 non-null values
            if len(non_null_indices) >= 4:
                yoy_idx = non_null_indices[-4]  # 4th from last

            # Now iterate again to extract values for each metric at these indices
            for metric, vals in all_quarters:
                # Get values at indices
                latest_val = vals[latest_idx] if latest_idx < len(vals) and vals[latest_idx] is not None else None
                prev_val = vals[prev_idx] if prev_idx is not None and prev_idx < len(vals) and vals[prev_idx] is not None else None
                yoy_val = vals[yoy_idx] if yoy_idx is not None and yoy_idx < len(vals) and vals[yoy_idx] is not None else None

                if 'sales' in metric:
                    data['revenue'] = self._clean_number(latest_val) if latest_val else 0
                    prev_data['revenue'] = self._clean_number(prev_val) if prev_val else 0
                    yoy_data['revenue'] = self._clean_number(yoy_val) if yoy_val else 0
                elif 'operating profit' in metric and 'opm' not in metric:
                    data['ebitda'] = self._clean_number(latest_val) if latest_val else 0
                    prev_data['ebitda'] = self._clean_number(prev_val) if prev_val else 0
                    yoy_data['ebitda'] = self._clean_number(yoy_val) if yoy_val else 0
                elif 'net profit' in metric:
                    data['pat'] = self._clean_number(latest_val) if latest_val else 0
                    prev_data['pat'] = self._clean_number(prev_val) if prev_val else 0
                    yoy_data['pat'] = self._clean_number(yoy_val) if yoy_val else 0
                elif 'eps' in metric:
                    data['eps'] = self._clean_number(latest_val) if latest_val else 0
                    prev_data['eps'] = self._clean_number(prev_val) if prev_val else 0
                    yoy_data['eps'] = self._clean_number(yoy_val) if yoy_val else 0
                elif 'opm %' in metric:
                    data['ebitda_margin'] = self._clean_percent(latest_val) if latest_val else 0
                    prev_data['ebitda_margin'] = self._clean_percent(prev_val) if prev_val else 0
                    yoy_data['ebitda_margin'] = self._clean_percent(yoy_val) if yoy_val else 0
                elif 'pat margin' in metric:
                    data['pat_margin'] = self._clean_percent(latest_val) if latest_val else 0
                    prev_data['pat_margin'] = self._clean_percent(prev_val) if prev_val else 0
                    yoy_data['pat_margin'] = self._clean_percent(yoy_val) if yoy_val else 0

            if data.get('revenue', 0) == 0:
                return None

            # Compute growths
            # QoQ growth
            if prev_data.get('revenue', 0) > 0 and data['revenue'] > 0:
                data['qoq_rev_growth'] = ((data['revenue'] - prev_data['revenue']) / prev_data['revenue']) * 100
            else:
                data['qoq_rev_growth'] = 0
            if prev_data.get('pat', 0) > 0 and data.get('pat', 0) > 0:
                data['qoq_pat_growth'] = ((data['pat'] - prev_data['pat']) / prev_data['pat']) * 100
            else:
                data['qoq_pat_growth'] = 0

            # YoY growth
            if yoy_data.get('revenue', 0) > 0 and data['revenue'] > 0:
                data['yoy_rev_growth'] = ((data['revenue'] - yoy_data['revenue']) / yoy_data['revenue']) * 100
            else:
                data['yoy_rev_growth'] = 0
            if yoy_data.get('pat', 0) > 0 and data.get('pat', 0) > 0:
                data['yoy_pat_growth'] = ((data['pat'] - yoy_data['pat']) / yoy_data['pat']) * 100
            else:
                data['yoy_pat_growth'] = 0

            # Store previous and yoy data for reference
            data['prev_quarter'] = prev_data
            data['yoy_quarter'] = yoy_data
            data['quarter'] = 'Latest'

            # Compute margins if missing
            if 'ebitda_margin' not in data or data['ebitda_margin'] == 0:
                if data.get('ebitda', 0) > 0 and data['revenue'] > 0:
                    data['ebitda_margin'] = (data['ebitda'] / data['revenue']) * 100
            if 'pat_margin' not in data or data['pat_margin'] == 0:
                if data.get('pat', 0) > 0 and data['revenue'] > 0:
                    data['pat_margin'] = (data['pat'] / data['revenue']) * 100

            return data

        except Exception as e:
            print(f"  Scrape error for {symbol}: {e}")
            return None

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
