"""
analysis/confirmation_scorer.py
Multi-factor confirmation scoring engine for NSE announcement analysis.
"""

import logging
from functools import lru_cache
import yfinance as yf

logger = logging.getLogger(__name__)


# ------------------------------------------------------------
# Config
# ------------------------------------------------------------

WEIGHTS = {
    "sentiment": 20,
    "price_action": 25,
    "volume": 15,
    "market": 10,
    "fundamentals": 20,
    "news_quality": 10,
}

NEWS_KEYWORD_WEIGHTS = {
    "order win": 22,
    "order received": 22,
    "new order": 20,
    "contract": 18,
    "acquisition": 18,
    "merger": 18,
    "buyback": 20,
    "dividend": 16,
    "bonus": 16,
    "stock split": 14,
    "split": 12,
    "record date": 8,
    "results": 14,
    "quarterly results": 16,
    "earnings": 16,
    "profit increase": 18,
    "revenue growth": 16,
    "capacity expansion": 18,
    "expansion": 14,
    "guidance raised": 20,
    "strategic partnership": 14,
    "joint venture": 14,
    "approval": 12,
    "regulatory approval": 18,
    "default": 25,
    "fraud": 25,
    "investigation": 20,
    "penalty": 16,
    "fine": 14,
    "resignation": 12,
    "litigation": 16,
    "downgrade": 14,
    "debt restructuring": 18,
    "cancellation": 16,
    "termination": 16,
    "delisting": 18,
    "suspension": 18,
    "board meeting": 4,
    "outcome of board meeting": 8,
}

SECTOR_MAP = {
    "RELIANCE": "NIFTYENERGY",
    "ONGC": "NIFTYENERGY",
    "COALINDIA": "NIFTYMETAL",
    "TATASTEEL": "NIFTYMETAL",
    "HINDALCO": "NIFTYMETAL",
    "INFY": "NIFTYIT",
    "TCS": "NIFTYIT",
    "WIPRO": "NIFTYIT",
    "HCLTECH": "NIFTYIT",
    "ICICIBANK": "BANKNIFTY",
    "HDFCBANK": "BANKNIFTY",
    "SBIN": "BANKNIFTY",
    "AXISBANK": "BANKNIFTY",
}


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def clamp(value, low=0, high=100):
    return max(low, min(high, round(value, 2)))


def safe_float(value, default=None):
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def get_direction(signal_text: str) -> str:
    text = str(signal_text or "").upper()
    if "BULLISH" in text:
        return "bullish"
    if "BEARISH" in text:
        return "bearish"
    return "neutral"


def fetch_history(symbol: str, period="6mo", interval="1d"):
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        hist = ticker.history(period=period, interval=interval, auto_adjust=False)
        return hist
    except Exception as e:
        logger.warning(f"History fetch failed for {symbol}: {e}")
        return None


@lru_cache(maxsize=1)
def get_nifty_snapshot():
    """
    Uses Nifty index as market regime proxy.
    """
    try:
        ticker = yf.Ticker("^NSEI")
        hist = ticker.history(period="10d", interval="1d", auto_adjust=False)

        if hist is None or hist.empty or len(hist) < 6:
            return {
                "nifty_1d": 0.0,
                "nifty_5d": 0.0,
                "regime": "neutral",
                "score": 50,
            }

        close = hist["Close"]
        last_close = close.iloc[-1]
        prev_close = close.iloc[-2]
        close_5d = close.iloc[-6]

        nifty_1d = ((last_close - prev_close) / prev_close) * 100
        nifty_5d = ((last_close - close_5d) / close_5d) * 100

        score = 50
        regime = "neutral"

        if nifty_1d > 0.5 and nifty_5d > 1.0:
            score = 75
            regime = "bullish"
        elif nifty_1d < -0.5 and nifty_5d < -1.0:
            score = 25
            regime = "bearish"
        elif nifty_5d > 0:
            score = 60
            regime = "slightly_bullish"
        elif nifty_5d < 0:
            score = 40
            regime = "slightly_bearish"

        return {
            "nifty_1d": round(nifty_1d, 2),
            "nifty_5d": round(nifty_5d, 2),
            "regime": regime,
            "score": score,
        }

    except Exception as e:
        logger.warning(f"Nifty snapshot failed: {e}")
        return {
            "nifty_1d": 0.0,
            "nifty_5d": 0.0,
            "regime": "neutral",
            "score": 50,
        }


