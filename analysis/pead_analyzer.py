"""
analysis/pead_analyzer.py
NSE Announcement Analysis Engine
    1. Sentiment Scoring (keyword + model)
    2. Live Price Fetch (yfinance)
    3. PEAD Drift Score
    4. Multi-factor Confirmation Score (ConfirmationScorer)
"""

import logging
import re
from datetime import datetime, timedelta

import yfinance as yf
import pandas as pd

# Confirmation Scoring Module
from analysis.confirmation_scorer import compute_confirmation_score

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Sentiment Keywords
# ─────────────────────────────────────────────────────────────

BULLISH_KEYWORDS = {
    "buyback": 6,
    "bonus": 5,
    "dividend declared": 6,
    "interim dividend": 6,
    "final dividend": 5,
    "stock split": 5,
    "order win": 7,
    "order received": 7,
    "new order": 6,
    "contract": 5,
    "acquisition": 5,
    "merger": 5,
    "partnership": 4,
    "joint venture": 4,
    "expansion": 5,
    "capacity expansion": 6,
    "strategic partnership": 4,
    "approval": 3,
    "regulatory approval": 5,
    "results": 3,
    "quarterly results": 4,
    "earnings": 5,
    "profit increase": 6,
    "revenue growth": 5,
    "EBITDA improvement": 6,
    "margin improvement": 6,
    "guidance raised": 7,
    "shareholder approval": 3,
    "positive update": 4,
    "board meeting outcome": 2,
}

BEARISH_KEYWORDS = {
    "default": -7,
    "fraud": -7,
    "investigation": -6,
    "penalty": -5,
    "fine": -4,
    "resignation": -4,
    "litigation": -5,
    "downgrade": -5,
    "debt restructuring": -6,
    "cancellation": -5,
    "termination": -5,
    "delisting": -6,
    "suspension": -6,
    "regulatory action": -5,
    "loss": -4,
    "profit decline": -5,
    "revenue decline": -5,
    "EBITDA decline": -5,
    "negative update": -5,
    "fraud investigation": -7,
    "show cause": -5,
    "notice": -3,
    "default in payment": -6,
}

# Impact Multipliers
IMPACT_MULTIPLIERS = {
    "board meeting": 0.5,
    "outcome of board meeting": 0.6,
    "record date": 0.3,
    "general update": 0.4,
    "press release": 0.5,
    "announcement": 0.5,
}

# Negative impact multipliers (reduces bullish confidence)
NEGATIVE_IMPACT_KEYWORDS = {
    "form mg": -5,
    "disclosure": -2,
    "corporate announcement": -1,
    "general": -1,
}


# ─────────────────────────────────────────────────────────────
# Sentiment Analysis
# ─────────────────────────────────────────────────────────────

def analyze_sentiment(text: str) -> dict:
    """
    Analyze announcement text for bullish/bearish sentiment.
    Returns score from -7 (very bearish) to +7 (very bullish).
    Also returns signal, impact, and matched keywords.
    """
    if not text:
        return {"score": 0, "signal": "⚪ NEUTRAL", "impact": "LOW", "matched_keywords": []}

    text_lower = text.lower()
    score = 0
    matched_keywords = []
    impact_modifier = 1.0

    # Check for impact multipliers
    for phrase, multiplier in IMPACT_MULTIPLIERS.items():
        if phrase in text_lower:
            impact_modifier *= (1 + multiplier)
            matched_keywords.append(phrase)

    # Check for negative impact keywords
    for phrase, penalty in NEGATIVE_IMPACT_KEYWORDS.items():
        if phrase in text_lower:
            score += penalty
            matched_keywords.append(phrase)

    # Check bullish keywords
    for keyword, weight in BULLISH_KEYWORDS.items():
        if keyword in text_lower:
            scored_weight = int(weight * impact_modifier)
            score += scored_weight
            matched_keywords.append(f"{keyword}(+{scored_weight})")

    # Check bearish keywords
    for keyword, weight in BEARISH_KEYWORDS.items():
        if keyword in text_lower:
            scored_weight = int(weight * impact_modifier)
            score += scored_weight
            matched_keywords.append(f"{keyword}({scored_weight})")

    # Clamp score to [-7, +7]
    score = max(-7, min(7, score))

    # Determine signal
    if score >= 3:
        signal = "🚀 BULLISH"
        impact = "HIGH"
    elif score >= 1:
        signal = "🟢 MILD BULLISH"
        impact = "MEDIUM"
    elif score <= -3:
        signal = "🔻 BEARISH"
        impact = "HIGH"
    elif score <= -1:
        signal = "🔴 MILD BEARISH"
        impact = "MEDIUM"
    else:
        signal = "⚪ NEUTRAL"
        impact = "LOW"

    return {
        "score": score,
        "signal": signal,
        "impact": impact,
        "matched_keywords": matched_keywords,
        "raw_text_snippet": text[:100],
    }


