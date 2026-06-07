import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# ============================================================
# CONFIG
# ============================================================

BSE_ANNOUNCEMENTS_URL = "https://www.bseindia.com/corporates/ann.html"

PAST_DAYS = 7
FUTURE_DAYS = 7
LOOKBACK_NOTICE_DAYS = 45
REQUEST_TIMEOUT = 20

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.bseindia.com/"
}

# Main focus: result-related subjects
RESULT_KEYWORDS = [
    "financial results",
    "quarterly results",
    "annual results",
    "audited results",
    "unaudited results",
    "results",
    "earnings",
    "standalone results",
    "consolidated results",
    "quarter ended",
    "year ended",
]

# Strict result phrases for better filtering
STRICT_RESULT_KEYWORDS = [
    "financial results",
    "quarterly results",
    "annual results",
    "audited financial results",
    "unaudited financial results",
    "standalone financial results",
    "consolidated financial results",
    "quarter ended",
    "year ended",
]

# Secondary announcements
SECONDARY_KEYWORDS = [
    "dividend",
    "board meeting",
    "bonus",
    "stock split",
    "split",
    "buyback",
    "rights issue",
    "merger",
    "acquisition",
    "agm",
    "egm",
    "fund raising",
    "preferential issue"
]

# Result-related meeting/intimation keywords
MEETING_KEYWORDS = [
    "board meeting",
    "meeting of board",
    "board of directors meeting",
    "intimation of board meeting",
    "notice of board meeting",
    "board to consider",
    "meeting scheduled"
]

# Important companies ko priority dene ke liye
FOCUS_COMPANIES = [
    "RELIANCE",
    "TCS",
    "INFOSYS",
    "HDFCBANK",
    "ICICIBANK",
    "SBIN",
    "LT",
    "ITC",
    "BHARTI",
    "AXISBANK",
    "KOTAKBANK",
    "MARUTI",
    "SUNPHARMA",
    "M&M",
    "ULTRACEMCO",
    "HCLTECH",
    "WIPRO",
    "TITAN",
    "BAJFINANCE",
    "NTPC",
    "POWERGRID",
    "ONGC",
    "COALINDIA",
    "ASIANPAINT",
    "HINDUNILVR"
]


# ============================================================
# HELPERS
# ============================================================

def clean_text(text):
    return re.sub(r"\s+", " ", text or "").strip()


def contains_any(text, keywords):
    text = (text or "").lower()
    return any(keyword.lower() in text for keyword in keywords)


def is_focus_company(company):
    company_upper = (company or "").upper()
    return any(name in company_upper for name in FOCUS_COMPANIES)


def is_strict_result_subject(subject):
    subject_lower = (subject or "").lower()
    return contains_any(subject_lower, STRICT_RESULT_KEYWORDS)


def is_result_subject(subject):
    subject_lower = (subject or "").lower()
    return contains_any(subject_lower, RESULT_KEYWORDS)


def is_result_meeting_subject(subject):
    """
    Sirf wahi subject True hoga jisme:
    - board meeting/intimation ho
    - aur saath me result-related wording ho
    """
    subject_lower = (subject or "").lower()
    has_meeting = contains_any(subject_lower, MEETING_KEYWORDS)
    has_result = contains_any(subject_lower, RESULT_KEYWORDS)
    return has_meeting and has_result


def parse_date_from_cell(text):
    """
    Table cell se announcement date parse karta hai.
    Common formats handle karta hai.
    """
    text = clean_text(text)

    candidates = []

    numeric_matches = re.findall(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", text)
    candidates.extend(numeric_matches)

    text_matches = re.findall(
        r"\b\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}\b",
        text
    )
    candidates.extend(text_matches)

    month_first_matches = re.findall(
        r"\b[A-Za-z]{3,9}\s+\d{1,2},\s+\d{4}\b",
        text
    )
    candidates.extend(month_first_matches)

    formats = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d/%m/%y",
        "%d-%m-%y",
        "%d %b %Y",
        "%d %B %Y",
        "%b %d, %Y",
        "%B %d, %Y",
    ]

    for candidate in candidates:
        for fmt in formats:
            try:
                return datetime.strptime(candidate, fmt).date()
            except ValueError:
                continue

    return None


def extract_future_dates_from_subject(subject):
    """
    Subject ke andar future meeting/result date nikalne ki koshish karta hai.
    Example:
    - 12/06/2026
    - 12-06-2026
    - 12 June 2026
    - June 12, 2026
    """
    subject = clean_text(subject)
    found_dates = []

    patterns = [
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        r"\b\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}\b",
        r"\b[A-Za-z]{3,9}\s+\d{1,2},\s+\d{4}\b",
    ]

    formats = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d/%m/%y",
        "%d-%m-%y",
        "%d %b %Y",
        "%d %B %Y",
        "%b %d, %Y",
        "%B %d, %Y",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, subject)
        for match in matches:
            for fmt in formats:
                try:
                    parsed = datetime.strptime(match, fmt).date()
                    found_dates.append(parsed)
                    break
                except ValueError:
                    continue

    return sorted(set(found_dates))


