# announcements/filters.py
import hashlib
from typing import Dict, List

# --- Expanded Keyword Filters ---
RESULT_KEYWORDS = [
    # Financial Results
    "financial results",
    "quarterly results",
    "q1 results",
    "q2 results",
    "q3 results",
    "q4 results",
    "fy results",
    "outcome of board meeting",
    "standalone results",
    "consolidated results",
    
    # Documents & Filings
    "investor presentation",
    "press release",
    "unaudited financial results",
    "audited financial results",
    "annual results",
    "half yearly results",
    
    # Financial Metrics
    "earnings",
    "profit & loss",
    "balance sheet",
    "cash flow",
    "cash flow statement",
    
    # Corporate Actions
    "dividend",
    "dividend declaration",
    "interim dividend",
    "final dividend",
    "buyback",
    "share buyback",
    "bonus",
    "bonus issue",
    "rights issue",
    "stock split",
    "board meeting",
    "shareholder approval",
]

def is_result_announcement(subject: str) -> bool:
    """Check if announcement is a financial result filing."""
    subject_lower = subject.lower()
    return any(keyword in subject_lower for keyword in RESULT_KEYWORDS)

# --- Duplicate Detection ---
seen_hashes = set()

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
