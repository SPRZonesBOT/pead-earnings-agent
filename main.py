"""
main.py — Stock Market Analyst Agent
Fetches NSE Announcements → PEAD Sentiment + Live Price Drift
"""

import logging
import sys
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("agent.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Imports
# ─────────────────────────────────────────────────────────────

try:
    from announcements.watcher_nse import get_nse_announcements
except ImportError as e:
    logger.error(f"❌ watcher_nse import failed: {e}")
    sys.exit(1)

try:
    from analysis.pead_analyzer import process_analysis
except ImportError as e:
    logger.error(f"❌ pead_analyzer import failed: {e}")
    sys.exit(1)


# ─────────────────────────────────────────────────────────────
# Display Helpers
# ─────────────────────────────────────────────────────────────

def print_separator(char="=", width=75):
    print(char * width)


def print_header(title: str, width=75):
    print_separator("=", width)
    print(f"{title:^{width}}")
    print_separator("=", width)


def print_summary(data: list):
    bullish  = [d for d in data if "BULLISH" in d.get("signal", "")]
    bearish  = [d for d in data if "BEARISH" in d.get("signal", "")]
    neutral  = [d for d in data if "NEUTRAL" in d.get("signal", "")]
    high_imp = [d for d in data if d.get("impact") == "HIGH"]
    confirmed_pead = [d for d in data if "CONFIRMED" in d.get("pead_signal", "")]

    print("\n📊 SUMMARY")
    print_separator("-", 45)
    print(f"  📦 Total Announcements  : {len(data)}")
    print(f"  🚀 Bullish              : {len(bullish)}")
    print(f"  🔻 Bearish              : {len(bearish)}")
    print(f"  ⚪ Neutral              : {len(neutral)}")
    print(f"  🔥 High Impact          : {len(high_imp)}")
    print(f"  ✅ Confirmed PEAD       : {len(confirmed_pead)}")
    print_separator("-", 45)


def print_announcement(ann: dict, idx: int):
    signal  = ann.get("signal", "⚪ NEUTRAL")
    impact  = ann.get("impact", "LOW")
    company = ann.get("company", "N/A")
    symbol  = ann.get("symbol", "N/A")
    subject = ann.get("subject", "N/A")
    date    = ann.get("date", "N/A")
    pdf_url = ann.get("pdf_url", "")
    source  = ann.get("source", "NSE")

    # Live price block
    price_data = ann.get("live_price", {})
    pead_signal = ann.get("pead_signal", "⚪ N/A")

    impact_badge = {
        "HIGH": "🔥 HIGH", "MEDIUM": "🟡 MEDIUM", "LOW": "🟢 LOW",
    }.get(impact, "⚪ UNKNOWN")

    print(f"\n{'─' * 75}")
    print(f"  #{idx}  |  {signal}  |  Impact: {impact_badge}")
    print(f"  🧠 PEAD: {pead_signal}")
    print(f"{'─' * 75}")
    print(f"  📅 Date    : {date}")
    print(f"  🏢 Company : {company}  ({symbol})")
    print(f"  📝 Subject : {subject}")

    if price_data and price_data.get("price"):
        price  = price_data["price"]
        change = price_data["change_pct"]
        trend  = price_data["trend"]
        volume = price_data.get("volume", "N/A")
        vol_surge = price_data.get("volume_surge_pct", "N/A")
        drift  = price_data.get("drift", "LOW")

        print(f"\n  💹 LIVE PRICE : ₹{price}  |  Change: {change:+.2f}%  |  Trend: {trend}")
        print(f"     📊 Volume   : {volume:,}  |  Vol Surge: {vol_surge}%  |  Drift: {drift}")
    else:
        print(f"\n  💹 Live Price: ❌ Not Available")

    if pdf_url:
        print(f"  📄 PDF      : {pdf_url}")


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def main():
    now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    print("\n")
    print_header("🚀 STOCK MARKET ANALYST AGENT — PEAD + LIVE PRICE")
    print(f"  ⏰ Run Time  : {now}")
    print(f"  📡 Exchange  : NSE (National Stock Exchange of India)")
    print(f"  🧠 Engine    : PEAD Sentiment + yfinance Live Drift")
    print_separator("=", 75)

    # ── Step 1: Fetch ────────────────────────────────────────
    print("\n📡 STEP 1: Fetching NSE Corporate Announcements...\n")

    try:
        raw_data = get_nse_announcements()
    except Exception as e:
        logger.error(f"❌ Fetch failed: {e}")
        print(f"\n❌ ERROR: Could not fetch announcements.\n   Reason: {e}")
        sys.exit(1)

    if not raw_data:
        print("⚠️  No announcements fetched. Internet issue?")
        sys.exit(0)

    print(f"✅ Fetched {len(raw_data)} announcements from NSE.\n")

    # ── Step 2: Analyze with Live Price ────────────────────
    print("🧠 STEP 2: Running PEAD Sentiment + Live Price Analysis...")

    try:
        analyzed_data = process_analysis(raw_data)
    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}")
        print(f"\n❌ ERROR: Analysis failed.\n   Reason: {e}")
        sys.exit(1)

    print(f"✅ Analysis complete for {len(analyzed_data)} announcements.\n")

    # ── Step 3: Display ──────────────────────────────────────
    print_header("📊 PEAD + LIVE PRICE IMPACT REPORT")

    # Summary
    print_summary(analyzed_data)

    # Confirmed PEAD picks
    confirmed = [d for d in analyzed_data if "CONFIRMED" in d.get("pead_signal", "")]
    if confirmed:
        print(f"\n🔥 CONFIRMED PEAD PICKS ({len(confirmed)})")
        print_separator("-", 75)
        for ann in confirmed:
            price_data = ann.get("live_price", {})
            price  = price_data.get("price", "N/A")
            change = price_data.get("change_pct", "N/A")
            print(f"  {ann['symbol']:12s} | ₹{str(price):>8s} | {change:>+6}% | {ann['pead_signal']}")
            print(f"  📝 {ann['subject'][:70]}")
        print()

    # All announcements
    print_separator("-", 75)
    print("📋 ALL ANNOUNCEMENTS (Detailed)")
    print_separator("-", 75)

    for idx, ann in enumerate(analyzed_data, 1):
        print_announcement(ann, idx)

    # ── Footer ───────────────────────────────────────────────
    print(f"\n{'─' * 75}")
    print(f"  ✅ DONE — {len(analyzed_data)} announcements processed at {now}")
    print(f"  📝 Logs: agent.log")
    print_separator("=", 75)
    print()


if __name__ == "__main__":
    main()
