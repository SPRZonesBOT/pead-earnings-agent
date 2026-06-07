import requests
from bs4 import BeautifulSoup
import json

def get_bse_announcements():
    """BSE se Corporate Announcements fetch karo"""
    
    print("🔍 Connecting to BSE...")
    
    # BSE Corporate Announcements URL
    url = "https://www.bseindia.com/corporates/ann.html"
    
    # Browser jaisa dikhne ke liye headers
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            print("✅ Connected to BSE successfully!")
            return response.text  # 🔑 HTML content return karo!
        
        else:
            print(f"❌ Error: Status code {response.status_code}")
            return None
    
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Check your internet connection")
        return None
    
    except requests.exceptions.Timeout:
        print("❌ Timeout Error: BSE server not responding")
        return None
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None

def get_mock_announcements():
    """Agar BSE connect nahi ho, toh mock data return karo (testing ke liye)"""
    
    print("📌 Using mock data for testing...")
    
    mock_html = """
    <table>
        <tr>
            <td>Reliance Industries</td>
            <td>Q3 FY2024 Results Announcement</td>
            <td>2025-01-15</td>
        </tr>
        <tr>
            <td>TCS</td>
            <td>Quarterly Earnings Report - Q3</td>
            <td>2025-01-10</td>
        </tr>
        <tr>
            <td>HDFC Bank</td>
            <td>Annual Financial Results Declared</td>
            <td>2025-01-12</td>
        </tr>
        <tr>
            <td>Infosys</td>
            <td>Dividend Announcement - FY2024</td>
            <td>2025-01-18</td>
        </tr>
        <tr>
            <td>ITC Limited</td>
            <td>Q3 Profit & Revenue Update</td>
            <td>2025-01-14</td>
        </tr>
    </table>
    """
    
    return mock_html
