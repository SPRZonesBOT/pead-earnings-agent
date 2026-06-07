"""
main.py — Stock Market Analyst Agent (Full)
Pipeline:
  NSE Announcements → Sentiment → Live Price → PEAD Drift → Confirmation Score → Telegram
"""

import logging
import sys
import os
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

try:
    from notifications.telegram_alert import TelegramAlert
    TELEGRAM_AVAILABLE = True
except ImportError:
    logger.warning("⚠️  telegram_alert module not found. Alerts disabled.")
    TelegramAlert = None
    TELEGRAM_AVAILABLE = False


# ─────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID_HERE")

TELEGRAM_SEND_STRONG_CONFIRMED   = True
TELEGRAM_SEND_MODERATE_CONFIRMED = False
TELEGRAM_SEND_WATCHLIST          = False

SHOW_ALL_ANNOUNCEMENTS = True
SHOW_SUBSCORES         = True


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def clamp(value, low=0, high=100):
    if not isinstance(value, (int, float)):
        return 0
    return max(low, min(high, int(value)))


def print_separator(char="=", width=90):
    print(char * width)


def print_header(title: str, width=90):
    print_separator("=", width)
    print(f"{title:^{width}}")
    print_separator("=", width)


# ─────────────────────────────────────────────────────────────
# Summary Printer
# ─────────────────────────────────────────────────────────────

def print_summary(data: list):
    total      = len(data)
    bullish    = [d for d in data if "BULLISH" in d.get("signal", "")]
    bearish    = [d for d in data if "BEARISH" in d.get("signal", "")]
    neutral    = [d for d in data if "NEUTRAL" in d.get("signal", "")]
    high_imp   = [d for d in data if d.get("impact") == "HIGH"]
    medium_imp = [d for d in data if d.get("impact") == "MEDIUM"]
    strong_c   = [d for d in data if d.get("confirmation_tier") == "🔥 STRONG CONFIRMED"]
    moderate_c = [d for d in data if d.get("confirmation_tier") == "✅ MODERATELY CONFIRMED"]
    watchlist  = [d for d in data if d.get("confirmation_tier") == "👀 WATCHLIST"]
    no_action  = [d for d in data if d.get("confirmation_tier") == "⛔ NO ACTION"]

    telegram_bound = strong_c + (moderate_c if TELEGRAM_SEND_MODERATE_CONFIRMED else [])

    print("\n📊 FINAL SUMMARY")
    print_separator("-", 56)
    print(f"  📦 Total Announcements        : {total}")
    print(f"  🚀 Bullish                    : {len(bullish)}")
    print(f"  🔻 Bearish                    : {len(bearish)}")
    print(f"  ⚪ Neutral                    : {len(neutral)}")
    print(f"  🔥 High Impact                : {len(high_imp)}")
    print(f"  🟡 Medium Impact              : {len(medium_imp)}")
    print(f"  {'─' * 49}")
    print(f"  🔥 STRONG CONFIRMED           : {len(strong_c)}")
    print(f"  ✅ MODERATELY CONFIRMED       : {len(moderate_c)}")
    print(f"  👀 WATCHLIST                  : {len(watchlist)}")
    print(f"  ⛔ NO ACTION                  : {len(no_action)}")
    print(f"  {'─' * 49}")
    print(f"  📱 Telegram Bound             : {len(telegram_bound)}")
    print_separator("-", 56)


# ─────────────────────────────────────────────────────────────
# Announcement Detail Printer
# ─────────────────────────────────────────────────────────────

