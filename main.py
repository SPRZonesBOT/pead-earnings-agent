# main.py
import os
import sys
import json
import argparse
from datetime import datetime

# Ensure project root is in path
sys.path.append(os.path.dirname(__file__))

# Custom modules
from announcements.nse_watcher import NSEWatcher
from announcements.bse_watcher import BSEWatcher
from announcements.screener_watcher import ScreenerWatcher
from announcements.price_fetcher import PriceFetcher
from database.db_manager import AnnouncementDB
from notifier_telegram import send_telegram_alert
import config

# State file
STATE_FILE = "state.json"

# -------------------------------------------------------------------
# State Management
# -------------------------------------------------------------------
def reset_state():
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
        print("🗑️ State reset successfully. All stocks will be reprocessed.")
    else:
        print("ℹ️ No state file found to reset.")

def get_processed_ids():
    try:
        with open(STATE_FILE, 'r') as f:
            return set(json.load(f).get('processed', []))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()

def save_processed_id(filing_id):
    existing = get_processed_ids()
    existing.add(filing_id)
    with open(STATE_FILE, 'w') as f:
        json.dump({'processed': list(existing)}, f)

# -------------------------------------------------------------------
# Mock Financials (fallback)
# -------------------------------------------------------------------
def get_mock_financials(symbol):
    """Return mock financials with growth values."""
    mock_data = {
        'RELIANCE': {
            'revenue': 250000, 'pat': 20000, 'ebitda': 35000, 'eps': 45,
            'ebitda_margin': 14.0, 'pat_margin': 8.0,
            'qoq_rev_growth': 8.5, 'qoq_pat_growth': 6.2,
            'yoy_rev_growth': 10.0, 'yoy_pat_growth': 8.5
        },
        'TCS': {
            'revenue': 60000, 'pat': 12000, 'ebitda': 15000, 'eps': 35,
            'ebitda_margin': 25.0, 'pat_margin': 20.0,
            'qoq_rev_growth': 16.2, 'qoq_pat_growth': 19.8,
            'yoy_rev_growth': 14.0, 'yoy_pat_growth': 18.0
        },
        'HDFCBANK': {
            'revenue': 45000, 'pat': 15000, 'ebitda': 20000, 'eps': 28,
            'ebitda_margin': 44.0, 'pat_margin': 33.0,
            'qoq_rev_growth': 13.5, 'qoq_pat_growth': 15.0,
            'yoy_rev_growth': 12.0, 'yoy_pat_growth': 14.0
        },
        'INFY': {
            'revenue': 40000, 'pat': 8000, 'ebitda': 10000, 'eps': 22,
            'ebitda_margin': 25.0, 'pat_margin': 20.0,
            'qoq_rev_growth': 12.0, 'qoq_pat_growth': 14.0,
            'yoy_rev_growth': 10.0, 'yoy_pat_growth': 12.0
        },
        'HINDUNILVR': {
            'revenue': 15000, 'pat': 3000, 'ebitda': 4000, 'eps': 15,
            'ebitda_margin': 27.0, 'pat_margin': 20.0,
            'qoq_rev_growth': 5.0, 'qoq_pat_growth': 7.0,
            'yoy_rev_growth': 4.0, 'yoy_pat_growth': 6.0
        },
        'ICICIBANK': {
            'revenue': 38000, 'pat': 11000, 'ebitda': 16000, 'eps': 18,
            'ebitda_margin': 42.0, 'pat_margin': 29.0,
            'qoq_rev_growth': 14.0, 'qoq_pat_growth': 16.5,
            'yoy_rev_growth': 12.0, 'yoy_pat_growth': 15.0
        },
        'SBIN': {
            'revenue': 120000, 'pat': 25000, 'ebitda': 45000, 'eps': 30,
            'ebitda_margin': 38.0, 'pat_margin': 21.0,
            'qoq_rev_growth': 9.0, 'qoq_pat_growth': 11.0,
            'yoy_rev_growth': 8.0, 'yoy_pat_growth': 10.0
        },
        'KOTAKBANK': {
            'revenue': 25000, 'pat': 8000, 'ebitda': 12000, 'eps': 40,
            'ebitda_margin': 48.0, 'pat_margin': 32.0,
            'qoq_rev_growth': 18.0, 'qoq_pat_growth': 20.0,
            'yoy_rev_growth': 16.0, 'yoy_pat_growth': 18.0
        },
        'LT': {
            'revenue': 55000, 'pat': 5000, 'ebitda': 7000, 'eps': 38,
            'ebitda_margin': 13.0, 'pat_margin': 9.0,
            'qoq_rev_growth': 4.0, 'qoq_pat_growth': 2.0,
            'yoy_rev_growth': 3.0, 'yoy_pat_growth': 1.0
        },
        'BHARTIARTL': {
            'revenue': 40000, 'pat': 6000, 'ebitda': 18000, 'eps': 12,
            'ebitda_margin': 45.0, 'pat_margin': 15.0,
            'qoq_rev_growth': 22.0, 'qoq_pat_growth': 25.0,
            'yoy_rev_growth': 20.0, 'yoy_pat_growth': 22.0
        },
    }
    default = {
        'revenue': 5000, 'pat': 500, 'ebitda': 800, 'eps': 10,
        'ebitda_margin': 16.0, 'pat_margin': 10.0,
        'qoq_rev_growth': 12.0, 'qoq_pat_growth': 15.0,
        'yoy_rev_growth': 10.0, 'yoy_pat_growth': 12.0
    }
    return mock_data.get(symbol, default)