def fetch_page(url):
    response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.text


def parse_announcement_rows(html):
    """
    BSE announcement page ke rows parse karta hai.
    Generic parsing rakha gaya hai taaki minor HTML change me bhi kaam kar sake.
    """
    soup = BeautifulSoup(html, "html.parser")
    rows = []

    for tr in soup.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 3:
            continue

        cells = [clean_text(td.get_text(" ", strip=True)) for td in tds]
        if not cells:
            continue

        ann_date = parse_date_from_cell(cells[0])
        if not ann_date:
            continue

        company = cells[1] if len(cells) > 1 else ""
        subject = " | ".join(cells[2:]) if len(cells) > 2 else ""

        company = clean_text(company)
        subject = clean_text(subject)

        if not company or not subject:
            continue

        rows.append({
            "announcement_date": ann_date,
            "company": company,
            "subject": subject
        })

    return rows


def dedupe_items(items, keys):
    seen = set()
    unique = []

    for item in items:
        marker = tuple(item.get(k) for k in keys)
        if marker in seen:
            continue
        seen.add(marker)
        unique.append(item)

    return unique


def classify_announcements(rows):
    today = datetime.now().date()
    recent_cutoff = today - timedelta(days=PAST_DAYS)
    notice_cutoff = today - timedelta(days=LOOKBACK_NOTICE_DAYS)
    future_limit = today + timedelta(days=FUTURE_DAYS)

    recent_results = []
    recent_others = []
    upcoming_result_meetings = []
    todays_pead_alerts = []

    for row in rows:
        ann_date = row["announcement_date"]
        company = row["company"]
        subject = row["subject"]

        is_result = is_result_subject(subject)
        is_strict_result = is_strict_result_subject(subject)
        is_secondary = contains_any(subject, SECONDARY_KEYWORDS)
        is_result_meeting = is_result_meeting_subject(subject)
        focus_flag = is_focus_company(company)

        # --------------------------------------------------------
        # 1) Recent result announcements
        # --------------------------------------------------------
        if recent_cutoff <= ann_date <= today and is_result:
            recent_results.append({
                "announcement_date": ann_date,
                "company": company,
                "subject": subject,
                "focus": focus_flag,
                "strict": is_strict_result
            })

            if ann_date == today:
                todays_pead_alerts.append({
                    "type": "RESULT ANNOUNCED TODAY",
                    "company": company,
                    "date": ann_date,
                    "subject": subject,
                    "focus": focus_flag
                })

        # --------------------------------------------------------
        # 2) Recent other announcements
        # --------------------------------------------------------
        if recent_cutoff <= ann_date <= today and (is_secondary and not is_result):
            recent_others.append({
                "announcement_date": ann_date,
                "company": company,
                "subject": subject,
                "focus": focus_flag
            })

        # --------------------------------------------------------
        # 3) Upcoming result-related board meeting notices
        #    Sirf strict result-meeting subjects hi lenge
        # --------------------------------------------------------
        if notice_cutoff <= ann_date <= today and is_result_meeting:
            candidate_dates = extract_future_dates_from_subject(subject)

            for meeting_date in candidate_dates:
                if today <= meeting_date <= future_limit:
                    item = {
                        "notice_date": ann_date,
                        "meeting_date": meeting_date,
                        "company": company,
                        "subject": subject,
                        "focus": focus_flag
                    }
                    upcoming_result_meetings.append(item)

                    if meeting_date == today:
                        todays_pead_alerts.append({
                            "type": "MEETING / RESULT DAY TODAY",
                            "company": company,
                            "date": meeting_date,
                            "subject": subject,
                            "focus": focus_flag
                        })

    recent_results = dedupe_items(
        recent_results,
        ["announcement_date", "company", "subject"]
    )

    recent_others = dedupe_items(
        recent_others,
        ["announcement_date", "company", "subject"]
    )

    upcoming_result_meetings = dedupe_items(
        upcoming_result_meetings,
        ["meeting_date", "company", "subject"]
    )

    todays_pead_alerts = dedupe_items(
        todays_pead_alerts,
        ["type", "date", "company", "subject"]
    )

    recent_results.sort(
        key=lambda x: (
            not x["focus"],
            not x["strict"],
            -x["announcement_date"].toordinal(),
            x["company"]
        )
    )
    recent_others.sort(
        key=lambda x: (
            not x["focus"],
            -x["announcement_date"].toordinal(),
            x["company"]
        )
    )
    upcoming_result_meetings.sort(
        key=lambda x: (
            not x["focus"],
            x["meeting_date"].toordinal(),
            x["company"]
        )
    )
    todays_pead_alerts.sort(
        key=lambda x: (
            not x["focus"],
            x["date"].toordinal(),
            x["company"]
        )
    )

    return {
        "recent_results": recent_results,
        "recent_others": recent_others,
        "upcoming_result_meetings": upcoming_result_meetings,
        "todays_pead_alerts": todays_pead_alerts
    }


