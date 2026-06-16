# main.py
import os
import sys
import json
import argparse
from datetime import datetime

# Ensure project root is in path
sys.path.append(os.path.dirname(__file__))

from announcements.nse_watcher import NSEWatcher
from announcements.bse_watcher import BSEWatcher
from announcements.screener_watcher import ScreenerWatcher   # New API-based
from database.db_manager import AnnouncementDB
from notifier_telegram import send_telegram_alert

# State file to avoid duplicate alerts
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
    """Return mock financials for testing when no real data available"""
    mock_data = {
        'RELIANCE':    {'revenue': 250000, 'pat': 20000, 'ebitda': 35000, 'eps': 45, 'ebitda_margin': 14.0, 'pat_margin': 8.0},
        'TCS':         {'revenue': 60000,  'pat': 12000, 'ebitda': 15000, 'eps': 35, 'ebitda_margin': 25.0, 'pat_margin': 20.0},
        'HDFCBANK':    {'revenue': 45000,  'pat': 15000, 'ebitda': 20000, 'eps': 28, 'ebitda_margin': 44.0, 'pat_margin': 33.0},
        'INFY':        {'revenue': 40000,  'pat': 8000,  'ebitda': 10000, 'eps': 22, 'ebitda_margin': 25.0, 'pat_margin': 20.0},
        'HINDUNILVR':  {'revenue': 15000,  'pat': 3000,  'ebitda': 4000,  'eps': 15, 'ebitda_margin': 27.0, 'pat_margin': 20.0},
        'ICICIBANK':   {'revenue': 38000,  'pat': 11000, 'ebitda': 16000, 'eps': 18, 'ebitda_margin': 42.0, 'pat_margin': 29.0},
        'SBIN':        {'revenue': 120000, 'pat': 25000, 'ebitda': 45000, 'eps': 30, 'ebitda_margin': 38.0, 'pat_margin': 21.0},
        'KOTAKBANK':   {'revenue': 25000,  'pat': 8000,  'ebitda': 12000, 'eps': 40, 'ebitda_margin': 48.0, 'pat_margin': 32.0},
        'LT':          {'revenue': 55000,  'pat': 5000,  'ebitda': 7000,  'eps': 38, 'ebitda_margin': 13.0, 'pat_margin': 9.0},
        'BHARTIARTL':  {'revenue': 40000,  'pat': 6000,  'ebitda': 18000, 'eps': 12, 'ebitda_margin': 45.0, 'pat_margin': 15.0},
    }
    return mock_data.get(symbol, {'revenue': 5000, 'pat': 500, 'ebitda': 800, 'eps': 10, 'ebitda_margin': 16.0, 'pat_margin': 10.0})

# -------------------------------------------------------------------
# PEAD Scoring Engine (Enhanced)
# -------------------------------------------------------------------
def calculate_pead_score(fin, prev_fin=None):
    """
    Enhanced PEAD score (0-100)
    Uses revenue growth, PAT growth, margins, EPS, and quality checks.
    """
    score = 0
    details = {}

    # 1. Revenue Growth (YoY or QoQ) – Max 25 points
    if prev_fin and prev_fin.get('revenue', 0) > 0:
        rev_growth = ((fin['revenue'] - prev_fin['revenue']) / prev_fin['revenue']) * 100
    else:
        rev_growth = 12  # default assumption
    details['rev_growth'] = round(rev_growth, 1)

    if rev_growth > 20:
        score += 25
    elif rev_growth > 12:
        score += 18
    elif rev_growth > 5:
        score += 10
    else:
        score += 3

    # 2. PAT Growth – Max 20 points
    if prev_fin and prev_fin.get('pat', 0) > 0:
        pat_growth = ((fin['pat'] - prev_fin['pat']) / prev_fin['pat']) * 100
    else:
        pat_growth = 15
    details['pat_growth'] = round(pat_growth, 1)

    if pat_growth > 25:
        score += 20
    elif pat_growth > 15:
        score += 15
    elif pat_growth > 5:
        score += 8
    else:
        score += 2

    # 3. EBITDA Margin level – Max 15 points
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

    # 4. PAT Margin level – Max 15 points
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

    # 5. EPS Strength – Max 15 points
    eps = fin.get('eps', 0)
    details['eps'] = round(eps, 2)
    if eps > 40:
        score += 15
    elif eps > 25:
        score += 10
    elif eps > 15:
        score += 5
    else:
        score += 2

    # 6. Quality Check: Margin expansion/contraction – Max 10 points
    if prev_fin and prev_fin.get('ebitda_margin', 0) > 0:
        margin_change = ebitda_margin - prev_fin.get('ebitda_margin', 0)
        if margin_change > 2:
            score += 10
        elif margin_change > 0:
            score += 5
        else:
            score += 0
    else:
        score += 5  # no prior data, neutral

    # Cap at 100
    score = min(score, 100)
    details['total_score'] = score

    return details

