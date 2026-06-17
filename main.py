# main.py (final optimized version)
# ... (imports as before, plus from announcements.price_fetcher import PriceFetcher)
# We'll modify the scoring to include YoY and price.

def calculate_pead_score(fin, qoq_rev=0, qoq_pat=0, yoy_rev=0, yoy_pat=0, price_return=0, prev_fin=None):
    """
    Enhanced PEAD score with YoY growth and price confirmation.
    Weights:
    - Revenue Growth (QoQ+YoY combined): 25 pts
    - PAT Growth (QoQ+YoY combined): 20 pts
    - EBITDA Margin: 15 pts
    - PAT Margin: 15 pts
    - EPS: 15 pts
    - Margin Expansion: 10 pts (still)
    - Price Confirmation: extra 10 pts (bonus, but we keep total max 100 by adjusting)
    We'll allocate: Rev 20, PAT 15, Margins (EBITDA 12, PAT 12), EPS 10, Margin Expansion 10, Price 21? Better: keep total 100 by rebalancing.
    We'll do:
    - Revenue Growth (QoQ+YoY average): 20
    - PAT Growth (QoQ+YoY average): 20
    - EBITDA Margin: 15
    - PAT Margin: 15
    - EPS: 10
    - Margin Expansion: 10
    - Price Return: 10 (if positive)
    Total 100.
    """
    score = 0
    details = {}

    # Revenue Growth: average of QoQ and YoY
    avg_rev_growth = (qoq_rev + yoy_rev) / 2 if qoq_rev and yoy_rev else max(qoq_rev, yoy_rev)
    details['rev_growth'] = round(avg_rev_growth, 1)
    if avg_rev_growth > 20:
        score += 20
    elif avg_rev_growth > 12:
        score += 15
    elif avg_rev_growth > 5:
        score += 8
    else:
        score += 2

    # PAT Growth
    avg_pat_growth = (qoq_pat + yoy_pat) / 2 if qoq_pat and yoy_pat else max(qoq_pat, yoy_pat)
    details['pat_growth'] = round(avg_pat_growth, 1)
    if avg_pat_growth > 25:
        score += 20
    elif avg_pat_growth > 15:
        score += 15
    elif avg_pat_growth > 5:
        score += 8
    else:
        score += 2

    # EBITDA Margin
    ebitda_margin = fin.get('ebitda_margin', 0)
    details['ebitda_margin'] = round(ebitda_margin, 1)
    if ebitda_margin > 30:
        score += 15
    elif ebitda_margin > 20:
        score += 10
    elif ebitda_margin > 15:
        score += 5
    else:
        score += 2

    # PAT Margin
    pat_margin = fin.get('pat_margin', 0)
    details['pat_margin'] = round(pat_margin, 1)
    if pat_margin > 20:
        score += 15
    elif pat_margin > 12:
        score += 10
    elif pat_margin > 8:
        score += 5
    else:
        score += 2

    # EPS
    eps = fin.get('eps', 0)
    details['eps'] = round(eps, 2)
    if eps > 40:
        score += 10
    elif eps > 25:
        score += 7
    elif eps > 15:
        score += 4
    else:
        score += 1

    # Margin Expansion
    if prev_fin and prev_fin.get('ebitda_margin', 0) > 0:
        margin_change = ebitda_margin - prev_fin.get('ebitda_margin', 0)
        if margin_change > 2:
            score += 10
        elif margin_change > 0:
            score += 5
        else:
            score += 0
    else:
        score += 5

    # Price Confirmation (bonus)
    details['price_return'] = round(price_return, 1)
    if price_return > 3:
        score += 10
    elif price_return > 0:
        score += 5
    else:
        score += 0

    score = min(score, 100)
    details['total_score'] = score
    return details