def print_section(title):
    print("\n" + "=" * 90)
    print(title)
    print("=" * 90)


def print_results(data):
    today = datetime.now().date()

    print("\n" + "=" * 90)
    print("AI FIESTA | BSE RESULT + ANNOUNCEMENT + PEAD TRACKER | UPGRADED")
    print("=" * 90)
    print(f"Run Time      : {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")
    print(f"Recent Window : Last {PAST_DAYS} days")
    print(f"Future Window : Next {FUTURE_DAYS} days")
    print("=" * 90)

    # --------------------------------------------------------
    # TODAY ALERTS
    # --------------------------------------------------------
    print_section("TODAY'S PEAD ALERTS")
    if data["todays_pead_alerts"]:
        for idx, item in enumerate(data["todays_pead_alerts"], start=1):
            tag = "IMPORTANT" if item["focus"] else "NORMAL"
            print(f"{idx}. [{tag}] {item['type']}")
            print(f"   Company : {item['company']}")
            print(f"   Date    : {item['date'].strftime('%d-%m-%Y')}")
            print(f"   Subject : {item['subject']}")
            print("-" * 90)
    else:
        print("No PEAD alert for today.")

    # --------------------------------------------------------
    # UPCOMING IMPORTANT RESULT MEETINGS
    # --------------------------------------------------------
    print_section(f"UPCOMING RESULT-RELATED MEETINGS / INTIMATIONS | NEXT {FUTURE_DAYS} DAYS")
    if data["upcoming_result_meetings"]:
        for idx, item in enumerate(data["upcoming_result_meetings"], start=1):
            days_left = (item["meeting_date"] - today).days
            tag = "IMPORTANT" if item["focus"] else "NORMAL"
            print(f"{idx}. [{tag}] {item['company']}")
            print(f"   Meeting Date : {item['meeting_date'].strftime('%d-%m-%Y')}  |  Days Left: {days_left}")
            print(f"   Notice Date  : {item['notice_date'].strftime('%d-%m-%Y')}")
            print(f"   Subject      : {item['subject']}")
            print("-" * 90)
    else:
        print("No upcoming result-related meeting notices found.")

    # --------------------------------------------------------
    # RECENT RESULTS
    # --------------------------------------------------------
    print_section(f"RECENT RESULT ANNOUNCEMENTS | LAST {PAST_DAYS} DAYS")
    if data["recent_results"]:
        for idx, item in enumerate(data["recent_results"], start=1):
            tag = "IMPORTANT" if item["focus"] else "NORMAL"
            strict_tag = "STRICT" if item.get("strict") else "BROAD"
            print(f"{idx}. [{tag}] [{strict_tag}] {item['company']}")
            print(f"   Announcement Date : {item['announcement_date'].strftime('%d-%m-%Y')}")
            print(f"   Subject           : {item['subject']}")
            print("-" * 90)
    else:
        print("No result announcements found in recent window.")

    # --------------------------------------------------------
    # OTHER ANNOUNCEMENTS
    # --------------------------------------------------------
    print_section(f"OTHER IMPORTANT ANNOUNCEMENTS | LAST {PAST_DAYS} DAYS")
    if data["recent_others"]:
        for idx, item in enumerate(data["recent_others"], start=1):
            tag = "IMPORTANT" if item["focus"] else "NORMAL"
            print(f"{idx}. [{tag}] {item['company']}")
            print(f"   Announcement Date : {item['announcement_date'].strftime('%d-%m-%Y')}")
            print(f"   Subject           : {item['subject']}")
            print("-" * 90)
    else:
        print("No other important announcements found in recent window.")

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------
    print_section("SUMMARY")
    print(f"Today's PEAD Alerts               : {len(data['todays_pead_alerts'])}")
    print(f"Upcoming Result Meetings Notices  : {len(data['upcoming_result_meetings'])}")
    print(f"Recent Result Announcements       : {len(data['recent_results'])}")
    print(f"Recent Other Announcements        : {len(data['recent_others'])}")
    print("=" * 90)


def main():
    try:
        print("Connecting to BSE...")
        html = fetch_page(BSE_ANNOUNCEMENTS_URL)

        print("Parsing announcement rows...")
        rows = parse_announcement_rows(html)

        print(f"Rows parsed: {len(rows)}")

        print("Classifying results, meetings, PEAD alerts...")
        data = classify_announcements(rows)

        print_results(data)

    except requests.exceptions.HTTPError as exc:
        print(f"HTTP Error: {exc}")
    except requests.exceptions.ConnectionError:
        print("Connection Error: Internet ya BSE website access issue.")
    except requests.exceptions.Timeout:
        print("Timeout Error: BSE response slow hai, thodi der baad try karo.")
    except Exception as exc:
        print(f"Unexpected Error: {exc}")


if __name__ == "__main__":
    main()
