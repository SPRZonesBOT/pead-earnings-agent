import logging

logger = logging.getLogger(__name__)


def get_bse_announcements():
    """
    BSE source is temporarily disabled due to persistent redirect loop issues.
    Returns empty list gracefully without crashing.
    """
    logger.warning("BSE source disabled — returns empty list")
    return []
