# announcements/screener_watcher.py
import requests
from bs4 import BeautifulSoup
import time
import re
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import FULL_SCAN_STOCKS, QUICK_SCAN_STOCKS

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
        if stocks_list is None:
            stocks_list = FULL_SCAN_STOCKS
        if isinstance(stocks_list, str):
            stocks_list = QUICK_SCAN_STOCKS if stocks_list.lower() == 'quick' else FULL_SCAN_STOCKS

        print(f"📊 Scanning {len(stocks_list)} stocks...")
        announcements = []
        count = 0
        for symbol in stocks_list:
            count += 1
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
                    print(f"  [{count}/{len(stocks_list)}] ✅ {symbol}: Rev {data['revenue']:,.0f}, PAT {data['pat']:,.0f}, P/E {data.get('pe_ratio',0):.1f}")
                else:
                    print(f"  [{count}/{len(stocks_list)}] ⚠️ No data for {symbol}")
                time.sleep(1.2)
            except Exception as e:
                print(f"  [{count}/{len(stocks_list)}] ❌ Error {symbol}: {e}")
                time.sleep(0.5)
        if announcements:
            print(f"✅ Fetched {len(announcements)} stocks from Screener.in")
        return announcements

    def _fetch_quarterly_data(self, symbol):
        url = f"https://www.screener.in/company/{symbol}/"
        try:
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                return None
            soup = BeautifulSoup(response.text, 'html.parser')
            data = {}

            # ---- Company name ----
            name_elem = soup.find('h1', class_='company-name')
            if name_elem:
                data['company_name'] = name_elem.text.strip()

            # ---- Current Market Price (CMP) ----
            price_div = soup.find('div', class_='font-size-18 strong line-height-14')
            if price_div:
                price_span = price_div.find('span')
                if price_span:
                    price_text = price_span.get_text(strip=True).replace('₹', '').replace(',', '').strip()
                    try:
                        data['current_price'] = float(price_text)
                    except:
                        data['current_price'] = 0.0

            # ---- Top Ratios (P/E, P/B, Div Yield, Market Cap) ----
            ratios_ul = soup.find('ul', id='top-ratios')
            if ratios_ul:
                for li in ratios_ul.find_all('li'):
                    text = li.get_text(strip=True)
                    if 'Market Cap' in text:
                        m = re.search(r'₹\s*([\d,]+)\s*Cr\.?', text)
                        if m:
                            data['market_cap'] = float(m.group(1).replace(',', ''))
                    elif 'Stock P/E' in text:
                        m = re.search(r'([\d.]+)', text)
                        if m:
                            data['pe_ratio'] = float(m.group(1))
                    elif 'Book Value' in text:
                        m = re.search(r'₹\s*([\d.]+)', text)
                        if m:
                            data['book_value'] = float(m.group(1))
                    elif 'Dividend Yield' in text:
                        m = re.search(r'([\d.]+)\s*%', text)
                        if m:
                            data['div_yield'] = float(m.group(1))

            # ---- Quarterly Table ----
            quarter_section = soup.find('section', id='quarters')
            if not quarter_section:
                return None
            table = quarter_section.find('table', class_='data-table')
            if not table:
                return None
            rows = table.find_all('tr')
            if len(rows) < 2:
                return None

            # Parse each metric row
            all_quarters = []
            for row in rows[1:]:
                cells = row.find_all('td')
                if len(cells) < 2:
                    continue
                metric = cells[0].get_text(strip=True).lower()
                vals = []
                for cell in cells[1:]:
                    txt = cell.get_text(strip=True)
                    vals.append(txt if txt and txt != '-' else None)
                all_quarters.append((metric, vals))

            # Identify latest, previous, and YoY indices using Sales row
            sales_row = None
            for metric, vals in all_quarters:
                if 'sales' in metric:
                    sales_row = vals
                    break
            if not sales_row:
                return None
            non_null = [i for i, v in enumerate(sales_row) if v is not None]
            if len(non_null) < 2:
                return None
            latest_idx = non_null[-1]
            prev_idx = non_null[-2] if len(non_null) >= 2 else None
            yoy_idx = non_null[-4] if len(non_null) >= 4 else None

            # Extract values
            prev_data = {}
            yoy_data = {}
            for metric, vals in all_quarters:
                latest = vals[latest_idx] if latest_idx < len(vals) and vals[latest_idx] is not None else None
                prev = vals[prev_idx] if prev_idx is not None and prev_idx < len(vals) and vals[prev_idx] is not None else None
                yoy = vals[yoy_idx] if yoy_idx is not None and yoy_idx < len(vals) and vals[yoy_idx] is not None else None

                if 'sales' in metric:
                    data['revenue'] = self._clean_number(latest)
                    prev_data['revenue'] = self._clean_number(prev)
                    yoy_data['revenue'] = self._clean_number(yoy)
                elif 'operating profit' in metric and 'opm' not in metric:
                    data['ebitda'] = self._clean_number(latest)
                    prev_data['ebitda'] = self._clean_number(prev)
                    yoy_data['ebitda'] = self._clean_number(yoy)
                elif 'net profit' in metric:
                    data['pat'] = self._clean_number(latest)
                    prev_data['pat'] = self._clean_number(prev)
                    yoy_data['pat'] = self._clean_number(yoy)
                elif 'eps' in metric:
                    data['eps'] = self._clean_number(latest)
                    prev_data['eps'] = self._clean_number(prev)
                    yoy_data['eps'] = self._clean_number(yoy)
                elif 'opm %' in metric:
                    data['ebitda_margin'] = self._clean_percent(latest)
                    prev_data['ebitda_margin'] = self._clean_percent(prev)
                    yoy_data['ebitda_margin'] = self._clean_percent(yoy)
                elif 'pat margin' in metric:
                    data['pat_margin'] = self._clean_percent(latest)
                    prev_data['pat_margin'] = self._clean_percent(prev)
                    yoy_data['pat_margin'] = self._clean_percent(yoy)

            if data.get('revenue', 0) == 0:
                return None

            # QoQ / YoY growths
            if prev_data.get('revenue', 0) > 0:
                data['qoq_rev_growth'] = ((data['revenue'] - prev_data['revenue']) / prev_data['revenue']) * 100
            else:
                data['qoq_rev_growth'] = 0
            if prev_data.get('pat', 0) > 0:
                data['qoq_pat_growth'] = ((data['pat'] - prev_data['pat']) / prev_data['pat']) * 100
            else:
                data['qoq_pat_growth'] = 0
            if yoy_data.get('revenue', 0) > 0:
                data['yoy_rev_growth'] = ((data['revenue'] - yoy_data['revenue']) / yoy_data['revenue']) * 100
            else:
                data['yoy_rev_growth'] = 0
            if yoy_data.get('pat', 0) > 0:
                data['yoy_pat_growth'] = ((data['pat'] - yoy_data['pat']) / yoy_data['pat']) * 100
            else:
                data['yoy_pat_growth'] = 0

            data['prev_quarter'] = prev_data
            data['yoy_quarter'] = yoy_data
            data['quarter'] = 'Latest'

            # Ensure margins
            if 'ebitda_margin' not in data or data['ebitda_margin'] == 0:
                if data.get('ebitda', 0) > 0 and data['revenue'] > 0:
                    data['ebitda_margin'] = (data['ebitda'] / data['revenue']) * 100
            if 'pat_margin' not in data or data['pat_margin'] == 0:
                if data.get('pat', 0) > 0 and data['revenue'] > 0:
                    data['pat_margin'] = (data['pat'] / data['revenue']) * 100

            return data
        except Exception as e:
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
