from announcements.scraper import get_bse_announcements
from announcements.parser import parse_announcements, filter_by_date

def main():
    print("🚀 PEAD Earnings Agent starting...\n")
    
    # 1. Fetch Data
    print("Step 1️⃣: Fetching announcements from BSE...")
    html_data = get_bse_announcements()
    
    if html_data:
        # 2. Parse Data
        print("\nStep 2️⃣: Parsing and filtering PEAD-related announcements...")
        announcements = parse_announcements(html_data)
        
        # 3. Filter Recent Announcements
        recent = filter_by_date(announcements, days=7)
        
        # 4. Display Results
        print(f"\n📊 Found {len(recent)} PEAD-related announcements:\n")
        print("-" * 60)
        
        for i, ann in enumerate(recent, 1):
            print(f"{i}. 🏢 {ann['company']}")
            print(f"   📝 {ann['announcement']}")
            print(f"   📅 Date: {ann['date']}")
            print(f"   🏷️ Category: {ann['category']}")
            print("-" * 60)
        
        if not recent:
            print("⚠️ No PEAD-related announcements found in the last 7 days.\n")
    
    else:
        print("❌ Failed to fetch data from BSE. Check your internet connection.\n")
    
    print("✅ Process completed!")

if __name__ == "__main__":
    main()
