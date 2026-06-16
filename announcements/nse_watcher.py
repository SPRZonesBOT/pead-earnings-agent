# announcements/nse_watcher.py
import requests
import json
from datetime import datetime, timedelta

class NSEWatcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.nseindia.com/'
        })
        # Get initial cookies
        self.session.get('https://www.nseindia.com', timeout=10)

    def get_financial_results(self, days=7):
        """
        Fetch corporate announcements from NSE API.
        Returns list of dicts with symbol, company, pdf_url, etc.
        """
        from_date = (datetime.now() - timedelta(days=days)).strftime('%d-%m-%Y')
        to_date = datetime.now().strftime('%d-%m-%Y')
        
        url = f"https://www.nseindia.com/api/corporate-announcements?index=all&from_date={from_date}&to_date={to_date}"
        
        try:
            response = self.session.get(url, timeout=15)
            
            if response.status_code != 200:
                print(f"⚠️ NSE API returned {response.status_code}")
                return self._scrape_nse_website(days)
            
            # Parse JSON
            try:
                data = response.json()
            except json.JSONDecodeError:
                print("⚠️ NSE API returned invalid JSON. Falling back to HTML scraping.")
                return self._scrape_nse_website(days)
            
            # Check if data is a list
            if isinstance(data, list):
                announcements = []
                for item in data:
                    # If item is dict, extract fields
                    if isinstance(item, dict):
                        subject = item.get('subject', '')
                        if 'financial results' in subject.lower() or 'outcome of board meeting' in subject.lower():
                            ann = {
                                'symbol': item.get('symbol', ''),
                                'company': item.get('company', ''),
                                'pdf_url': item.get('attachment_url', ''),
                                'id': f"{item.get('symbol')}_{item.get('announcement_id', '')}",
                                'date': item.get('ann_date', ''),
                                'subject': subject,
                                'close_price': 0,
                                'volume': 0,
                                'avg_volume': 0
                            }
                            announcements.append(ann)
                if announcements:
                    print(f"✅ Found {len(announcements)} financial result announcements from NSE API.")
                    return announcements[:15]
                else:
                    print("⚠️ No financial results found in NSE API response.")
                    return self._scrape_nse_website(days)
            
            # If data is a dict with a 'data' key
            elif isinstance(data, dict):
                items = data.get('data', [])
                if not items:
                    items = data.get('announcements', [])
                if items:
                    announcements = []
                    for item in items:
                        if isinstance(item, dict):
                            subject = item.get('subject', '')
                            if 'financial results' in subject.lower() or 'outcome of board meeting' in subject.lower():
                                ann = {
                                    'symbol': item.get('symbol', ''),
                                    'company': item.get('company', ''),
                                    'pdf_url': item.get('attachment_url', ''),
                                    'id': f"{item.get('symbol')}_{item.get('announcement_id', '')}",
                                    'date': item.get('ann_date', ''),
                                    'subject': subject
                                }
                                announcements.append(ann)
                    if announcements:
                        print(f"✅ Found {len(announcements)} financial result announcements from NSE API.")
                        return announcements[:15]
            
            # If we reach here, no valid data found
            print("⚠️ NSE API returned unexpected format. Falling back to HTML scraping.")
            return self._scrape_nse_website(days)
            
        except Exception as e:
            print(f"❌ NSE API error: {e}")
            return self._scrape_nse_website(days)

    def _scrape_nse_website(self, days=7):
        """
        Fallback: Scrape announcements from NSE's corporate announcements page using HTML parsing.
        This is less reliable but works when API fails.
        """
        print("🔄 Attempting HTML scraping from NSE website...")
        try:
            from bs4 import BeautifulSoup
            
            # Use the main NSE announcements page
            url = "https://www.nseindia.com/corporate/corporate-announcements"
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            # Look for tables with announcements
            tables = soup.find_all('table')
            announcements = []
            
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 4:
                        # Try to find subject cell
                        subject = cells[3].get_text(strip=True) if len(cells) > 3 else ''
                        if 'financial results' in subject.lower() or 'outcome of board meeting' in subject.lower():
                            symbol = cells[1].get_text(strip=True) if len(cells) > 1 else ''
                            company = cells[2].get_text(strip=True) if len(cells) > 2 else ''
                            # Extract PDF link from row
                            pdf_link = None
                            link = row.find('a', href=True)
                            if link and '.pdf' in link['href'].lower():
                                pdf_link = link['href']
                                if not pdf_link.startswith('http'):
                                    pdf_link = 'https://www.nseindia.com' + pdf_link
                            ann = {
                                'symbol': symbol,
                                'company': company,
                                'pdf_url': pdf_link,
                                'id': f"{symbol}_{datetime.now().strftime('%Y%m%d')}",
                                'date': datetime.now().strftime('%d-%b-%Y'),
                                'subject': subject
                            }
                            announcements.append(ann)
            
            if announcements:
                print(f"✅ Found {len(announcements)} announcements via HTML scraping.")
                return announcements[:10]
            else:
                print("⚠️ No announcements found via HTML scraping.")
                return []
                
        except Exception as e:
            print(f"❌ HTML scraping error: {e}")
            return []

    def download_pdf(self, pdf_url):
        if not pdf_url:
            return None
        try:
            # Need to use same session with cookies
            response = self.session.get(pdf_url, timeout=30)
            if response.status_code == 200 and 'application/pdf' in response.headers.get('content-type', ''):
                filename = f"temp_{int(datetime.now().timestamp())}.pdf"
                with open(filename, 'wb') as f:
                    f.write(response.content)
                return filename
        except Exception as e:
            print(f"PDF download error: {e}")
        return None
