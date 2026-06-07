from announcements.watcher_bse import get_bse_announcements
from announcements.watcher_nse import get_nse_announcements
import schedule
import time
from datetime import datetime
from announcements.watcher_bse import watch_bse          # ✅ Updated import
from announcements.watcher_nse import watch_nse          # ✅ Updated import
from notifier_telegram import send_telegram_alert
from database.db import db                               # ✅ Updated import
from config import POLLING_INTERVAL
import logging

# Setup logging
logging.basicConfig(
    filename="logs/watcher.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def run_watchers():
    """BSE aur NSE watchers run karo"""
    print(f"\n{'='*90}")
    print(f"⏰ Cycle at {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")
    print(f"{'='*90}")
    
    watch_bse()
    watch_nse()

def process_announcements():
    """Announcements ko process karo aur alerts bhejo"""
    announcements = db.get_unprocessed_announcements()
    
    if announcements:
        print(f"\n📢 Processing {len(announcements)} announcements...")
        
        for ann_id, source, company, symbol, subject in announcements:
            # Send Telegram alert
            send_telegram_alert(
                company=company,
                subject=subject,
                source=source,
                ann_datetime=datetime.now().isoformat(),
                pdf_link=None
            )
            
            # Mark as processed
            db.mark_announcement_processed(ann_id)
            
            logging.info(f"Processed: {company} - {source}")

def job_scheduler():
    """Main scheduler"""
    schedule.every(POLLING_INTERVAL).seconds.do(run_watchers)
    schedule.every(1).minutes.do(process_announcements)
    
    print("🟢 Scheduler started...")
    print(f"📊 Polling interval: {POLLING_INTERVAL} seconds")
    
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    try:
        print(f"""
╔═══════════════════════════════════════════════════════════╗
║     🚀 PEAD AGENT - Live Result Announcements Monitor     ║
║     Version 1.0 - MVP (Ingestion + Alerts)                 ║
╚═══════════════════════════════════════════════════════════╝
        """)
        
        job_scheduler()
    
    except KeyboardInterrupt:
        print("\n🛑 Scheduler stopped by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        logging.error(f"Fatal error: {e}")