# -------------------------------------------------------------------
# Main Orchestrator
# -------------------------------------------------------------------
def run_pead_cycle(force_mock=False, reset=False, no_real=False):
    if reset:
        reset_state()

    db = AnnouncementDB()
    processed_ids = get_processed_ids()

    print(f"\n🚀 Starting PEAD Agent...")
    print(f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 50)

    announcements = []

    # ---------- Real Data Fetching ----------
    if not no_real and not force_mock:
        # 1. Try Screener.in (most reliable)
        print("📡 Attempting Screener.in API...")
        try:
            screener = ScreenerWatcher()
            announcements = screener.get_financial_results()
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

    # ---------- Mock Data (if requested or no real data) ----------
    if force_mock:
        print("📊 Using MOCK data for testing (no real announcements fetched).")
        mock_symbols = ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'HINDUNILVR',
                        'ICICIBANK', 'SBIN', 'KOTAKBANK', 'LT', 'BHARTIARTL']
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

    # ---------- Process Each Announcement ----------
    candidates = []
    processed_count = 0
    skipped_count = 0

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

        # A. If data is from Screener, financials already in dict
        if 'financials' in ann and ann['financials']:
            fin = ann['financials']
            print(f"   📊 Using Screener financials for {symbol}")
            # Debug: print extracted values
            print(f"      Revenue: {fin.get('revenue',0):,.0f}, PAT: {fin.get('pat',0):,.0f}, EBITDA Margin: {fin.get('ebitda_margin',0):.1f}%, PAT Margin: {fin.get('pat_margin',0):.1f}%")

        # B. Else try PDF download & parse
        elif ann.get('pdf_url'):
            pdf_path = None
            try:
                # Try downloading with NSE or BSE watcher (whichever has download method)
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
                        fin = None  # invalid extraction
            except Exception as e:
                print(f"   ⚠️ PDF processing error: {e}")
            finally:
                if pdf_path and os.path.exists(pdf_path):
                    os.remove(pdf_path)

        # C. If still no financials, use mock
        if not fin:
            fin = get_mock_financials(symbol)
            print(f"   📊 Using mock financials for {symbol}")
            print(f"      Revenue: {fin.get('revenue',0):,.0f}, PAT: {fin.get('pat',0):,.0f}, EBITDA Margin: {fin.get('ebitda_margin',0):.1f}%, PAT Margin: {fin.get('pat_margin',0):.1f}%")

        # Get historical data for comparison
        hist_df = db.get_history(symbol)
        if not hist_df.empty:
            prev_fin = hist_df.iloc[0].to_dict()

        # Calculate PEAD score
        score_data = calculate_pead_score(fin, prev_fin)
        score = score_data['total_score']

        # Apply liquidity penalty (if data available)
        liquidity = db.get_liquidity(symbol)
        if liquidity < 5_00_00_000 and liquidity > 0:
            print(f"   ⚠️ Low liquidity ({liquidity/1e7:.1f} Cr) - penalty -5")
            score = max(score - 5, 0)

        # Determine action
        if score >= 70:
            action = "🔴 BUY"
        elif score >= 50:
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
            'date': ann.get('date', '')
        })

        save_processed_id(filing_id)
        processed_count += 1
        print(f"   ✅ Score: {score} | {action}")

    print("-" * 50)
    print(f"📊 Summary: {processed_count} processed, {skipped_count} skipped.")

    # ---------- Top 10 Ranking ----------
    top_10 = sorted(candidates, key=lambda x: x['score'], reverse=True)[:10]

    # ---------- Send Alert ----------
    if top_10:
        msg = f"📈 *TOP {len(top_10)} PEAD PICKS - THIS QUARTER*\n"
        msg += f"🕒 {datetime.now().strftime('%d-%b %I:%M %p')}\n\n"

        for i, stock in enumerate(top_10, 1):
            msg += f"{i}. *{stock['company']}* ({stock['symbol']})\n"
            msg += f"   📊 Score: {stock['score']} | {stock['action']}\n"
            msg += f"   📈 Rev Growth: {stock['rev_growth']}% | PAT Growth: {stock['pat_growth']}%\n"
            msg += f"   📉 EBITDA Margin: {stock['ebitda_margin']}% | PAT Margin: {stock['pat_margin']}%\n"
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
    parser.add_argument('--reset', action='store_true', help='Reset state (process all stocks again)')
    parser.add_argument('--force-mock', action='store_true', help='Force use of mock data (for testing)')
    parser.add_argument('--no-real', action='store_true', help='Skip real data fetching, only use mock')
    args = parser.parse_args()

    if args.no_real:
        args.force_mock = True

    run_pead_cycle(force_mock=args.force_mock, reset=args.reset, no_real=args.no_real)
