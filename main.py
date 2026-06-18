# main.py
import os, sys, json, argparse
from datetime import datetime
sys.path.append(os.path.dirname(__file__))

from announcements.screener_watcher import ScreenerWatcher
from announcements.nse_watcher import NSEWatcher
from announcements.bse_watcher import BSEWatcher
from announcements.price_fetcher import PriceFetcher
from database.db_manager import AnnouncementDB
from notifier_telegram import send_telegram_alert
from analysis.quantum_scoring import QuantumScorer
from analysis.quantum_weight_optimizer import QuantumWeightOptimizer
import config

STATE_FILE = "state.json"

def reset_state():
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
        print("🗑️ State reset.")

def get_processed_ids():
    try:
        with open(STATE_FILE, 'r') as f:
            return set(json.load(f).get('processed', []))
    except:
        return set()

def save_processed_id(fid):
    existing = get_processed_ids()
    existing.add(fid)
    with open(STATE_FILE, 'w') as f:
        json.dump({'processed': list(existing)}, f)

def get_mock_financials(symbol):
    # ... (same as before, include mock ratios)
    # For brevity, keep the existing mock function; ensure it has 'pe_ratio', 'div_yield'
    # We'll assume it returns a dict with at least those keys.
    return {}

def run_pead_cycle(force_mock=False, reset=False, no_real=False, scan_mode='full'):
    if reset:
        reset_state()
    db = AnnouncementDB()
    processed_ids = get_processed_ids()

    print(f"\n🚀 PEAD Agent (Scan: {scan_mode.upper()})")
    print(f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{'-'*50}")

    announcements = []
    if not no_real and not force_mock:
        print(f"📡 Screener.in ({scan_mode})...")
        try:
            screener = ScreenerWatcher()
            announcements = screener.get_financial_results(stocks_list=scan_mode)
        except Exception as e:
            print(f"❌ Screener error: {e}")
        if not announcements:
            # fallback to NSE/BSE...
            pass
    if not announcements:
        force_mock = True

    if force_mock:
        print("📊 Using MOCK data.")
        announcements = []
        for sym in config.NIFTY_50[:10]:
            announcements.append({'symbol': sym, 'company': sym+' Ltd', 'id': f"MOCK_{sym}", 'date': datetime.now().strftime('%d-%b-%Y')})

    scorer = QuantumScorer(lookback=50)
    price_fetcher = PriceFetcher() if config.ENABLE_PRICE_FETCH else None

    candidates = []
    processed = skipped = 0
    for ann in announcements:
        symbol = ann.get('symbol')
        fid = ann.get('id')
        if not symbol or fid in processed_ids:
            if fid in processed_ids:
                skipped += 1
            continue
        print(f"📈 {symbol}...")
        fin = None
        if 'financials' in ann and ann['financials']:
            fin = ann['financials']
        elif 'financials' not in ann:
            fin = get_mock_financials(symbol)  # fallback
        if not fin:
            fin = get_mock_financials(symbol)

        qoq_rev = fin.get('qoq_rev_growth', 0)
        qoq_pat = fin.get('qoq_pat_growth', 0)
        yoy_rev = fin.get('yoy_rev_growth', 0)
        yoy_pat = fin.get('yoy_pat_growth', 0)
        price_return = 0
        if price_fetcher and ann.get('date'):
            try:
                pd = price_fetcher.get_price_confirmation(symbol, ann.get('date'))
                if pd:
                    price_return = pd.get('return_pct', 0)
            except:
                pass

        # History for margin expansion (optional)
        hist_df = db.get_history(symbol)
        prev_fin = hist_df.iloc[0].to_dict() if not hist_df.empty else None

        score_data = scorer.score(fin, qoq_rev, qoq_pat, yoy_rev, yoy_pat, price_return, prev_fin)
        score = score_data['total_score']

        # liquidity penalty
        liq = db.get_liquidity(symbol)
        if liq < config.MIN_LIQUIDITY and liq > 0:
            score = max(score - 5, 0)

        action = "🔴 BUY" if score >= config.BUY_THRESHOLD else "🟡 WATCH" if score >= config.WATCH_THRESHOLD else "🟢 AVOID"

        candidates.append({
            'symbol': symbol,
            'company': ann.get('company', symbol),
            'score': score,
            'action': action,
            'rev_growth': score_data.get('rev_growth', 0),
            'pat_growth': score_data.get('pat_growth', 0),
            'ebitda_margin': score_data.get('ebitda_margin', 0),
            'pat_margin': score_data.get('pat_margin', 0),
            'cmp': fin.get('current_price', 0),
            'price_return': score_data.get('price_return', 0),
            'date': ann.get('date', '')
        })
        save_processed_id(fid)
        processed += 1
        print(f"   ✅ Score: {score:.1f} | {action}")

    print(f"Summary: {processed} processed, {skipped} skipped.")

    top10 = sorted(candidates, key=lambda x: x['score'], reverse=True)[:10]
    if top10:
        msg = f"📈 *TOP {len(top10)} PEAD PICKS*\n🕒 {datetime.now().strftime('%d-%b %I:%M %p')}\n\n"
        for i, s in enumerate(top10, 1):
            msg += f"{i}. *{s['company']}* ({s['symbol']})\n"
            msg += f"   📊 Score: {s['score']:.1f} | {s['action']}\n"
            msg += f"   📈 Rev: {s['rev_growth']:.1f}% | PAT: {s['pat_growth']:.1f}%\n"
            msg += f"   📉 EBITDA: {s['ebitda_margin']:.1f}% | PAT: {s['pat_margin']:.1f}%\n"
            if s.get('cmp', 0) > 0:
                msg += f"   💰 CMP: ₹{s['cmp']:,.2f}\n"
            if s.get('price_return') is not None:
                msg += f"   📈 Price Return (5d): {s['price_return']:.1f}%\n"
            msg += "\n"
        send_telegram_alert(msg)
        print("\n" + "="*50 + "\n📢 ALERT:\n" + msg + "="*50)

def run_weight_optimizer():
    # In a real system, you'd fetch historical features and returns from the database.
    # For demonstration, we generate synthetic data.
    # Replace this with actual historical data extraction.
    print("🔄 Preparing synthetic dataset...")
    np.random.seed(42)
    X = np.random.randn(500, 8)
    y = (0.3 * X[:, 0] + 0.2 * X[:, 1] + 0.1 * X[:, 2] - 0.1 * X[:, 5] + 0.2 * np.random.randn(500))
    y = y / np.std(y)
    optimizer = QuantumWeightOptimizer(X, y, n_iter=3000)
    optimizer.optimize()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--reset', action='store_true')
    parser.add_argument('--force-mock', action='store_true')
    parser.add_argument('--no-real', action='store_true')
    parser.add_argument('--scan-mode', choices=['quick','full'], default='full')
    parser.add_argument('--optimize-weights', action='store_true')
    args = parser.parse_args()

    if args.optimize_weights:
        run_weight_optimizer()
    else:
        if args.no_real:
            args.force_mock = True
        run_pead_cycle(force_mock=args.force_mock, reset=args.reset,
                       no_real=args.no_real, scan_mode=args.scan_mode)