# -------------------------------------------------------------------
# Enhanced PEAD Scoring Engine
# -------------------------------------------------------------------
def calculate_pead_score(fin, qoq_rev=0, qoq_pat=0, yoy_rev=0, yoy_pat=0,
                         price_return=0, prev_fin=None):
    """
    Enhanced PEAD score (0-100) using QoQ, YoY, margins, EPS, margin expansion, price return.
    Weights:
    - Revenue Growth (QoQ+YoY weighted) : 20 pts
    - PAT Growth (QoQ+YoY weighted)    : 20 pts
    - EBITDA Margin                     : 15 pts
    - PAT Margin                        : 15 pts
    - EPS                               : 10 pts
    - Margin Expansion                  : 10 pts
    - Price Confirmation                : 10 pts
    Total = 100
    """
    score = 0
    details = {}

    # ---- 1. Revenue Growth (weighted avg of QoQ and YoY) - 20 pts ----
    if qoq_rev and yoy_rev:
        rev_growth = (0.7 * qoq_rev) + (0.3 * yoy_rev)
    else:
        rev_growth = max(qoq_rev, yoy_rev)
    details['rev_growth'] = round(rev_growth, 1)
    if rev_growth > 20:
        score += 20
    elif rev_growth > 12:
        score += 15
    elif rev_growth > 5:
        score += 8
    else:
        score += 2

    # ---- 2. PAT Growth (weighted avg) - 20 pts ----
    if qoq_pat and yoy_pat:
        pat_growth = (0.7 * qoq_pat) + (0.3 * yoy_pat)
    else:
        pat_growth = max(qoq_pat, yoy_pat)
    details['pat_growth'] = round(pat_growth, 1)
    if pat_growth > 25:
        score += 20
    elif pat_growth > 15:
        score += 15
    elif pat_growth > 5:
        score += 8
    else:
        score += 2

    # ---- 3. EBITDA Margin - 15 pts ----
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

    # ---- 4. PAT Margin - 15 pts ----
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

    # ---- 5. EPS - 10 pts ----
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

    # ---- 6. Margin Expansion - 10 pts ----
    if prev_fin and prev_fin.get('ebitda_margin', 0) > 0:
        margin_change = ebitda_margin - prev_fin.get('ebitda_margin', 0)
        if margin_change > 2:
            score += 10
        elif margin_change > 0:
            score += 5
        else:
            score += 0
    else:
        score += 5  # neutral if no prior

    # ---- 7. Price Return - 10 pts ----
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