# ─────────────────────────────────────────────────────────────
# Live Price Fetch
# ─────────────────────────────────────────────────────────────

def get_live_price(symbol: str) -> dict:
    """
    Fetch real-time price data for a symbol using yfinance.
    """
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        hist = ticker.history(period="5d", interval="1d", auto_adjust=False)

        if hist.empty:
            logger.warning(f"No price history for {symbol}")
            return {
                "price": None,
                "change": 0.0,
                "change_pct": 0.0,
                "volume": 0,
                "volume_surge_pct": 0.0,
                "trend": "N/A",
                "drift": "N/A",
            }

        close = hist["Close"]
        current_price = round(close.iloc[-1], 2)
        prev_close = close.iloc[-2] if len(close) >= 2 else current_price
        change = round(current_price - prev_close, 2)
        change_pct = round(((current_price - prev_close) / prev_close) * 100, 2)

        volume = int(hist["Volume"].iloc[-1]) if "Volume" in hist else 0

        # Average volume (last 20 days)
        avg_volume_20d = int(hist["Volume"].tail(20).mean()) if len(hist) >= 20 else volume
        volume_surge_pct = round(
            ((volume - avg_volume_20d) / max(avg_volume_20d, 1)) * 100, 1
        )

        # Trend determination
        if change_pct > 1.5:
            trend = "📈 Strong Up"
        elif change_pct > 0.5:
            trend = "📈 Up"
        elif change_pct < -1.5:
            trend = "📉 Strong Down"
        elif change_pct < -0.5:
            trend = "📉 Down"
        else:
            trend = "➡️ Sideways"

        # Drift Score (price action strength)
        drift = "LOW"
        if abs(change_pct) >= 3:
            drift = "VERY_HIGH"
        elif abs(change_pct) >= 2:
            drift = "HIGH"
        elif abs(change_pct) >= 1:
            drift = "MEDIUM"

        return {
            "price": current_price,
            "change": change,
            "change_pct": change_pct,
            "volume": volume,
            "avg_volume_20d": avg_volume_20d,
            "volume_surge_pct": volume_surge_pct,
            "trend": trend,
            "drift": drift,
        }

    except Exception as e:
        logger.error(f"Live price fetch failed for {symbol}: {e}")
        return {
            "price": None,
            "change": 0.0,
            "change_pct": 0.0,
            "volume": 0,
            "volume_surge_pct": 0.0,
            "trend": "N/A",
            "drift": "N/A",
        }


# ─────────────────────────────────────────────────────────────
# PEAD Drift Scoring
# ─────────────────────────────────────────────────────────────

