import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


def get_bse_announcements() -> List[Dict]:
    """
    BSE temporarily disabled.
    Returns empty list so the rest of the app continues to work.
    """
    logger.info("BSE is disabled. Skipping BSE announcements fetch.")
    return []


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = get_bse_announcements()
    print(f"BSE disabled. Returned {len(results)} items.")
