# announcements/bse_watcher.py (API-based)
import requests
import json
from datetime import datetime, timedelta

class BSEWatcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Referer': 'https://www.bseindia.com/'
        })

    def get_financial_results(self):
        """BSE API se announcements fetch karein"""
        try:
            # BSE ka corporate announcements API (example)
            # Real endpoint often: https://api.bseindia.com/BseIndiaAPI/api/Announcements
            # But we'll use a known working method: scraping via requests with proper params
            
            url = "https://www.bseindia.com/corporates/ann/GetAnnouncements.aspx"
            params = {
                'mode': 'M',
                'pageid': '1',
                'field': 'anndate',
                'dir': 'DESC'
            }
            response = self.session.get(url, params=params, timeout=15)
            if response.status_code != 200:
                print(f"BSE API returned status {response.status_code}")
                return self._get_mock_data()
            
            data = response.json()
            announcements = []
            
            for item in data.get('Table', []):
                subject = item.get('SUBJECT', '')
                if 'Financial Results' not in subject and 'Outcome of Board Meeting' not in subject:
                    continue
                
                # Extract symbol from COMPANY_NAME or SCRIP_CD
                scrip_code = item.get('SCRIP_CD', '')
                symbol = self._map_scrip_to_symbol(scrip_code) or item.get('COMPANY_NAME', '')[:10].upper()
                
                pdf_url = item.get('ATTACHMENT', '')
                if pdf_url and not pdf_url.startswith('http'):
                    pdf_url = 'https://www.bseindia.com' + pdf_url
                
                announcements.append({
                    'symbol': symbol,
                    'company': item.get('COMPANY_NAME', ''),
                    'scrip_code': scrip_code,
                    'pdf_url': pdf_url,
                    'id': f"{symbol}_{item.get('ANNDATE', '')}",
                    'date': item.get('ANNDATE', ''),
                    'subject': subject
                })
            
            if announcements:
                print(f"✅ Found {len(announcements)} result announcements via API.")
                return announcements[:10]
            else:
                print("⚠️ No result announcements in API response.")
                return self._get_mock_data()
                
        except Exception as e:
            print(f"❌ BSE API error: {e}")
            return self._get_mock_data()

    def _map_scrip_to_symbol(self, scrip_code):
        """Scrip code to symbol mapping (commonly known)"""
        mapping = {
            '500325': 'RELIANCE', '500570': 'TCS', '500180': 'HDFCBANK',
            '500875': 'ITC', '500696': 'HINDUNILVR', '500247': 'KOTAKBANK',
            '532174': 'ICICIBANK', '500209': 'INFY', '532540': 'SBIN',
            '500010': 'HDFC', '500111': 'BAJAJFINSV', '532977': 'BHARTIARTL'
        }
        return mapping.get(str(scrip_code), None)

    def download_pdf(self, pdf_url):
        if not pdf_url:
            return None
        try:
            response = self.session.get(pdf_url, timeout=30)
            if response.status_code == 200 and 'application/pdf' in response.headers.get('content-type', ''):
                filename = f"temp_{int(datetime.now().timestamp())}.pdf"
                with open(filename, 'wb') as f:
                    f.write(response.content)
                return filename
        except Exception as e:
            print(f"PDF download error: {e}")
        return None

    def _get_mock_data(self):
        print("🔄 Using mock data for testing...")
        return [
            {
                'symbol': 'RELIANCE', 'company': 'Reliance Industries Ltd',
                'pdf_url': None, 'id': 'REL_MOCK', 'date': '16-Jun-2025',
                'close_price': 2850, 'volume': 1500000, 'avg_volume': 1200000
            },
            {
                'symbol': 'TCS', 'company': 'Tata Consultancy Services',
                'pdf_url': None, 'id': 'TCS_MOCK', 'date': '16-Jun-2025',
                'close_price': 4200, 'volume': 800000, 'avg_volume': 650000
            },
            {
                'symbol': 'HDFC', 'company': 'HDFC Bank Ltd',
                'pdf_url': None, 'id': 'HDFC_MOCK', 'date': '16-Jun-2025',
                'close_price': 1650, 'volume': 2000000, 'avg_volume': 1800000
            }
        ]
