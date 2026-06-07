import schedule
import time
from announcements.watcher_nse import get_nse_announcements
from announcements.watcher_bse import get_bse_announcements
from announcements.filters import process_announcements

def run_watcher():
    print("\n🔍 Checking for new announcements...")
    nse_items = get_nse_announcements()
    bse_items = get_bse_announcements()

    all_items = nse_items + bse_items
    filtered = process_announcements(all_items)

    for item in filtered:
        print(f"🔔 NEW RESULT ALERT: {item['company']} — {item['subject']} (Source: {item['source']})")
        # TODO: Trigger Document Fetcher (Module 2) here

if __name__ == "__main__":
    print("✅ Announcement Watcher Started (Ctrl+C to exit)")
    run_watcher()  # First run immediately
    schedule.every(5).minutes.do(run_watcher)  # Then every 5 mins

    while True:
        schedule.run_pending()
        time.sleep(30)