@lru_cache(maxsize=256)
def get_fundamental_snapshot(symbol: str):
    """
    Pull approximate fundamental data from yfinance.
    Gracefully falls back if fields missing.
    """
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        info = ticker.info or {}

        return {
            "roe": safe_float(info.get("returnOnEquity")),
            "debt_to_equity": safe_float(info.get("debtToEquity")),
            "profit_margin": safe_float(info.get("profitMargins")),
            "revenue_growth": safe_float(info.get("revenueGrowth")),
            "earnings_growth": safe_float(info.get("earningsGrowth")),
            "current_ratio": safe_float(info.get("currentRatio")),
            "market_cap": safe_float(info.get("marketCap")),
            "avg_volume": safe_float(info.get("averageVolume")),
            "trailing_pe": safe_float(info.get("trailingPE")),
            "price_to_book": safe_float(info.get("priceToBook")),
        }

    except Exception as e:
        logger.warning(f"Fundamental fetch failed for {symbol}: {e}")
        return {
            "roe": None,
            "debt_to_equity": None,
            "profit_margin": None,
            "revenue_growth": None,
            "earnings_growth": None,
            "current_ratio": None,
            "market_cap": None,
            "avg_volume": None,
            "trailing_pe": None,
            "price_to_book": None,
        }


# ------------------------------------------------------------
# Sub-score engines
# ------------------------------------------------------------

def score_sentiment(announcement: dict):
    raw_score = abs(int(announcement.get("score", 0)))
    impact = str(announcement.get("impact", "LOW")).upper()
    subject = str(announcement.get("subject", "")).lower()

    if raw_score >= 4:
        score = 90
    elif raw_score == 3:
        score = 82
    elif raw_score == 2:
        score = 72
    elif raw_score == 1:
        score = 60
    else:
        score = 35

    if impact == "HIGH":
        score += 10
    elif impact == "MEDIUM":
        score += 5

    if "board meeting" in subject and raw_score <= 1:
        score -= 8

    return {
        "score": clamp(score),
        "note": f"keyword_strength={raw_score}, impact={impact}",
    }


def score_price_action(announcement: dict):
    symbol = announcement.get("symbol", "")
    live_price = announcement.get("live_price", {}) or {}
    direction = get_direction(announcement.get("signal"))

    change_pct = safe_float(live_price.get("change_pct"), 0.0)
    score = 50

    # Immediate move
    if direction == "bullish":
        if change_pct >= 4:
            score = 90
        elif change_pct >= 2:
            score = 78
        elif change_pct >= 1:
            score = 68
        elif change_pct > -1:
            score = 52
        elif change_pct > -2:
            score = 35
        else:
            score = 20
    elif direction == "bearish":
        if change_pct <= -4:
            score = 90
        elif change_pct <= -2:
            score = 78
        elif change_pct <= -1:
            score = 68
        elif change_pct < 1:
            score = 52
        elif change_pct < 2:
            score = 35
        else:
            score = 20
    else:
        if abs(change_pct) >= 3:
            score = 65
        elif abs(change_pct) >= 1:
            score = 55
        else:
            score = 40

    hist = fetch_history(symbol, period="6mo")
    note_parts = [f"1d_change={change_pct:.2f}%"]

    try:
        if hist is not None and not hist.empty:
            close = hist["Close"]
            last_close = close.iloc[-1]

            if len(close) >= 20:
                sma20 = close.tail(20).mean()
                if last_close > sma20:
                    score += 8 if direction != "bearish" else -5
                    note_parts.append("above_20dma")
                else:
                    score -= 8 if direction != "bearish" else 5
                    note_parts.append("below_20dma")

            if len(close) >= 50:
                sma50 = close.tail(50).mean()
                if last_close > sma50:
                    score += 6 if direction != "bearish" else -6
                    note_parts.append("above_50dma")
                else:
                    score -= 6 if direction != "bearish" else 6
                    note_parts.append("below_50dma")

            if len(close) >= 6:
                ret_5d = ((close.iloc[-1] - close.iloc[-6]) / close.iloc[-6]) * 100
                note_parts.append(f"5d_return={ret_5d:.2f}%")

                if direction == "bullish" and ret_5d > 0:
                    score += 6
                elif direction == "bullish" and ret_5d < 0:
                    score -= 6
                elif direction == "bearish" and ret_5d < 0:
                    score += 6
                elif direction == "bearish" and ret_5d > 0:
                    score -= 6

    except Exception as e:
        logger.warning(f"Price action scoring failed for {symbol}: {e}")

    return {
        "score": clamp(score),
        "note": ", ".join(note_parts),
    }


