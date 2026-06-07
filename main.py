import logging
from typing import List, Dict

from announcements.watcher_nse import get_nse_announcements

# ─── Logging Setup ─────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─── Main Orchestrator ─────────────────────────────────────────────
def main():
    logger.info("=" * 50)
    logger.info("📢 Announcement Fetcher Started (NSE Only)")
    logger.info("=" * 50)

    all_results: List[Dict] = []

    # ─── NSE ───────────────────────────────────────────────────────
    logger.info("⏳ Fetching NSE announcements...")
    try:
        nse_results = get_nse_announcements()
        logger.info(f"✅ NSE returned {len(nse_results)} items.")
        all_results.extend(nse_results)
    except Exception as e:
        logger.error(f"❌ NSE fetch failed: {e}")

    # ─── BSE — Disabled ────────────────────────────────────────────
    logger.info("⏭️  BSE is disabled. Skipping...")

    # ─── Summary ───────────────────────────────────────────────────
    logger.info("=" * 50)
    logger.info(f"📊 Total announcements fetched: {len(all_results)}")
    logger.info("=" * 50)

    if not all_results:
        logger.warning("⚠️  No announcements found from any source.")
        return

    # ─── Display Results ───────────────────────────────────────────
    print("\n" + "=" * 80)
    print(f"{'📢 LATEST ANNOUNCEMENTS':^80}")
    print("=" * 80)

    for idx, item in enumerate(all_results, 1):
        print(f"\n{'─' * 80}")
        print(f"  #{idx}")
        print(f"  🏢 Company : {item.get('company', 'N/A')}")
        print(f"  🔖 Symbol  : {item.get('symbol', 'N/A')}")
        print(f"  📅 Date    : {item.get('date', 'N/A')}")
        print(f"  📝 Subject : {item.get('subject', 'N/A')}")
        print(f"  🔗 Source  : {item.get('source', 'N/A')}")

        pdf_url = item.get('pdf_url', '')
        if pdf_url:
            print(f"  📄 PDF     : {pdf_url}")

    print("\n" + "=" * 80)
    print(f"{'✅ DONE':^80}")
    print("=" * 80)


# ─── Entry Point ──────────────────────────────────────────────────
if __name__ == "__main__":
    main()
