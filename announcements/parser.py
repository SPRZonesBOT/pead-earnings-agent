from bs4 import BeautifulSoup
import re
from datetime import datetime

def parse_announcements(html_content):
    """Parse BSE announcements aur PEAD-related data extract karo"""
    
    print("📋 Parsing announcements...")
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # BSE table rows find karo
        rows = soup.find_all('tr')
        
        # PEAD-related keywords
        pead_keywords = ['results', 'earnings', 'quarterly', 'annual', 'dividend', 
                         'profit', 'revenue', 'financial', 'Q1', 'Q2', 'Q3', 'Q4']
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 3:
                company = cells[0].text.strip() if len(cells) > 0 else "N/A"
                announcement = cells[1].text.strip() if len(cells) > 1 else "N/A"
                date = cells[2].text.strip() if len(cells) > 2 else "N/A"
                
                # Check karo ke ye announcement PEAD-related hai ya nahi
                if any(keyword.lower() in announcement.lower() for keyword in pead_keywords):
                    announcements.append({
                        'company': company,
                        'announcement': announcement,
                        'date': date,
                        'category': 'PEAD'
                    })
        
        print(f"✅ Found {len(announcements)} PEAD-related announcements")
        return announcements
    
    except Exception as e:
        print(f"❌ Parsing Error: {e}")
        return []

def filter_by_date(announcements, days=7):
    """Recent announcements filter karo (last N days)"""
    filtered = [a for a in announcements if a['date']]
    return filtered[:days]