def score_volume(announcement: dict):
    live_price = announcement.get("live_price", {}) or {}
    symbol = announcement.get("symbol", "")
    surge_pct = safe_float(live_price.get("volume_surge_pct"), 0.0)
    today_volume = safe_float(live_price.get("volume"), 0.0)

    score = 35
    if surge_pct >= 250:
        score = 92
    elif surge_pct >= 180:
        score = 82
    elif surge_pct >= 140:
        score = 72
    elif surge_pct >= 110:
        score = 62
    elif surge_pct >= 90:
        score = 52
    else:
        score = 38

    fundamentals = get_fundamental_snapshot(symbol)
    avg_volume = safe_float(fundamentals.get("avg_volume"))

    if today_volume and today_volume < 100000:
        score -= 12

    if avg_volume:
        if avg_volume < 100000:
            score -= 10
        elif avg_volume > 1000000:
            score += 8

    return {
        "score": clamp(score),
        "note": f"volume_surge={surge_pct:.1f}%, today_volume={int(today_volume) if today_volume else 0}",
    }


def score_market_context(announcement: dict):
    direction = get_direction(announcement.get("signal"))
    live_price = announcement.get("live_price", {}) or {}
    stock_change = safe_float(live_price.get("change_pct"), 0.0)

    nifty = get_nifty_snapshot()
    nifty_1d = safe_float(nifty.get("nifty_1d"), 0.0)
    base_score = safe_float(nifty.get("score"), 50)

    relative_strength = stock_change - nifty_1d
    score = base_score

    if direction == "bullish":
        if relative_strength >= 2:
            score += 18
        elif relative_strength >= 1:
            score += 10
        elif relative_strength < 0:
            score -= 10
    elif direction == "bearish":
        if relative_strength <= -2:
            score += 18
        elif relative_strength <= -1:
            score += 10
        elif relative_strength > 0:
            score -= 10

    return {
        "score": clamp(score),
        "note": f"nifty_1d={nifty_1d:.2f}%, rs={relative_strength:.2f}%, regime={nifty.get('regime')}",
    }


def score_fundamentals(announcement: dict):
    symbol = announcement.get("symbol", "")
    f = get_fundamental_snapshot(symbol)

    score = 50
    available = 0

    roe = safe_float(f.get("roe"))
    if roe is not None:
        available += 1
        if roe >= 0.18:
            score += 15
        elif roe >= 0.12:
            score += 10
        elif roe >= 0.08:
            score += 5
        elif roe <= 0:
            score -= 12

    debt = safe_float(f.get("debt_to_equity"))
    if debt is not None:
        available += 1
        if debt < 0.5:
            score += 12
        elif debt < 1.0:
            score += 8
        elif debt < 2.0:
            score += 2
        else:
            score -= 10

    margin = safe_float(f.get("profit_margin"))
    if margin is not None:
        available += 1
        if margin >= 0.15:
            score += 10
        elif margin >= 0.08:
            score += 6
        elif margin < 0:
            score -= 10

    revenue_growth = safe_float(f.get("revenue_growth"))
    if revenue_growth is not None:
        available += 1
        if revenue_growth >= 0.15:
            score += 8
        elif revenue_growth >= 0.05:
            score += 5
        elif revenue_growth < 0:
            score -= 8

    earnings_growth = safe_float(f.get("earnings_growth"))
    if earnings_growth is not None:
        available += 1
        if earnings_growth >= 0.15:
            score += 10
        elif earnings_growth >= 0.05:
            score += 6
        elif earnings_growth < 0:
            score -= 10

    current_ratio = safe_float(f.get("current_ratio"))
    if current_ratio is not None:
        available += 1
        if current_ratio > 1.3:
            score += 4
        elif current_ratio < 1.0:
            score -= 4

    if available <= 1:
        score = 50

    return {
        "score": clamp(score),
        "note": (
            f"roe={roe}, debt={debt}, margin={margin}, "
            f"rev_growth={revenue_growth}, earn_growth={earnings_growth}, data_points={available}"
        ),
    }


