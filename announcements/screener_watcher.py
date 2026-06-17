# announcements/screener_watcher.py (Update)
import requests
from bs4 import BeautifulSoup
import time
import re
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

try:
    from config import STOCKS_LIST, NIFTY_200
except ImportError:
    # Fallback if config not found
    STOCKS_LIST = [
        'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'HINDUNILVR',
        'ICICIBANK', 'SBIN', 'KOTAKBANK', 'LT', 'BHARTIARTL'
    ]

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
        """
        Fetch data for stocks from config.
        If stocks_list is None, uses config.STOCKS_LIST or fallback.
        """
        if stocks_list is None:
            try:
                from config import STOCKS_LIST
                stocks = STOCKS_LIST
            except ImportError:
                # Fallback to NIFTY_200 if available
                try:
                    from config import NIFTY_200
                    stocks = NIFTY_200
                except ImportError:
                    # Final fallback: 30 stocks
                    stocks = [
                        'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'HINDUNILVR',
                        'ICICIBANK', 'SBIN', 'KOTAKBANK', 'LT', 'BHARTIARTL',
                        'ITC', 'WIPRO', 'HCLTECH', 'ASIANPAINT', 'TITAN',
                        'MARUTI', 'TATAMOTORS', 'SUNPHARMA', 'NTPC', 'POWERGRID'
                    ]
        else:
            stocks = stocks_list

        print(f"📊 Scanning {len(stocks)} stocks...")

        announcements = []
        count = 0
        for symbol in stocks:
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
                    # Print progress
                    print(f"  [{count}/{len(stocks)}] ✅ {symbol}: Rev {data['revenue']:,.0f} (QoQ {data.get('qoq_rev_growth',0):.1f}%, PAT {data.get('pat',0):,.0f})")
                else:
                    print(f"  [{count}/{len(stocks)}] ⚠️ No data for {symbol}")
                time.sleep(1.2)  # Rate limit
            except Exception as e:
                print(f"  [{count}/{len(stocks)}] ❌ Error {symbol}: {e}")
                time.sleep(0.5)

        if announcements:
            print(f"✅ Fetched {len(announcements)} stocks from Screener.in")
            return announcements
        else:
            return []

    # ... rest of the class remains the same as before ...
    # (Keep _fetch_quarterly_data, _clean_number, _clean_percent, download_pdf)
