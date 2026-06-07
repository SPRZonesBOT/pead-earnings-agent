import requests
from bs4 import BeautifulSoup

def get_bse_announcements():
    print("🔍 Fetching announcements from BSE...")
    
    # BSE Corporate Announcements URL
    url = "https://www.bseindia.com/corporates/ann.html"
    
    # Browser jaisa dikhne ke liye headers zaroori hain
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            print("✅ Successfully connected to BSE!")
            # Yahan hum parsing logic baad mein add karenge
            return "Raw Data Received"
        else:
            print(f"❌ Error: Received status code {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return None

if __name__ == "__main__":
    get_bse_announcements()
