# announcements/nse_watcher.py
import requests
from datetime import datetime, timedelta

class NSEWatcher:
    def get_financial_results(self):
        from_date = (datetime.now() - timedelta(days=7)).strftime('%d-%m-%Y')
        to_date = datetime.now().strftime('%d-%m-%Y')
        url = f"https://www.nseindia.com/api/corporate-announcements?index=all&from_date={from_date}&to_date={to_date}"
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json'
        }
        session = requests.Session()
        # NSE requires a cookie first
        session.get('https://www.nseindia.com', headers=headers)
        response = session.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            announcements = []
            for item in data:
                subject = item.get('subject', '')
                if 'financial results' in subject.lower() or 'outcome of board meeting' in subject.lower():
                    announcements.append({
                        'symbol': item.get('symbol'),
                        'company': item.get('company'),
                        'pdf_url': item.get('attachment_url'),
                        'id': str(item.get('announcement_id')),
                        'date': item.get('ann_date'),
                        'subject': subject
                    })
            if announcements:
                return announcements[:10]
        print("No NSE financial results found.")
        return []
