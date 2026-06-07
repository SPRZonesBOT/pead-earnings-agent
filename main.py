import logging
import schedule
import time
from datetime import datetime
from announcements.watcher_nse import get_nse_announcements
from announcements.watcher_bse import get_bse_announcements

# ─────────────────────────────────────────────
# Logging Setup
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('watcher.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Main Watcher Function
# ─────────────────────────────────────────────
def run_watcher():
    """
    Main watcher loop:
    1. Fetch NSE announcements
    2. Fetch BSE announcements
    3. Display filtered results
    """
    print("\n" + "="*80)
    print(f"🔍 Checking for new announcements at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

    nse_items = []
    bse_items = []

    # Fetch NSE announcements
    try:
        logger.info("Fetching NSE announcements...")
        nse_items = get_nse_announcements()
        if nse_items:
            logger.info(f"✅ NSE: {len(nse_items)} relevant announcements found")
        else:
            logger.warning("⚠️  NSE: No relevant announcements found")
    except Exception as e:
        logger.error(f"❌ NSE Error: {e}", exc_info=True)

    # Fetch BSE announcements
    try:
        logger.info("Fetching BSE announcements...")
        bse_items = get_bse_announcements()
        if bse_items:
            logger.info(f"✅ BSE: {len(bse_items)} relevant announcements found")
        else:
            logger.warning("⚠️  BSE: No relevant announcements found")
    except Exception as e:
        logger.error(f"❌ BSE Error: {e}", exc_info=True)

    # Combine and display results
    all_items = nse_items + bse_items

    if all_items:
        print(f"\n{'─'*80}")
        print(f"🎯 TOTAL ALERTS: {len(all_items)}")
        print(f"{'─'*80}\n")

        for idx, item in enumerate(all_items, 1):
            print(f"📌 Alert #{idx}")
            print(f"   📅 Date:    {item.get('date', 'N/A')}")
            print(f"   🏢 Company: {item.get('company', 'N/A')}")
            print(f"   📊 Symbol:  {item.get('symbol', 'N/A')}")
            print(f"   📄 Subject: {item.get('subject', 'N/A')}")
            if item.get('pdf_url'):
                print(f"   🔗 PDF:     {item.get('pdf_url')}")
            print(f"   🌐 Source:  {item.get('source', 'N/A')}")
            print()
    else:
        print("\n⚠️  No relevant announcements at this time.\n")

    print("="*80 + "\n")

# ─────────────────────────────────────────────
# Scheduler Setup
# ─────────────────────────────────────────────
def schedule_watcher():
    """Schedule the watcher to run every X minutes."""
    POLLING_INTERVAL = 5  # minutes (change as needed)
    schedule.every(POLLING_INTERVAL).minutes.do(run_watcher)
    logger.info(f"✅ Scheduler started. Polling every {POLLING_INTERVAL} minutes.")

# ─────────────────────────────────────────────
# Main Entry Point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    try:
        print("\n" + "="*80)
        print("🚀 PEAD EARNINGS AGENT - ANNOUNCEMENT WATCHER MODULE 1")
        print("="*80)
        print(f"⏰ Started at: {datetime.now()}")
        print(f"📝 Logs: watcher.log")
        print("⏸️  Press Ctrl+C to stop\n")

        # Run immediately
        run_watcher()

        # Then schedule
        schedule_watcher()

        # Keep running
        while True:
            schedule.run_pending()
            time.sleep(30)  # Check schedule every 30 seconds

    except KeyboardInterrupt:
        print("\n\n⛔ Watcher stopped by user.")
        logger.info("Watcher stopped by user.")
    except Exception as e:
        logger.critical(f"❌ Critical error: {e}", exc_info=True)
        print(f"\n❌ Critical error: {e}")
