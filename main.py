"""
main.py — Stock Market Analyst Agent
Fetches NSE Corporate Announcements + Runs PEAD Sentiment Analysis
"""

import logging
import sys
from datetime import datetime

# ─────────────────────────────────────────────────────────────
# Logging Setup
# ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("agent.log", encoding="utf-8"),
    ]
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Imports
# ─────────────────────────────────────────────────────────────
try:
    from announcements.watcher_nse import get_nse_announcements
except ImportError as e:
    logger.error(f"❌ Could not import watcher_nse: {e}")
    sys.exit(1)

try:
    from analysis.pead_analyzer import process_analysis
except ImportError as e:
    logger.error(f"❌ Could not import pead_analyzer: {e}")
    sys.exit(1)


# ─────────────────────────────────────────────────────────────
# Display Helpers
# ─────────────────────────────────────────────────────────────

def print_separator(char="=", width=70):
    print(char * width)


def print_header(title: str, width=70):
    print_separator("=", width)
    print(f"{title:^{width}}")
    print_separator("=", width)


def print_summary(data: list):
    """Print a quick summary of analysis results."""
    bullish  = [d for d in data if "BULLISH"  in d.get("signal", "")]
    bearish  = [d for d in data if "BEARISH"  in d.get("signal", "")]
    neutral  = [d for d in data if "NEUTRAL"  in d.get("signal", "")]
    high_imp = [d for d in data if d.get("impact") == "HIGH"]

    print("\n📊 SUMMARY")
    print_separator("-", 40)
    print(f"  📦 Total Announcements : {len(data)}")
    print(f"  🚀 Bullish             : {len(bullish)}")
    print(f"  🔻 Bearish             : {len(bearish)}")
    print(f"  ⚪ Neutral             : {len(neutral)}")
    print(f"  🔥 High Impact         : {len(high_imp)}")
    print_separator("-", 40)


def print_announcements(data: list):
    """Print each announcement with analysis."""
    if not data:
        print("\n⚠️  No announcements to display.")
        return

    for idx, ann in enumerate(data, 1):
        signal  = ann.get("signal", "⚪ NEUTRAL")
        impact  = ann.get("impact", "LOW")
        company = ann.get("company", "N/A")
        symbol  = ann.get("symbol", "N/A")
        subject = ann.get("subject", "N/A")
        date    = ann.get("date", "N/A")
        pdf_url = ann.get("pdf_url", "")
        source  = ann.get("source", "NSE")

        # Impact badge
        impact_badge = {
            "HIGH":   "🔥 HIGH",
            "MEDIUM": "🟡 MEDIUM",
            "LOW":    "🟢 LOW",
        }.get(impact, "⚪ UNKNOWN")

        print(f"\n{'─' * 70}")
        print(f"  #{idx}  |  {signal}  |  Impact: {impact_badge}  |  Source: {source}")
        print(f"{'─' * 70}")
        print(f"  📅 Date    : {date}")
        print(f"  🏢 Company : {company}")
        print(f"  🔖 Symbol  : {symbol}")
        print(f"  📝 Subject : {subject}")
        if pdf_url:
            print(f"  📄 PDF     : {pdf_url}")


def print_high_impact_only(data: list):
    """Print only HIGH impact announcements separately."""
    high_impact = [d for d in data if d.get("impact") == "HIGH"]

    if not high_impact:
        print("\n  ℹ️  No HIGH impact announcements found today.")
        return

    print(f"\n🔥 HIGH IMPACT ANNOUNCEMENTS ({len(high_impact)} found)")
    print_separator("-", 70)

    for ann in high_impact:
        print(f"\n  🏢 {ann.get('company', 'N/A')} ({ann.get('symbol', 'N/A')})")
        print(f"  📝 {ann.get('subject', 'N/A')}")
        print(f"  📅 {ann.get('date', 'N/A')}  |  {ann.get('signal', 'N/A')}")


# ─────────────────────────────────────────────────────────────
# MAIN FUNCTION
# ─────────────────────────────────────────────────────────────

def main():
    now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    print("\n")
    print_header("🚀 STOCK MARKET ANALYST AGENT")
    print(f"  ⏰ Run Time  : {now}")
    print(f"  📡 Exchange  : NSE (National Stock Exchange of India)")
    print(f"  🧠 Analysis  : PEAD Sentiment Engine")
    print_separator("=", 70)

    # ── STEP 1: Fetch Announcements ──────────────────────────
    print("\n📡 STEP 1: Fetching NSE Corporate Announcements...\n")

    try:
        raw_data = get_nse_announcements()
    except Exception as e:
        logger.error(f"❌ Fetch failed: {e}")
        print(f"\n❌ ERROR: Could not fetch announcements.\n   Reason: {e}")
        sys.exit(1)

    if not raw_data:
        print("⚠️  No announcements fetched. Please check your internet connection or try again later.")
        sys.exit(0)

    print(f"✅ Fetched {len(raw_data)} announcements from NSE.")

    # ── STEP 2: PEAD Sentiment Analysis ─────────────────────
    print("\n🧠 STEP 2: Running PEAD Sentiment Analysis...\n")

    try:
        analyzed_data = process_analysis(raw_data)
    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}")
        print(f"\n❌ ERROR: Analysis failed.\n   Reason: {e}")
        sys.exit(1)

    print(f"✅ Analysis complete for {len(analyzed_data)} announcements.")

    # ── STEP 3: Display Results ──────────────────────────────
    print("\n")
    print_header("📊 MARKET IMPACT REPORT")

    # Summary first
    print_summary(analyzed_data)

    # High Impact Highlights
    print_high_impact_only(analyzed_data)

    # All Announcements
    print("\n")
    print_header("📋 ALL ANNOUNCEMENTS (Detailed)")
    print_announcements(analyzed_data)

    # ── Footer ───────────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print(f"  ✅ DONE — {len(analyzed_data)} announcements processed at {now}")
    print(f"  📝 Logs saved to: agent.log")
    print_separator("=", 70)
    print()


# ─────────────────────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    main()
