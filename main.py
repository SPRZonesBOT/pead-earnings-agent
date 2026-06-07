import logging
import schedule
import time
import sys
from datetime import datetime
from announcements.watcher_nse import get_nse_announcements
from announcements.watcher_bse import get_bse_announcements

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = False

if not logger.handlers:
    file_handler = logging.FileHandler("watcher.log", encoding="utf-8")
    console_handler = logging.StreamHandler(sys.stdout)

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


def run_watcher():
    print("\n" + "=" * 80)
    print("PEAD EARNINGS AGENT - ANNOUNCEMENT WATCHER MODULE 1")
    print("=" * 80)
    print(f"Started at: {datetime.now()}")
    print("Logs: watcher.log")
    print("Press Ctrl+C to stop\n")

    print("=" * 80)
    print(f"Checking for new announcements at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    nse_items = []
    bse_items = []

    try:
        logger.info("Fetching NSE announcements...")
        nse_items = get_nse_announcements()
        logger.info(f"NSE fetched: {len(nse_items)} items")
    except Exception as e:
        logger.error(f"NSE Error: {e}", exc_info=True)

    try:
        logger.info("Fetching BSE announcements...")
        bse_items = get_bse_announcements()
        logger.info(f"BSE fetched: {len(bse_items)} items")
    except Exception as e:
        logger.error(f"BSE Error: {e}", exc_info=True)

    all_items = nse_items + bse_items

    if all_items:
        print(f"\n{'-' * 80}")
        print(f"TOTAL ALERTS: {len(all_items)}")
        print(f"{'-' * 80}\n")

        for idx, item in enumerate(all_items, 1):
            print(f"Alert #{idx}")
            print(f"Date:    {item.get('date', 'N/A')}")
            print(f"Company: {item.get('company', 'N/A')}")
            print(f"Symbol:  {item.get('symbol', 'N/A')}")
            print(f"Subject: {item.get('subject', 'N/A')}")
            if item.get("pdf_url"):
                print(f"PDF:     {item.get('pdf_url')}")
            print(f"Source:  {item.get('source', 'N/A')}")
            print()
    else:
        print("No relevant announcements at this time.")

    print("=" * 80 + "\n")


def schedule_watcher():
    POLLING_INTERVAL = 5
    schedule.every(POLLING_INTERVAL).minutes.do(run_watcher)
    logger.info(f"Scheduler started. Polling every {POLLING_INTERVAL} minutes.")


if __name__ == "__main__":
    try:
        run_watcher()
        schedule_watcher()

        while True:
            schedule.run_pending()
            time.sleep(30)

    except KeyboardInterrupt:
        print("\nWatcher stopped by user.")
        logger.info("Watcher stopped by user.")
    except Exception as e:
        print(f"\nCritical error: {e}")
        logger.critical(f"Critical error: {e}", exc_info=True)