def calculate_drift_score(announcement: dict) -> dict:
    """
    Calculates a PEAD drift score based on sentiment + price action.
    
    Returns:
        - raw_score: float
        - final_signal: str  (CONFIRMED BULLISH, MODERATE, CONFLICT, etc.)
        - confidence: str    (HIGH / MEDIUM / LOW)
    """
    score = int(announcement.get("score", 0))
    live_price = announcement.get("live_price", {}) or {}
    change_pct = live_price.get("change_pct", 0.0) or 0.0
    drift_raw = live_price.get("drift", "LOW")

    final_signal = "⚪ No Drift"
    raw_score = 0.0
    confidence = "LOW"

    # Sentiment direction
    sentimental_bullish = score >= 2
    sentimental_bearish = score <= -2

    # Price direction
    price_bullish = change_pct > 0.5
    price_bearish = change_pct < -0.5

    # Strong alignment: Sentiment + Price same direction
    if sentimental_bullish and price_bullish:
        raw_score = abs(score) * 1.5 + (change_pct * 12)
        final_signal = "✅ CONFIRMED BULLISH (PEAD+)"
        confidence = "HIGH"

    elif sentimental_bearish and price_bearish:
        raw_score = abs(score) * 1.5 + (abs(change_pct) * 12)
        final_signal = "✅ CONFIRMED BEARISH (PEAD-)"
        confidence = "HIGH"

    # Partial alignment: Sentiment strong, price mild
    elif sentimental_bullish and not price_bearish:
        raw_score = abs(score) * 1.0 + (change_pct * 8)
        final_signal = "🟡 MODERATE BULLISH DRIFT"
        confidence = "MEDIUM"

    elif sentimental_bearish and not price_bullish:
        raw_score = abs(score) * 1.0 + (abs(change_pct) * 8)
        final_signal = "🟡 MODERATE BEARISH DRIFT"
        confidence = "MEDIUM"

    # Conflict: Sentiment and Price in opposite direction
    elif sentimental_bullish and price_bearish:
        raw_score = abs(score) * 0.5 - (abs(change_pct) * 8)
        final_signal = "⚠️ CONFLICT: Bullish News / Bearish Price"
        confidence = "LOW"

    elif sentimental_bearish and price_bullish:
        raw_score = abs(score) * 0.5 - (abs(change_pct) * 8)
        final_signal = "⚠️ CONFLICT: Bearish News / Bullish Price"
        confidence = "LOW"

    # Neutral territory
    else:
        raw_score = abs(change_pct) * 6
        final_signal = "⚪ NEUTRAL DRIFT"
        confidence = "LOW"

    # Boost for very strong drift
    if drift_raw in ("VERY_HIGH", "HIGH"):
        raw_score *= 1.15
        if "CONFIRMED" in final_signal:
            final_signal += " 🔥"

    raw_score = round(raw_score, 2)

    return {
        "raw_score": raw_score,
        "final_signal": final_signal,
        "confidence": confidence,
        "sentiment_score": score,
        "price_change_pct": change_pct,
    }


# ─────────────────────────────────────────────────────────────
# Main Pipeline
# ─────────────────────────────────────────────────────────────

def process_analysis(announcements: list) -> list:
    """
    Full analysis pipeline for a list of NSE announcements.
    
    Steps:
        1. Sentiment Analysis (keyword-based)
        2. Live Price Fetch (yfinance)
        3. PEAD Drift Score
        4. Multi-factor Confirmation Score
    
    Args:
        announcements: list of dicts with keys:
            - symbol, company, subject, date, pdf_url, source
    
    Returns:
        list of dicts with enriched analysis data
    """
    if not announcements:
        return []

    logger.info(f"Processing {len(announcements)} announcements...")

    for idx, ann in enumerate(announcements):
        symbol = ann.get("symbol", "")
        company = ann.get("company", "")
        subject = ann.get("subject", "")
        symbol_lower = symbol.lower().strip()

        logger.info(f"[{idx+1}/{len(announcements)}] {company} ({symbol})")

        # ── Step 1: Sentiment ────────────────────────────────
        analysis = analyze_sentiment(subject)
        ann.update(analysis)

        # ── Step 2: Live Price ───────────────────────────────
        live_price_data = get_live_price(symbol)
        ann["live_price"] = live_price_data

        # ── Step 3: PEAD Drift ───────────────────────────────
        drift_score = calculate_drift_score(ann)
        ann["drift_score"] = drift_score
        ann["pead_signal"] = drift_score["final_signal"]

        # ── Step 4: Multi-factor Confirmation Score ──────────
        if live_price_data and live_price_data.get("price") is not None:
            confirmation = compute_confirmation_score(ann)
            ann["confirmation"] = confirmation
            ann["confirmation_score"] = confirmation["final_score"]
            ann["confirmation_tier"] = confirmation["tier"]
            ann["telegram_ready"] = confirmation["telegram_ready"]
            ann["direction"] = confirmation["direction"]
            ann["sub_scores"] = confirmation.get("sub_scores", {})
        else:
            ann["confirmation"] = None
            ann["confirmation_score"] = 0
            ann["confirmation_tier"] = "⛔ NO ACTION"
            ann["telegram_ready"] = False
            ann["direction"] = "neutral"
            ann["sub_scores"] = {}

        logger.info(
            f"  → Signal: {analysis['signal']} | "
            f"Price: {live_price_data.get('price', 'N/A')} "
            f"({live_price_data.get('change_pct', 0):+.2f}%) | "
            f"PEAD: {ann['pead_signal'][:30]}... | "
            f"Confirm: {ann['confirmation_tier'][:20]} ({ann['confirmation_score']}/100)"
        )

    return announcements
