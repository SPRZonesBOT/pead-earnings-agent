import logging

from announcements.watcher_nse import get_nse_announcements
from announcements.watcher_bse import get_bse_announcements

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

logger = logging.getLogger(__name__)


def main():
    logger.info("Starting announcements fetch...")

    # NSE fetch
    try:
        results_nse = get_nse_announcements()
        logger.info(f"NSE returned {len(results_nse)} items.")
    except Exception as e:
        logger.error(f"NSE fetch failed: {e}")
        results_nse = []

    # BSE disabled stub
    try:
        results_bse = get_bse_announcements()
        logger.info(f"BSE returned {len(results_bse)} items.")
    except Exception as e:
        logger.error(f"BSE fetch failed: {e}")
        results_bse = []

    all_results = results_nse + results_bse

    logger.info(f"Total announcements fetched: {len(all_results)}")

    for item in all_results:
        print(item)


if __name__ == "__main__":
    main()
