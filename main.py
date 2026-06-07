import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

# Priority 1 (Main Focus): Results
# Priority 2 (Secondary): Other key announcements
PRIORITY_KEYWORDS = [
    "Financial Results",        # ⭐ MAIN FOCUS
    "Quarterly Results",        # ⭐ MAIN FOCUS
    "Annual Results",           # ⭐ MAIN FOCUS
    "Unaudited Results",        # ⭐ MAIN FOCUS
    "Audited Results",          # ⭐ MAIN FOCUS
]

SECONDARY_KEYWORDS = [
    "Dividend",                 # Dividend announcements
    "Board Meeting",            # Board meeting updates
    "Bonus Issue",              # Bonus shares
    "Rights Issue",             # Rights issue
    "Merger",                   # Merger & Acquisition
    "Acquisition",              # Company buyouts
    "Buyback",                  # Share buyback
    "Stock Split",              # Stock split
    "AGM",                      # Annual General Meeting
    "EGM",                      # Extraordinary General Meeting
]

DAYS_TO_CHECK = 7  # Last 7 days ka data

# ─────────────────────────────────────────────
# BSE ANNOUNCEMENT FETCHER
# ─────────────────────────────────────────────

def fetch_bse_announcements():
    """BSE se announcements fetch karta hai"""

    url = "https://www.bseindia.com/corporates/ann.html"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.bseindia.com/"
    }

    print("\n" + "="*60)
    print("   BSE PEAD EARNINGS AGENT - ANNOUNCEMENT TRACKER")
    print("="*60)
    print(f"   Checking last {DAYS_TO_CHECK} days of announcements...")
    print("="*60 + "\n")

    try:
        print("🔄 Step 1: Connecting to BSE...")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        print("✅ Connected to BSE Successfully!\n")

    except requests.exceptions.ConnectionError:
        print("❌ Error: Internet connection failed. Please check your network.")
        return
    except requests.exceptions.Timeout:
        print("❌ Error: BSE server timeout. Try again later.")
        return
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
        return

    # ─────────────────────────────────────────
    # PARSE HTML
    # ─────────────────────────────────────────
    print("🔄 Step 2: Parsing BSE data...")
    soup = BeautifulSoup(response.text, "html.parser")

    cutoff_date = datetime.now() - timedelta(days=DAYS_TO_CHECK)

    priority_results = []    # Results (Main Focus)
    secondary_results = []   # Other Announcements

    rows = soup.find_all("tr")

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 3:
            continue

        try:
            date_text = cols[0].get_text(strip=True)
            company   = cols[1].get_text(strip=True)
            subject   = cols[2].get_text(strip=True)

            # Date filter
            try:
                ann_date = datetime.strptime(date_text, "%d-%m-%Y")
            except ValueError:
                try:
                    ann_date = datetime.strptime(date_text, "%d/%m/%Y")
                except ValueError:
                    continue

            if ann_date < cutoff_date:
                continue

            # Keyword matching
            matched_priority  = any(kw.lower() in subject.lower() for kw in PRIORITY_KEYWORDS)
            matched_secondary = any(kw.lower() in subject.lower() for kw in SECONDARY_KEYWORDS)

            entry = {
                "date"   : date_text,
                "company": company,
                "subject": subject
            }

            if matched_priority:
                priority_results.append(entry)
            elif matched_secondary:
                secondary_results.append(entry)

        except Exception:
            continue

    # ─────────────────────────────────────────
    # DISPLAY RESULTS
    # ─────────────────────────────────────────
    print(f"✅ Parsing complete!\n")

    # ── Priority: Results ──
    print("="*60)
    print(f"  ⭐ FINANCIAL RESULTS (Main Focus) — {len(priority_results)} Found")
    print("="*60)

    if priority_results:
        for i, ann in enumerate(priority_results, 1):
            print(f"\n  [{i}] 📅 Date    : {ann['date']}")
            print(f"       🏢 Company : {ann['company']}")
            print(f"       📋 Subject : {ann['subject']}")
    else:
        print("  ⚠️  No Financial Results found in last 7 days.")

    # ── Secondary: Other Announcements ──
    print("\n" + "="*60)
    print(f"  📢 OTHER KEY ANNOUNCEMENTS — {len(secondary_results)} Found")
    print("="*60)

    if secondary_results:
        for i, ann in enumerate(secondary_results, 1):
            print(f"\n  [{i}] 📅 Date    : {ann['date']}")
            print(f"       🏢 Company : {ann['company']}")
            print(f"       📋 Subject : {ann['subject']}")
    else:
        print("  ⚠️  No other key announcements found in last 7 days.")

    # ── Summary ──
    total = len(priority_results) + len(secondary_results)
    print("\n" + "="*60)
    print(f"  ✅ SUMMARY")
    print("="*60)
    print(f"  • Financial Results  : {len(priority_results)}")
    print(f"  • Other Announcements: {len(secondary_results)}")
    print(f"  • Total Found        : {total}")
    print("="*60 + "\n")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    fetch_bse_announcements()
