"""
analysis/pead_analyzer.py — PEAD Analyzer with Live Price Drift Detection
"""

import re
import yfinance as yf
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Sentiment Keywords (Basic)
# ─────────────────────────────────────────────────────────────

BULLISH_KEYWORDS = [
    "dividend", "bonus", "split", "acquisition", "profit increase",
    "growth", "record date", "outcome of board meeting", "order win",
    "expansion", "successful", "positive", "increase in revenue",
    "joint venture", "takeover", "capacity expansion", "buyback",
    "rights issue", "merger", "strong demand", "guidance raised",
]

BEARISH_KEYWORDS = [
    "loss", "resignation", "decrease", "strike", "penalty",
    "fine", "cancellation", "litigation", "investigation", "default",
    "fraud", "withdrawal", "termination", "reduction", "layoff",
    "downgrade", "debt restructuring", "non-payment", "regulatory action",
    "caveat emptor", "suspension", "delisting",
]


# ─────────────────────────────────────────────────────────────
# Sentiment Analyzer
# ─────────────────────────────────────────────────────────────

def analyze_sentiment(subject: str) -> dict:
    """
    Analyze announcement subject text for market sentiment.
    Returns signal, score, and impact level.
    """
    subject_lower = str(subject).lower()
    score = 0

    for word in BULLISH_KEYWORDS:
        if word in subject_lower:
            score += 1

    for word in BEARISH_KEYWORDS:
        if word in subject_lower:
            score -= 1

    if score > 0:
        signal = "🚀 BULLISH"
    elif score < 0:
        signal = "🔻 BEARISH"
    else:
        signal = "⚪ NEUTRAL"

    abs_score = abs(score)
    if abs_score >= 2:
        impact = "HIGH"
    elif abs_score == 1:
        impact = "MEDIUM"
    else:
        impact = "LOW"

    return {
        "signal": signal,
        "score": score,
        "impact": impact,
    }


# ─────────────────────────────────────────────────────────────
# LIVE PRICE DRIFT DETECTION
# ─────────────────────────────────────────────────────────────

def get_live_price(symbol: str) -> dict:
    """
    Fetch live price and percentage change for a stock using yfinance.
    Returns dict with price, change %, trend, and volume.
    """
    try:
        # NSE symbol format for yfinance: SYMBOL.NS
        ticker = yf.Ticker(f"{symbol}.NS")
        data = ticker.history(period="5d")

        if data.empty:
            logger.warning(f"⚠️  No live data found for {symbol}")
            return {
                "price": None,
                "change_pct": None,
                "trend": "❓ No Data",
                "volume": None,
            }

        # Current price & previous close
        current_price = data["Close"].iloc[-1]
        prev_close = data["Close"].iloc[-2] if len(data) > 1 else current_price
        change_pct = ((current_price - prev_close) / prev_close) * 100

        # Volume comparison (today vs avg of last 5 days)
        avg_volume = data["Volume"].mean()
        today_volume = data["Volume"].iloc[-1]
        volume_surge = (today_volume / avg_volume * 100) if avg_volume > 0 else 0

        # Trend classification
        if change_pct > 1.5:
            trend = "🚀 Strong Up"
        elif change_pct > 0.5:
            trend = "📈 Up"
        elif change_pct > -0.5:
            trend = "➖ Flat"
        elif change_pct > -1.5:
            trend = "📉 Down"
        else:
            trend = "🔻 Strong Down"

        # Drift classification (for PEAD)
        if change_pct is not None and abs(change_pct) > 2.0:
            drift = "HIGH"
        elif change_pct is not None and abs(change_pct) > 1.0:
            drift = "MEDIUM"
        else:
            drift = "LOW"

        return {
            "price": round(current_price, 2),
            "change_pct": round(change_pct, 2),
            "trend": trend,
            "volume": int(today_volume),
            "volume_surge_pct": round(volume_surge, 1),
            "drift": drift,
        }

    except Exception as e:
        logger.error(f"❌ yfinance error for {symbol}: {e}")
        return {
            "price": None,
            "change_pct": None,
            "trend": "❌ Error",
            "volume": None,
            "volume_surge_pct": None,
            "drift": "UNKNOWN",
        }


# ─────────────────────────────────────────────────────────────
# Main Processing Pipeline
# ─────────────────────────────────────────────────────────────

def process_analysis(announcements: list) -> list:
    """
    Takes a list of announcements, adds:
      1. Sentiment Analysis
      2. Live Price Data
      3. PEAD Drift Score
    """
    if not announcements:
        return []

    for ann in announcements:
        # Step 1: Sentiment analysis on subject
        analysis = analyze_sentiment(ann.get("subject", ""))
        ann.update(analysis)

        # Step 2: Fetch live price for the symbol
        symbol = ann.get("symbol", "")
        if symbol:
            price_data = get_live_price(symbol)
            ann["live_price"] = price_data

            # Step 3: PEAD Drift Score (combining sentiment + price action)
            # If sentiment is BULLISH and price is UP -> Confirmed PEAD
            # If sentiment is BULLISH but price is DOWN -> Watch/Contrarian
            drift_score = calculate_drift_score(ann)
            ann["drift_score"] = drift_score
            ann["pead_signal"] = drift_score["final_signal"]
        else:
            ann["live_price"] = None
            ann["drift_score"] = None
            ann["pead_signal"] = "⚠️ No Symbol"

    return announcements


def calculate_drift_score(ann: dict) -> dict:
    """
    PEAD Drift Score:
    - Combines keyword sentiment + live price movement
    - Higher confidence if both align
    """
    signal = ann.get("signal", "⚪ NEUTRAL")
    price_data = ann.get("live_price", {})
    change_pct = price_data.get("change_pct", 0)

    score = ann.get("score", 0)  # -N to +N

    # Add price drift factor (scale: -2 to +2)
    if change_pct is not None:
        if change_pct > 2:
            price_factor = 2
        elif change_pct > 1:
            price_factor = 1
        elif change_pct > -1:
            price_factor = 0
        elif change_pct > -2:
            price_factor = -1
        else:
            price_factor = -2
    else:
        price_factor = 0

    total_score = score + price_factor

    # Final PEAD Signal
    if total_score >= 2:
        final_signal = "✅ CONFIRMED BULLISH (PEAD+)" if score > 0 else "🔶 PRICE SURGE (Check News)"
    elif total_score <= -2:
        final_signal = "✅ CONFIRMED BEARISH (PEAD-)" if score < 0 else "🔶 PRICE DROP (Check News)"
    elif total_score > 0:
        final_signal = "🟡 MILD BULLISH"
    elif total_score < 0:
        final_signal = "🟡 MILD BEARISH"
    else:
        final_signal = "⚪ NEUTRAL / NO DRIFT"

    return {
        "sentiment_score": score,
        "price_factor": price_factor,
        "total_score": total_score,
        "final_signal": final_signal,
    }
