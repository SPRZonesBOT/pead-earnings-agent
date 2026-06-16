# announcements/screener_watcher.py
import requests
import json
import time

class ScreenerWatcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Referer': 'https://www.screener.in/'
        })

    def get_financial_results(self):
        """Fetch top Nifty stocks using Screener.in API"""
        nifty_symbols = [
            'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'HINDUNILVR',
            'ICICIBANK', 'SBIN', 'KOTAKBANK', 'LT', 'BHARTIARTL',
            'ITC', 'WIPRO', 'HCLTECH', 'ASIANPAINT', 'TITAN'
        ]
        announcements = []
        for symbol in nifty_symbols:
            try:
                data = self._fetch_quarterly_data_api(symbol)
                if data:
                    announcements.append({
                        'symbol': symbol,
                        'company': data.get('company_name', symbol),
                        'pdf_url': None,
                        'id': f"SCR_{symbol}_{data.get('quarter', '')}",
                        'date': data.get('quarter', ''),
                        'financials': data
                    })
                    print(f"  ✅ {symbol}: Revenue={data.get('revenue',0):,.0f}, PAT={data.get('pat',0):,.0f}, Margin={data.get('ebitda_margin',0):.1f}%")
                else:
                    print(f"  ⚠️ No data for {symbol}")
                time.sleep(0.5)  # Rate limit
            except Exception as e:
                print(f"  ❌ Error {symbol}: {e}")

        if announcements:
            print(f"✅ Fetched {len(announcements)} stocks from Screener.in API")
            return announcements
        else:
            print("⚠️ No data from Screener API. Falling back to mock.")
            return []

    def _fetch_quarterly_data_api(self, symbol):
        """
        Use Screener.in's JSON API for quarterly results
        Endpoint: https://www.screener.in/api/company/{symbol}/quick/
        """
        url = f"https://www.screener.in/api/company/{symbol}/quick/"
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code != 200:
                return None

            data = response.json()
            if not data:
                return None

            result = {}
            # Extract company name
            result['company_name'] = data.get('company_name', symbol)

            # Quarterly results are in 'quarters' key
            quarters = data.get('quarters', [])
            if not quarters:
                return None

            # Latest quarter is first in list
            latest = quarters[0]
            result['quarter'] = latest.get('date', '')

            # Map fields (keys might be 'revenue', 'profit', etc.)
            result['revenue'] = latest.get('revenue', 0) or latest.get('sales', 0)
            result['pat'] = latest.get('profit_after_tax', 0) or latest.get('net_profit', 0)
            result['ebitda'] = latest.get('ebitda', 0)
            result['eps'] = latest.get('eps', 0)

            # Margins from latest data or compute
            ebitda_margin = latest.get('ebitda_margin')
            if ebitda_margin is None:
                ebitda_margin = (result['ebitda'] / result['revenue']) * 100 if result['revenue'] else 0
            result['ebitda_margin'] = ebitda_margin

            pat_margin = latest.get('net_profit_margin')
            if pat_margin is None:
                pat_margin = (result['pat'] / result['revenue']) * 100 if result['revenue'] else 0
            result['pat_margin'] = pat_margin

            # Also store previous quarters for growth later (optional)
            result['previous_quarters'] = quarters[1:] if len(quarters) > 1 else []

            return result

        except Exception as e:
            print(f"  API error for {symbol}: {e}")
            return None

    def download_pdf(self, pdf_url):
        return None  # Screener doesn't provide PDFs
