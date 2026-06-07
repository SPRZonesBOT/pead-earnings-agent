"""
announcements/filters.py — Filter corporate announcements

Removes ONLY spam and duplicates.
Keeps everything else (relaxed filtering).
"""

import logging

logger = logging.getLogger(__name__)


# ── Keywords that indicate spam / irrelevant announcements ──
# ONLY these are removed — everything else passes through
SPAM_KEYWORDS = [
    "trading window",
    "trading window-xbrl",
    "window-xbrl",
    "disclosure under sebi takeover regulations",
    "disclosure pursuant to sebi takeover regulations",
    "secretarial compliance report",
    "secretarial compliance",
    "loss of share certificate",
    "issue of duplicate share certificate",
    "duplicate share certificate",
    "closure of trading window",
    "re-opening of trading window",
    "compliance certificate under regulation",
    "due date certificate",
    "soft copy of the newspaper",
    "newspaper advertisement",
    "newspaper publication",
    "extract of annual return",
    "format of annual return",
    "investor complaints",
    "investor complaint",
    "regulation 29",
    "regulation 31",
    "regulation 40",
    "intimation of loss",
    "shareholding pattern statement",
    "shareholding pattern - promoter",
    "change in shareholding",
    "statement of deviation",
    "deviation and variation",
    "unitholding pattern",
    "business responsibility",
    "business responsibility and sustainability",
    "annual report only",
    "certificate regarding",
    "encumbrance certificate",
]


def _safe_text(val) -> str:
    """Safely convert to string."""
    if val is None:
        return ""
    return str(val).strip()


def is_spam(announcement: dict) -> bool:
    """
    Check if announcement is SPAM.
    
    Very strict: only removes known spam keywords.
    Everything else passes through.
    """
    subject = _safe_text(announcement.get("subject", "")).lower()
    company = _safe_text(announcement.get("company", "")).lower()

    # Empty subject = spam
    if not subject or subject in ("n/a", "na", "-", ""):
        return True

    # Check spam keywords
    for keyword in SPAM_KEYWORDS:
        if keyword.lower() in subject or keyword.lower() in company:
            return True

    return False


def process_announcements(announcements: list) -> list:
    """
    Filter announcements:
      1. Remove SPAM (known irrelevant keywords)
      2. Remove DUPLICATES
      3. Keep EVERYTHING else
    """
    filtered = []
    seen = set()

    for ann in announcements:
        # 1. Skip if SPAM
        if is_spam(ann):
            continue

        # 2. Skip if DUPLICATE
        key = (
            ann.get("date", ""),
            ann.get("company", "").upper(),
            ann.get("subject", "")[:50].upper(),
        )
        if key in seen:
            continue

        seen.add(key)
        filtered.append(ann)

    logger.info(f"Filters: {len(announcements)} in → {len(filtered)} out (removed {len(announcements) - len(filtered)} spam/duplicates)")
    return filtered
