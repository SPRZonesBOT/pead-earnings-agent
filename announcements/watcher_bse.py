import logging

logger = logging.getLogger(__name__)

def get_bse_announcements():
    logger.warning("BSE source disabled temporarily due to redirect loop.")
    return []
