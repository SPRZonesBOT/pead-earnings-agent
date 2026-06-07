"""
analysis/pead_analyzer.py — Analyze announcements for market impact
"""

import re

# Positive/Bullish Keywords
BULLISH_KEYWORDS = [
    "dividend", "bonus", "split", "acquisition", "profit increase", 
    "growth", "record date", "outcome of board meeting", "order win",
    "expansion", "successful", "positive", "increase in revenue",
    "joint venture", "takeover", "capacity expansion"
]

# Negative/Bearish Keywords
BEARISH_KEYWORDS = [
    "loss", "resignation", "decrease", "strike", "penalty", 
    "fine", "cancellation", "litigation", "investigation", "default",
    "fraud", "withdrawal", "termination", "reduction"
]

def analyze_sentiment(subject: str) -> dict:
    """
    Analyzes the text of an announcement to determine market sentiment.
    """
    subject_lower = str(subject).lower()
    score = 0
    signal = "NEUTRAL"
    
    # Check Bullish
    for word in BULLISH_KEYWORDS:
        if word in subject_lower:
            score += 1
            
    # Check Bearish
    for word in BEARISH_KEYWORDS:
        if word in subject_lower:
            score -= 1
            
    if score > 0:
        signal = "🚀 BULLISH"
    elif score < 0:
        signal = "🔻 BEARISH"
    else:
        signal = "⚪ NEUTRAL"
        
    # Determine Impact Level
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
        "impact": impact
    }

def process_analysis(announcements: list) -> list:
    """
    Takes a list of announcements and adds sentiment analysis to each.
    """
    if not announcements:
        return []
        
    for ann in announcements:
        analysis = analyze_sentiment(ann.get("subject", ""))
        ann.update(analysis)
        
    return announcements
