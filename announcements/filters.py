import hashlib
from typing import Dict, List

# --- Keyword Filters ---
RESULT_KEYWORDS = [
    "financial results",
    "quarterly results",
    "outcome of board meeting",
    "standalone results",
    "consolidated results",
    "investor presentation",
    "press release",
    "unaudited financial results",
    "audited financial results",
    "earnings",
    "profit & loss",
    "balance sheet",
    "cash flow statement",
    "dividend declaration",
    "buyback",
    "bonus issue",
    "rights issue",
]

def is_result_announcement(subject: str) -> bool:
    """Check if announcement is a financial result filing."""
    subject_lower = subject.lower()
    return any(keyword in subject_lower for keyword in RESULT_KEYWORDS)

# --- Duplicate Detection ---
seen_hashes = set()  # In-memory cache (replace with Redis later)

def get_hash(company: str, subject: str, date: str) -> str:
    """Generate unique hash for an announcement."""
    raw = f"{company}|{subject}|{date}"
    return hashlib.md5(raw.encode()).hexdigest()

def is_duplicate(company: str, subject: str, date: str) -> bool:
    """Check if announcement is already processed."""
    h = get_hash(company, subject, date)
    if h in seen_hashes:
        return True
    seen_hashes.add(h)
    return False

# --- Announcement Processor ---
def process_announcements(raw_announcements: List[Dict]) -> List[Dict]:
    """Filter and deduplicate announcements."""
    filtered = []
    for item in raw_announcements:
        if is_result_announcement(item["subject"]):
            if not is_duplicate(item["company"], item["subject"], item["date"]):
                filtered.append(item)
    return filtered
