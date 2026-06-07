from announcements.scraper import get_bse_announcements

def main():
    print("🚀 PEAD Earnings Agent starting...")
    
    # 1. Fetch Data
    data = get_bse_announcements()
    
    if data:
        print("📊 Data fetch ho gaya hai, ab parsing ki baari hai.")
    else:
        print("⚠️ Data fetch nahi ho paaya.")

if __name__ == "__main__":
    main()
