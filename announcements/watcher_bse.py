import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
from config import BSE_ANNOUNCEMENTS_URL, HEADERS, RESULT_KEYWORDS, FOCUS_COMPANIES
from db import db

def clean_text(text):
    return re.sub(r"\s+", " ", text or "").strip()

def contains_any(text, keywords):
    text = (text or "").lower()
    return any(keyword.lower() in text for keyword in keywords)

def is_focus_company(company):
    company_upper = (company or "").upper()
    return any(name in company_upper for name in FOCUS_COMPANIES)

def fetch_bse_announcements():
    """BSE se live announcements fetch karo"""
    print("🔍 Fetching BSE announcements...")
    
    try:
        response = requests.get(BSE_ANNOUNCEMENTS_URL, headers=HEADERS, timeout=20)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"❌ BSE fetch error: {e}")
        return None

def parse_date(date_str):
    """Date parse karo"""
    date_str = clean_text(date_str)
    
    formats = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d/%m/%y",
        "%d-%m-%y",
        "%d %b %Y",
        "%d %B %Y",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    return None

def extract_pdf_link(row_element):
    """Table row se PDF link extract karo"""
    links = row_element.find_all("a")
    
    for link in links:
        href = link.get("href", "")
        if ".pdf" in href.lower() or "attachment" in href.lower():
            # Agar relative URL hai to absolute banao
            if href.startswith("/"):
                href = "https://www.bseindia.com" + href
            return href
    
    return None

def watch_bse():
    """BSE ko continuously watch karo"""
    html = fetch_bse_announcements()
    
    if not html:
        return
    
    soup = BeautifulSoup(html, "html.parser")
    rows_found = 0
    new_announcements = 0
    
    for tr in soup.find_all("tr"):
        tds = tr.find_all("td")
        
        if len(tds) < 3:
            continue
        
        rows_found += 1
        
        # Extract fields
        cells = [clean_text(td.get_text(" ", strip=True)) for td in tds]
        
        ann_date_str = cells[0] if len(cells) > 0 else None
        company = cells[1] if len(cells) > 1 else ""
        subject = " | ".join(cells[2:]) if len(cells) > 2 else ""
        
        company = clean_text(company)
        subject = clean_text(subject)
        
        if not company or not subject or not ann_date_str:
            continue
        
        # Parse date
        ann_datetime = parse_date(ann_date_str)
        if not ann_datetime:
            continue
        
        # Check if result-related
        is_result = contains_any(subject, RESULT_KEYWORDS)
        is_focus = is_focus_company(company)
        
        if not is_result:
            continue
        
        # Extract PDF link
        pdf_link = extract_pdf_link(tr)
        
        # Save to DB
        ann_id = db.insert_announcement(
            source="BSE",
            company_name=company,
            symbol="",
            ann_datetime=ann_datetime.isoformat(),
            subject=subject,
            ann_url="https://www.bseindia.com/corporates/ann.html",
            is_result=is_result
        )
        
        # Save document link if found
        if ann_id and pdf_link:
            db.insert_document(ann_id, "PDF", pdf_link)
            print(f"   📎 PDF link: {pdf_link[:80]}...")
        
        if ann_id:
            new_announcements += 1
    
    print(f"✅ BSE: {rows_found} rows parsed, {new_announcements} new announcements saved")

if __name__ == "__main__":
    watch_bse()