# -------------------------------------------------------------------
# Main Orchestrator
# -------------------------------------------------------------------
def run_pead_cycle(force_mock=False, reset=False, no_real=False, scan_mode='full'):
    if reset:
        reset_state()

    db = AnnouncementDB()
    processed_ids = get_processed_ids()

    print(f"\n🚀 Starting PEAD Agent (Scan: {scan_mode.upper()})...")
    print(f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 50)

    announcements = []

    # ---------- Real Data Fetching ----------
    if not no_real and not force_mock:
        print(f"📡 Attempting Screener.in API with {scan_mode} scan...")
        try:
            screener = ScreenerWatcher()
            # Pass scan_mode string; watcher will map to list
            announcements = screener.get_financial_results(stocks_list=scan_mode)
            if announcements:
                print(f"✅ Found {len(announcements)} stocks via Screener.in.")
            else:
                print("⚠️ No data from Screener. Trying NSE...")
        except Exception as e:
            print(f"❌ Screener error: {e}. Trying NSE...")

        # 2. Fallback to NSE if Screener failed
        if not announcements:
            try:
                nse = NSEWatcher()
                announcements = nse.get_financial_results()
                if announcements:
                    print(f"✅ Found {len(announcements)} announcements via NSE.")
                else:
                    print("⚠️ No data from NSE. Trying BSE...")
            except Exception as e:
                print(f"❌ NSE error: {e}. Trying BSE...")

        # 3. Fallback to BSE if NSE failed
        if not announcements:
            try:
                bse = BSEWatcher()
                announcements = bse.get_financial_results()
                if announcements:
                    print(f"✅ Found {len(announcements)} announcements via BSE.")
                else:
                    print("⚠️ No data from BSE. Falling back to mock data.")
                    force_mock = True
            except Exception as e:
                print(f"❌ BSE error: {e}. Falling back to mock data.")
                force_mock = True
    else:
        force_mock = True

    # ---------- Mock Data ----------
    if force_mock:
        print("📊 Using MOCK data for testing.")
        mock_symbols = config.NIFTY_50[:10]  # just 10 for speed
        announcements = []
        for sym in mock_symbols:
            announcements.append({
                'symbol': sym,
                'company': sym + ' Ltd',
                'pdf_url': None,
                'id': f"MOCK_{sym}_{datetime.now().strftime('%Y%m%d')}",
                'date': datetime.now().strftime('%d-%b-%Y'),
                'close_price': 1000,
                'volume': 1000000,
                'avg_volume': 800000,
                'subject': 'Mock Financial Results'
            })

    # ---------- Process ----------
    candidates = []
    processed_count = 0
    skipped_count = 0

    # Price fetcher
    price_fetcher = None
    if config.ENABLE_PRICE_FETCH:
        price_fetcher = PriceFetcher()

    for ann in announcements:
        symbol = ann.get('symbol')
        filing_id = ann.get('id')
        if not symbol:
            continue

        if filing_id in processed_ids:
            print(f"⏭️ Skipping {symbol} - already processed.")
            skipped_count += 1
            continue

        print(f"📈 Processing {symbol}...")
        fin = None
        prev_fin = None

        # A. From Screener
        if 'financials' in ann and ann['financials']:
            fin = ann['financials']
            qoq_rev = fin.get('qoq_rev_growth', 0)
            qoq_pat = fin.get('qoq_pat_growth', 0)
            yoy_rev = fin.get('yoy_rev_growth', 0)
            yoy_pat = fin.get('yoy_pat_growth', 0)
            print(f"   📊 Screener data: Rev {fin.get('revenue',0):,.0f}, PAT {fin.get('pat',0):,.0f}, Margins EBT {fin.get('ebitda_margin',0):.1f}% PAT {fin.get('pat_margin',0):.1f}%")
            print(f"      Growth: QoQ Rev {qoq_rev:.1f}%, QoQ PAT {qoq_pat:.1f}%, YoY Rev {yoy_rev:.1f}%, YoY PAT {yoy_pat:.1f}%")

        # B. PDF parse (if any)
        elif ann.get('pdf_url'):
            pdf_path = None
            try:
                if hasattr(NSEWatcher, 'download_pdf'):
                    watcher = NSEWatcher()
                else:
                    watcher = BSEWatcher()
                pdf_path = watcher.download_pdf(ann['pdf_url'])
                if pdf_path:
                    from analysis.financial_extractor import FinancialExtractor
                    extractor = FinancialExtractor(pdf_path)
                    fin = extractor.extract_standalone_numbers()
                    if fin and fin.get('revenue', 0) == 0:
                        fin = None
            except Exception as e:
                print(f"   ⚠️ PDF processing error: {e}")
            finally:
                if pdf_path and os.path.exists(pdf_path):
                    os.remove(pdf_path)

        # C. Mock fallback
        if not fin:
            fin = get_mock_financials(symbol)
            qoq_rev = fin.get('qoq_rev_growth', 12.0)
            qoq_pat = fin.get('qoq_pat_growth', 15.0)
            yoy_rev = fin.get('yoy_rev_growth', 10.0)
            yoy_pat = fin.get('yoy_pat_growth', 12.0)
            print(f"   📊 Using mock financials for {symbol}")
            print(f"      Revenue: {fin.get('revenue',0):,.0f}, PAT: {fin.get('pat',0):,.0f}, EBITDA Margin: {fin.get('ebitda_margin',0):.1f}%, PAT Margin: {fin.get('pat_margin',0):.1f}%")
            print(f"      Growth: QoQ Rev {qoq_rev:.1f}%, QoQ PAT {qoq_pat:.1f}%, YoY Rev {yoy_rev:.1f}%, YoY PAT {yoy_pat:.1f}%")

        # Historical data for margin expansion (from DB)
        hist_df = db.get_history(symbol)
        if not hist_df.empty:
            prev_fin = hist_df.iloc[0].to_dict()

        # Price confirmation
        price_return = 0
        if config.ENABLE_PRICE_FETCH and price_fetcher and ann.get('date'):
            try:
                price_data = price_fetcher.get_price_confirmation(symbol, ann.get('date'))
                if price_data:
                    price_return = price_data.get('return_pct', 0)
                    print(f"      Price Return (5-day): {price_return:.1f}%")
            except Exception as e:
                print(f"      ⚠️ Price fetch failed: {e}")

        # Calculate score
        score_data = calculate_pead_score(
            fin=fin,
            qoq_rev=qoq_rev,
            qoq_pat=qoq_pat,
            yoy_rev=yoy_rev,
            yoy_pat=yoy_pat,
            price_return=price_return,
            prev_fin=prev_fin
        )
        score = score_data['total_score']

        # Liquidity penalty
        liquidity = db.get_liquidity(symbol)
        if liquidity < config.MIN_LIQUIDITY and liquidity > 0:
            print(f"   ⚠️ Low liquidity ({liquidity/1e7:.1f} Cr) - penalty -5")
            score = max(score - 5, 0)

        # Action
        if score >= config.BUY_THRESHOLD:
            action = "🔴 BUY"
        elif score >= config.WATCH_THRESHOLD:
            action = "🟡 WATCH"
        else:
            action = "🟢 AVOID"

        candidates.append({
            'symbol': symbol,
            'company': ann.get('company', symbol),
            'score': score,
            'action': action,
            'rev_growth': score_data.get('rev_growth', 0),
            'pat_growth': score_data.get('pat_growth', 0),
            'ebitda_margin': score_data.get('ebitda_margin', 0),
            'pat_margin': score_data.get('pat_margin', 0),
            'price_return': score_data.get('price_return', 0),
            'date': ann.get('date', '')
        })

        save_processed_id(filing_id)
        processed_count += 1
        print(f"   ✅ Score: {score} | {action}")

    print("-" * 50)
    print(f"📊 Summary: {processed_count} processed, {skipped_count} skipped.")

    # Top 10
    top_10 = sorted(candidates, key=lambda x: x['score'], reverse=True)[:10]

    if top_10:
        msg = f"📈 *TOP {len(top_10)} PEAD PICKS - THIS QUARTER*\n"
        msg += f"🕒 {datetime.now().strftime('%d-%b %I:%M %p')}\n\n"
        for i, stock in enumerate(top_10, 1):
            msg += f"{i}. *{stock['company']}* ({stock['symbol']})\n"
            msg += f"   📊 Score: {stock['score']} | {stock['action']}\n"
            msg += f"   📈 Rev Growth: {stock['rev_growth']}% | PAT Growth: {stock['pat_growth']}%\n"
            msg += f"   📉 EBITDA Margin: {stock['ebitda_margin']}% | PAT Margin: {stock['pat_margin']}%\n"
            if stock.get('price_return') is not None:
                msg += f"   📈 Price Return (5d): {stock['price_return']:.1f}%\n"
            if stock.get('date'):
                msg += f"   📅 {stock['date']}\n"
            msg += "\n"
        send_telegram_alert(msg)
        print("\n" + "="*50)
        print("📢 ALERT:")
        print(msg)
        print("="*50)
    else:
        print("ℹ️ No fresh high-quality PEAD candidates found.")

    print(f"\n✅ Cycle complete. Total processed in state: {len(get_processed_ids())}")

# -------------------------------------------------------------------
# Command-line Entry
# -------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PEAD Earnings Agent')
    parser.add_argument('--reset', action='store_true', help='Reset state')
    parser.add_argument('--force-mock', action='store_true', help='Force mock')
    parser.add_argument('--no-real', action='store_true', help='Skip real data')
    parser.add_argument('--scan-mode', choices=['quick', 'full'], default='full',
                        help='Scan mode: quick (Nifty 50) or full (all 280 stocks)')
    args = parser.parse_args()

    if args.no_real:
        args.force_mock = True

    run_pead_cycle(force_mock=args.force_mock, reset=args.reset,
                   no_real=args.no_real, scan_mode=args.scan_mode)