def print_announcement_detail(ann: dict, idx: int):
    signal        = ann.get("signal", "⚪ NEUTRAL")
    impact        = ann.get("impact", "LOW")
    company       = ann.get("company", "N/A")
    symbol        = ann.get("symbol", "N/A")
    subject       = ann.get("subject", "N/A")
    date          = ann.get("date", "N/A")

    live_price    = ann.get("live_price", {}) or {}
    pead_signal   = ann.get("pead_signal", "⚪ N/A")
    drift_score   = ann.get("drift_score", {}) or {}

    confirm_tier  = ann.get("confirmation_tier", "⛔ NO ACTION")
    confirm_score = ann.get("confirmation_score", 0)
    confirmation  = ann.get("confirmation", {}) or {}
    sub_scores    = confirmation.get("sub_scores", {}) or {}

    impact_colors = {"HIGH": "🔥 HIGH", "MEDIUM": "🟡 MEDIUM", "LOW": "🟢 LOW"}
    impact_badge  = impact_colors.get(impact, "⚪ UNKNOWN")

    pead_conf      = drift_score.get("confidence", "LOW")
    pead_conf_icon = {"HIGH": "🔥", "MEDIUM": "🟡", "LOW": "⚪"}.get(pead_conf, "⚪")

    print(f"\n{'─' * 90}")
    print(f"  #{idx:3d} | {signal:20s} | Impact: {impact_badge:12s} | {confirm_tier}")
    print(f"  {'─' * 86}")
    print(f"  🧠 PEAD    : {pead_signal}")
    print(f"  ✅ Confirm : {confirm_tier:35s} | Score: {confirm_score:3.1f}/100")
    print(f"  {'─' * 86}")
    print(f"  📅 Date    : {date}")
    print(f"  🏢 Company : {company}")
    print(f"  🔤 Symbol  : {symbol}")
    print(f"  📝 Subject : {subject[:120]}")

    # ── Live Price Block ─────────────────────────────────────
    if live_price.get("price") is not None:
        price  = live_price.get("price", 0)
        change = live_price.get("change_pct", 0)
        trend  = live_price.get("trend", "N/A")
        volume = live_price.get("volume", 0)
        avol   = live_price.get("avg_volume_20d", 0)
        vsurge = live_price.get("volume_surge_pct", 0)
        dr     = live_price.get("drift", "N/A")

        print(f"\n  💹 LIVE MARKET DATA")
        print(f"     Price       : ₹{price:>10,.2f}")
        print(f"     Change      : {change:>+8.2f}%  |  {trend}")
        print(f"     Volume      : {volume:>12,}  |  Avg(20d): {avol:>12,}")
        print(f"     Vol Surge   : {vsurge:>+7.1f}%")
        print(f"     Drift       : {dr}")
    else:
        print(f"\n  💹 Live Price : ❌ Not Available")

    # ── PEAD Detail ──────────────────────────────────────────
    if drift_score:
        print(f"\n  🧠 PEAD DETAIL")
        print(f"     Drift Score     : {drift_score.get('raw_score', 'N/A')}")
        print(f"     Confidence      : {pead_conf_icon} {pead_conf}")
        print(f"     Sentiment Score : {drift_score.get('sentiment_score', 'N/A')}")
        print(f"     Price Change %  : {drift_score.get('price_change_pct', 0):+.2f}%")

    # ── Sub-Scores Block ─────────────────────────────────────
    if sub_scores and SHOW_SUBSCORES:
        print(f"\n  📌 CONFIRMATION SUB-SCORES")
        score_keys = [
            ("sentiment",   "Sentiment"),
            ("price_action","Price Action"),
            ("volume",      "Volume"),
            ("market",      "Market Context"),
            ("fundamentals","Fundamentals"),
            ("news_quality","News Quality"),
        ]
        for key, label in score_keys:
            ss     = sub_scores.get(key, {}) or {}
            s_val  = ss.get("score", "N/A")
            s_note = ss.get("note", "")
            bar    = "█" * (clamp(s_val, 0, 100) // 5) if isinstance(s_val, (int, float)) else ""
            print(f"     {label:15s} : {str(s_val):>3s}/100  {bar}")
            if s_note:
                print(f"                   ({s_note[:80]})")

    # ── Reasons / Penalties ──────────────────────────────────
    reasons = confirmation.get("reasons", [])
    if reasons:
        print(f"\n  📋 REASONS")
        for r in reasons:
            print(f"     • {r}")

    # ── PDF Link ─────────────────────────────────────────────
    pdf_url = ann.get("pdf_url", "")
    if pdf_url:
        print(f"\n  📄 PDF : {pdf_url}")

    # ── Matched Keywords ─────────────────────────────────────
    keywords = ann.get("matched_keywords", [])
    if keywords:
        kw_display = ", ".join(keywords[:8])
        print(f"\n  🔑 Keywords : {kw_display}")
        if len(keywords) > 8:
            print(f"               ... and {len(keywords) - 8} more")


# ─────────────────────────────────────────────────────────────
# Confirmed Picks Printer
# ─────────────────────────────────────────────────────────────

def print_confirmed_picks(data: list):
    strong   = sorted(
        [d for d in data if d.get("confirmation_tier") == "🔥 STRONG CONFIRMED"],
        key=lambda x: x.get("confirmation_score", 0), reverse=True
    )
    moderate = sorted(
        [d for d in data if d.get("confirmation_tier") == "✅ MODERATELY CONFIRMED"],
        key=lambda x: x.get("confirmation_score", 0), reverse=True
    )
    watch    = sorted(
        [d for d in data if d.get("confirmation_tier") == "👀 WATCHLIST"],
        key=lambda x: x.get("confirmation_score", 0), reverse=True
    )

    def print_tier_table(picks, heading):
        if not picks:
            return
        print(f"\n{heading} ({len(picks)})")
        print_separator("-", 90)
        print(f"  {'Symbol':<12s}  {'Price':>10s}  {'Change':>8s}  {'Score':>6s}  {'Signal':<25s}")
        print_separator("-", 90)
        for ann in picks:
            pd_    = ann.get("live_price", {}) or {}
            price  = pd_.get("price", 0) or 0
            change = pd_.get("change_pct", 0) or 0
            signal = ann.get("signal", "N/A")
            score  = ann.get("confirmation_score", 0)
            print(
                f"  {ann.get('symbol','N/A'):<12s}  "
                f"₹{price:>8.2f}  "
                f"{change:>+7.2f}%  "
                f"{score:>5.1f}  "
                f"{signal:<25s}"
            )
        print()

    print_tier_table(strong,   "🔥 STRONG CONFIRMED PICKS")
    print_tier_table(moderate, "✅ MODERATELY CONFIRMED PICKS")

    # Watchlist — top 10 only
    if watch:
        print(f"\n👀 WATCHLIST TOP 10")
        print_separator("-", 90)
        print(f"  {'Symbol':<12s}  {'Price':>10s}  {'Change':>8s}  {'Score':>6s}  {'Signal':<25s}")
        print_separator("-", 90)
        for ann in watch[:10]:
            pd_    = ann.get("live_price", {}) or {}
            price  = pd_.get("price", 0) or 0
            change = pd_.get("change_pct", 0) or 0
            signal = ann.get("signal", "N/A")
            score  = ann.get("confirmation_score", 0)
            print(
                f"  {ann.get('symbol','N/A'):<12s}  "
                f"₹{price:>8.2f}  "
                f"{change:>+7.2f}%  "
                f"{score:>5.1f}  "
                f"{signal:<25s}"
            )
        if len(watch) > 10:
            print(f"  ... and {len(watch) - 10} more")
        print()


# ─────────────────────────────────────────────────────────────
# Telegram Alert Sender
# ─────────────────────────────────────────────────────────────

def send_telegram_alerts(telegram, analyzed_data: list):
    if not telegram or not getattr(telegram, "enabled", False):
        logger.info("ℹ️  Telegram disabled — skipping alerts.")
        return

    telegram_picks = []
    for ann in analyzed_data:
        tier = ann.get("confirmation_tier", "")
        if tier == "🔥 STRONG CONFIRMED" and TELEGRAM_SEND_STRONG_CONFIRMED:
            telegram_picks.append(ann)
        elif tier == "✅ MODERATELY CONFIRMED" and TELEGRAM_SEND_MODERATE_CONFIRMED:
            telegram_picks.append(ann)

    if not telegram_picks:
        logger.info("ℹ️  No Telegram-bound picks found.")
        try:
            telegram.send_daily_summary(analyzed_data)
            print("  📊 Daily summary sent!")
        except Exception as e:
            logger.warning(f"Daily summary send failed: {e}")
        return

    sent_count = 0
    for pick in telegram_picks:
        try:
            success = telegram.send_pead_alert(pick)
            if success:
                sent_count += 1
                print(
                    f"  📱 Alert sent   : {pick.get('symbol','?')} — "
                    f"{pick.get('confirmation_tier','?')} "
                    f"({pick.get('confirmation_score', 0)}/100)"
                )
            else:
                print(f"  ❌ Alert failed : {pick.get('symbol','?')}")
        except Exception as e:
            logger.warning(f"Alert send error for {pick.get('symbol','?')}: {e}")

    try:
        telegram.send_daily_summary(analyzed_data)
        print("  📊 Daily summary sent!")
    except Exception as e:
        logger.warning(f"Daily summary send failed: {e}")

    logger.info(f"✅ Telegram: {sent_count}/{len(telegram_picks)} alerts sent.")


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def main():
    now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    print("\n")
    print_header("🚀 STOCK MARKET ANALYST AGENT — FULL PIPELINE")
    print(f"  ⏰ Run Time      : {now}")
    print(f"  📡 Exchange      : NSE")
    print(f"  🧠 Engine        : Sentiment + Live Price + PEAD Drift + Confirmation Score")
    print(f"  📱 Telegram      : {'✅ Active' if TELEGRAM_AVAILABLE else '❌ Module Missing'}")
    print_separator("=", 90)

    # ── Initialize Telegram ──────────────────────────────────
    telegram = None
    if TELEGRAM_AVAILABLE and TelegramAlert:
        try:
            telegram = TelegramAlert(
                bot_token=TELEGRAM_BOT_TOKEN,
                chat_id=TELEGRAM_CHAT_ID,
            )
            if getattr(telegram, "enabled", False):
                print("✅ Telegram Bot: Connected & Ready 📱")
            else:
                print("⚠️  Telegram Bot: Not configured.")
        except Exception as e:
            logger.warning(f"Telegram init failed: {e}")
            print(f"⚠️  Telegram init error: {e}")
    else:
        print("⚠️  Telegram Bot: Module not loaded.")

    # ── Step 1: Fetch Announcements ──────────────────────────
    print("\n📡 STEP 1: Fetching NSE Announcements...\n")
    try:
        raw_data = get_nse_announcements()
    except Exception as e:
        logger.error(f"❌ Fetch failed: {e}")
        print(f"\n❌ ERROR: Could not fetch announcements.\n   Reason: {e}")
        sys.exit(1)

    if not raw_data:
        print("⚠️  No announcements fetched. Check internet connection.")
        sys.exit(0)

    print(f"✅ Fetched {len(raw_data)} announcements from NSE.\n")

    # ── Step 2: Full Analysis ────────────────────────────────
    print("🧠 STEP 2: Running Analysis Pipeline...\n")
    try:
        analyzed_data = process_analysis(raw_data)
    except Exception as e:
        logger.error(f"❌ Analysis pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        print(f"\n❌ ERROR: Analysis failed.\n   Reason: {e}")
        sys.exit(1)

    print(f"\n✅ Analysis complete for {len(analyzed_data)} announcements.\n")

    # ── Step 3: Telegram Alerts ──────────────────────────────
    print("📱 STEP 3: Sending Telegram Alerts...\n")
    send_telegram_alerts(telegram, analyzed_data)

    # ── Step 4: Display Results ──────────────────────────────
    print_header("📊 FINAL REPORT — CONFIRMATION SCORE ANALYSIS")

    # Summary table
    print_summary(analyzed_data)

    # Tier-wise compact tables
    print_confirmed_picks(analyzed_data)

    # Full detail for all announcements
    if SHOW_ALL_ANNOUNCEMENTS:
        print_separator("=", 90)
        print(f"{'📋 ALL ANNOUNCEMENTS — FULL DETAILS':^90}")
        print_separator("=", 90)
        for idx, ann in enumerate(analyzed_data, 1):
            print_announcement_detail(ann, idx)

    # ── Footer Stats ─────────────────────────────────────────
    total_strong   = len([d for d in analyzed_data if d.get("confirmation_tier") == "🔥 STRONG CONFIRMED"])
    total_moderate = len([d for d in analyzed_data if d.get("confirmation_tier") == "✅ MODERATELY CONFIRMED"])
    total_watch    = len([d for d in analyzed_data if d.get("confirmation_tier") == "👀 WATCHLIST"])
    total_noaction = len([d for d in analyzed_data if d.get("confirmation_tier") == "⛔ NO ACTION"])

    print_separator("=", 90)
    print(f"{'📊 SESSION STATS':^90}")
    print_separator("-", 90)
    print(f"  🔥 Strong Confirmed      : {total_strong}")
    print(f"  ✅ Moderately Confirmed  : {total_moderate}")
    print(f"  👀 Watchlist             : {total_watch}")
    print(f"  ⛔ No Action             : {total_noaction}")
    print(f"  📦 Total Processed       : {len(analyzed_data)}")
    print_separator("=", 90)
    print(f"  ⏰ Completed At          : {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")
    print(f"  📁 Logs saved to         : agent.log")
    print_separator("=", 90)


# ─────────────────────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    main()
