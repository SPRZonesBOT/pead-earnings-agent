import logging
from announcements.watcher_bse import get_bse_announcements
from announcements.watcher_nse import get_nse_announcements

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point for PEAD Earnings Agent."""
    logger.info("🚀 Starting PEAD Earnings Agent...")

    # Fetch NSE announcements
    try:
        logger.info("Fetching NSE Announcements...")
        nse_data = get_nse_announcements()
        logger.info(f"NSE: {len(nse_data)} announcements found")
    except Exception as e:
        logger.error(f"NSE fetch crashed: {e}")
        nse_data = []

    # Fetch BSE announcements
    try:
        logger.info("Fetching BSE Announcements...")
        bse_data = get_bse_announcements()
        logger.info(f"BSE: {len(bse_data)} announcements found")
    except Exception as e:
        logger.error(f"BSE fetch crashed: {e}")
        bse_data = []

    # Combine results
    all_announcements = nse_data + bse_data

    if not all_announcements:
        logger.warning("⚠️ No announcements found. This is expected if markets are closed or no new filings today.")
        return

    # Pretty print table
    print("\n" + "=" * 110)
    print(f"{'SOURCE':<8} | {'DATE':<14} | {'COMPANY':<30} | SUBJECT")
    print("=" * 110)

    for ann in all_announcements:
        company = ann["company"]
        if len(company) > 28:
            company = company[:27] + ".."
        print(f"{ann['source']:<8} | {ann['date']:<14} | {company:<30} | {ann['subject']}")

    print("=" * 110)
    logger.info("✅ Done!")


if __name__ == "__main__":
    main()