def score_news_quality(announcement: dict):
    subject = str(announcement.get("subject", "")).lower()
    score = 25
    matched = []

    for keyword, weight in NEWS_KEYWORD_WEIGHTS.items():
        if keyword in subject:
            score += weight
            matched.append(keyword)

    if not matched:
        score = 35

    if "board meeting" in subject and len(matched) == 1:
        score -= 5

    return {
        "score": clamp(score),
        "note": f"matched={matched[:5]}",
    }


# ------------------------------------------------------------
# Final engine
# ------------------------------------------------------------

def compute_confirmation_score(announcement: dict):
    """
    Final weighted confirmation score.
    """
    sentiment = score_sentiment(announcement)
    price_action = score_price_action(announcement)
    volume = score_volume(announcement)
    market = score_market_context(announcement)
    fundamentals = score_fundamentals(announcement)
    news_quality = score_news_quality(announcement)

    weighted_score = (
        sentiment["score"] * WEIGHTS["sentiment"] +
        price_action["score"] * WEIGHTS["price_action"] +
        volume["score"] * WEIGHTS["volume"] +
        market["score"] * WEIGHTS["market"] +
        fundamentals["score"] * WEIGHTS["fundamentals"] +
        news_quality["score"] * WEIGHTS["news_quality"]
    ) / 100

    direction = get_direction(announcement.get("signal"))
    live_price = announcement.get("live_price", {}) or {}
    change_pct = safe_float(live_price.get("change_pct"), 0.0)

    bonus = 0
    penalties = []

    # Directional alignment bonus / penalty
    if direction == "bullish":
        if change_pct >= 1.5:
            bonus += 8
        elif change_pct < -1.0:
            bonus -= 12
            penalties.append("bullish_news_but_price_weak")
    elif direction == "bearish":
        if change_pct <= -1.5:
            bonus += 8
        elif change_pct > 1.0:
            bonus -= 12
            penalties.append("bearish_news_but_price_strong")

    # Hard filters
    if sentiment["score"] < 50 and news_quality["score"] < 45:
        bonus -= 8
        penalties.append("weak_news_signal")

    if volume["score"] < 40:
        bonus -= 5
        penalties.append("weak_volume_confirmation")

    final_score = clamp(weighted_score + bonus)

    # Tier logic
    if (
        final_score >= 80 and
        sentiment["score"] >= 60 and
        price_action["score"] >= 65 and
        volume["score"] >= 55
    ):
        tier = "🔥 STRONG CONFIRMED"
        telegram_ready = True

    elif (
        final_score >= 65 and
        sentiment["score"] >= 55 and
        price_action["score"] >= 55
    ):
        tier = "✅ MODERATELY CONFIRMED"
        telegram_ready = True

    elif final_score >= 50:
        tier = "👀 WATCHLIST"
        telegram_ready = False

    else:
        tier = "⛔ NO ACTION"
        telegram_ready = False

    reasons = [
        f"Sentiment {sentiment['score']}",
        f"Price {price_action['score']}",
        f"Volume {volume['score']}",
        f"Market {market['score']}",
        f"Fundamentals {fundamentals['score']}",
        f"News {news_quality['score']}",
    ]

    if penalties:
        reasons.extend([f"Penalty: {p}" for p in penalties])

    return {
        "final_score": final_score,
        "tier": tier,
        "telegram_ready": telegram_ready,
        "direction": direction,
        "weighted_score": round(weighted_score, 2),
        "bonus_adjustment": bonus,
        "reasons": reasons,
        "sub_scores": {
            "sentiment": sentiment,
            "price_action": price_action,
            "volume": volume,
            "market": market,
            "fundamentals": fundamentals,
            "news_quality": news_quality,
        },
    }
