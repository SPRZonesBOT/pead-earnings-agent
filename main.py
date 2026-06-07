import logging
from announcements.watcher_bse import get_bse_announcements
from announcements.watcher_nse import get_nse_announcements

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

def main():
    logger.info("Starting PEAD Earnings Agent...")

    try:
        logger.info("Fetching BSE Announcements...")
        bse_data = get_bse_announcements()
        logger.info(f"Total BSE Announcements found: {len(bse_data)}")
    except Exception as e:
        logger.error(f"BSE fetch crashed: {e}")
        bse_data = []

    try:
        logger.info("Fetching NSE Announcements...")
        nse_data = get_nse_announcements()
        logger.info(f"Total NSE Announcements found: {len(nse_data)}")
    except Exception as e:
        logger.error(f"NSE fetch crashed: {e}")
        nse_data = []

    all_announcements = bse_data + nse_data

    if not all_announcements:
        logger.warning("No new announcements found right now.")
        return

    print("\n" + "=" * 100)
    print(f"{'SOURCE':<8} | {'DATE':<12} | {'COMPANY':<25} | SUBJECT")
    print("=" * 100)

    for ann in all_announcements:
        company = ann["company"][:23] + ".." if len(ann["company"]) > 25 else ann["company"]
        print(f"{ann['source']:<8} | {ann['date']:<12} | {company:<25} | {ann['subject']}")

    print("=" * 100)

if __name__ == "__main__":
    main()
