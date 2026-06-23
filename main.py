# main.py
import os
import sys
import json
import argparse
from datetime import datetime
import numpy as np

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

# ---------- State Management ----------
def reset_state():
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
        print("[PEAD] State reset.")

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

# ---------- Mock Financials (fallback) ----------
def get_mock_financials(symbol):
    mock_data = {
        'RELIANCE': {
            'revenue': 250000, 'pat': 20000, 'ebitda': 35000, 'eps': 45,
            'ebitda_margin': 14.0, 'pat_margin': 8.0,
            'qoq_rev_growth': 8.5, 'qoq_pat_growth': 6.2,
            'yoy_rev_growth': 10.0, 'yoy_pat_growth': 8.5,
            'current_price': 1329.00,
            'pe_ratio': 22.5, 'div_yield': 0.8
        },
        'TCS': {
            'revenue': 60000, 'pat': 12000, 'ebitda': 15000, 'eps': 35,
            'ebitda_margin': 25.0, 'pat_margin': 20.0,
            'qoq_rev_growth': 16.2, 'qoq_pat_growth': 19.8,
            'yoy_rev_growth': 14.0, 'yoy_pat_growth': 18.0,
            'current_price': 4200.50,
            'pe_ratio': 28.0, 'div_yield': 1.2
        },
    }
    default = {
        'revenue': 5000, 'pat': 500, 'ebitda': 800, 'eps': 10,
        'ebitda_margin': 16.0, 'pat_margin': 10.0,
        'qoq_rev_growth': 12.0, 'qoq_pat_growth': 15.0,
        'yoy_rev_growth': 10.0, 'yoy_pat_growth': 12.0,
        'current_price': 1000.00,
        'pe_ratio': 20.0, 'div_yield': 1.0
    }
    return mock_data.get(symbol, default)

# ---------- Quantum Weight Optimizer Runner ----------
def run_weight_optimizer():
    print("[PEAD] Preparing synthetic dataset for weight optimization...")
    np.random.seed(42)
    n_samples = 500
    n_features = 8
    X = np.random.randn(n_samples, n_features)
    y = (0.3 * X[:, 0] + 0.2 * X[:, 1] + 0.1 * X[:, 2] - 0.1 * X[:, 5] + 0.2 * np.random.randn(n_samples))
    y = y / np.std(y)

    optimizer = QuantumWeightOptimizer(X, y, n_iter=3000, temp_init=100.0, cooling_rate=0.995)
    optimized_weights = optimizer.optimize()
    print("[PEAD] Optimization complete. Weights saved to 'weights.json'.")

# ---------- PEAD Orchestrator ----------
def run_pead_cycle(force_mock=False, reset=False, no_real=False, scan_mode='full'):
    if reset:
        reset_state()
    db = AnnouncementDB()
    processed_ids = get_processed_ids()

    print(f"\n[PEAD] Agent (Scan: {scan_mode.upper()})")
    print(f"[PEAD] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 50)

    announcements = []
    if not no_real and not force_mock:
        print(f"[PEAD] Screener.in ({scan_mode})...")
        try:
            screener = ScreenerWatcher()
            announcements = screener.get_financial_results(stocks_list=scan_mode)
        except Exception as e:
            print(f"[PEAD] Screener error: {e}")
        if not announcements:
            print("[PEAD] No data from Screener, trying fallback...")
    if not announcements:
        force_mock = True

    if force_mock:
        print("[PEAD] Using MOCK data.")
        announcements = []
        for sym in config.NIFTY_50[:10]:
            announcements.append({
                'symbol': sym,
                'company': sym + ' Ltd',
                'id': f"MOCK_{sym}",
                'date': datetime.now().strftime('%d-%b-%Y')
            })

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

        print(f"[PEAD] {symbol}...")
        fin = ann.get('financials') if 'financials' in ann else None
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

        hist_df = db.get_history(symbol)
        prev_fin = hist_df.iloc[0].to_dict() if not hist_df.empty else None

        score_data = scorer.score(fin, qoq_rev, qoq_pat, yoy_rev, yoy_pat, price_return, prev_fin)
        score = score_data['total_score']

        liq = db.get_liquidity(symbol)
        if liq < config.MIN_LIQUIDITY and liq > 0:
            score = max(score - 5, 0)

        action = "BUY" if score >= config.BUY_THRESHOLD else "WATCH" if score >= config.WATCH_THRESHOLD else "AVOID"

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
        print(f"   [PEAD] Score: {score:.1f} | {action}")

    print(f"[PEAD] Summary: {processed} processed, {skipped} skipped.")

    top10 = sorted(candidates, key=lambda x: x['score'], reverse=True)[:10]
    if top10:
        msg = f"[PEAD] TOP {len(top10)} PICKS\n{datetime.now().strftime('%d-%b %I:%M %p')}\n\n"
        for i, s in enumerate(top10, 1):
            msg += f"{i}. {s['company']} ({s['symbol']})\n"
            msg += f"   Score: {s['score']:.1f} | {s['action']}\n"
            msg += f"   Rev Growth: {s['rev_growth']:.1f}% | PAT Growth: {s['pat_growth']:.1f}%\n"
            msg += f"   EBITDA Margin: {s['ebitda_margin']:.1f}% | PAT Margin: {s['pat_margin']:.1f}%\n"
            if s.get('cmp', 0) > 0:
                msg += f"   CMP: Rs.{s['cmp']:,.2f}\n"
            if s.get('price_return') is not None:
                msg += f"   Price Return (5d): {s['price_return']:.1f}%\n"
            msg += "\n"
        send_telegram_alert(msg)
        print("\n" + "="*50 + "\n[PEAD] ALERT:\n" + msg + "="*50)
    else:
        print("[PEAD] No fresh candidates found.")

    print(f"[PEAD] Cycle complete. Total processed in state: {len(get_processed_ids())}")

# ---------- Command-line ----------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PEAD Earnings Agent')
    parser.add_argument('--reset', action='store_true', help='Reset state')
    parser.add_argument('--force-mock', action='store_true', help='Force mock data')
    parser.add_argument('--no-real', action='store_true', help='Skip real data')
    parser.add_argument('--scan-mode', choices=['quick', 'full'], default='full',
                        help='Scan mode: quick (Nifty 50) or full (all 280 stocks)')
    parser.add_argument('--optimize-weights', action='store_true',
                        help='Run quantum-inspired weight optimization and exit')
    args = parser.parse_args()

    if args.optimize_weights:
        run_weight_optimizer()
    else:
        if args.no_real:
            args.force_mock = True
        run_pead_cycle(force_mock=args.force_mock, reset=args.reset,
                       no_real=args.no_real, scan_mode=args.scan_mode)
