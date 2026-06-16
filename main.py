# main.py
import os
import sys
import json
import argparse
from datetime import datetime

# Ensure project root is in path
sys.path.append(os.path.dirname(__file__))

from announcements.nse_watcher import NSEWatcher   # NSE API (Recommended)
from announcements.bse_watcher import BSEWatcher   # BSE API (Fallback)
from database.db_manager import AnnouncementDB
from notifier_telegram import send_telegram_alert

# State file to avoid duplicate alerts
STATE_FILE = "state.json"

def reset_state():
    """Delete state.json to force reprocessing of all stocks"""
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
        print("🗑️ State reset successfully. All stocks will be reprocessed.")
    else:
        print("ℹ️ No state file found to reset.")

def get_processed_ids():
    """Get set of already processed announcement IDs"""
    try:
        with open(STATE_FILE, 'r') as f:
            return set(json.load(f).get('processed', []))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()

def save_processed_id(filing_id):
    """Save processed announcement ID to state file"""
    existing = get_processed_ids()
    existing.add(filing_id)
    with open(STATE_FILE, 'w') as f:
        json.dump({'processed': list(existing)}, f)

def get_mock_financials(symbol):
    """Return mock financials for testing when no real data available"""
    mock_data = {
        'RELIANCE': {'revenue': 250000, 'pat': 20000, 'ebitda': 35000, 'eps': 45, 'ebitda_margin': 14, 'pat_margin': 8},
        'TCS': {'revenue': 60000, 'pat': 12000, 'ebitda': 15000, 'eps': 35, 'ebitda_margin': 25, 'pat_margin': 20},
        'HDFCBANK': {'revenue': 45000, 'pat': 15000, 'ebitda': 20000, 'eps': 28, 'ebitda_margin': 44, 'pat_margin': 33},
        'INFY': {'revenue': 40000, 'pat': 8000, 'ebitda': 10000, 'eps': 22, 'ebitda_margin': 25, 'pat_margin': 20},
        'HINDUNILVR': {'revenue': 15000, 'pat': 3000, 'ebitda': 4000, 'eps': 15, 'ebitda_margin': 27, 'pat_margin': 20},
        'ICICIBANK': {'revenue': 38000, 'pat': 11000, 'ebitda': 16000, 'eps': 18, 'ebitda_margin': 42, 'pat_margin': 29},
        'SBIN': {'revenue': 120000, 'pat': 25000, 'ebitda': 45000, 'eps': 30, 'ebitda_margin': 38, 'pat_margin': 21},
        'KOTAKBANK': {'revenue': 25000, 'pat': 8000, 'ebitda': 12000, 'eps': 40, 'ebitda_margin': 48, 'pat_margin': 32},
        'LT': {'revenue': 55000, 'pat': 5000, 'ebitda': 7000, 'eps': 38, 'ebitda_margin': 13, 'pat_margin': 9},
        'BHARTIARTL': {'revenue': 40000, 'pat': 6000, 'ebitda': 18000, 'eps': 12, 'ebitda_margin': 45, 'pat_margin': 15},
    }
    return mock_data.get(symbol, {'revenue': 5000, 'pat': 500, 'ebitda': 800, 'eps': 10, 'ebitda_margin': 16, 'pat_margin': 10})

def calculate_pead_score(fin, prev_fin=None):
    """
    Simple PEAD scoring (0-100)
    Later you can replace this with your pead_analyzer.py
    """
    score = 0
    
    # Revenue growth (assuming 15% if no previous data)
    if prev_fin and prev_fin.get('revenue', 0) > 0:
        rev_growth = ((fin['revenue'] - prev_fin['revenue']) / prev_fin['revenue']) * 100
    else:
        rev_growth = 12  # Default assumption
    
    # PAT growth
    if prev_fin and prev_fin.get('pat', 0) > 0:
        pat_growth = ((fin['pat'] - prev_fin['pat']) / prev_fin['pat']) * 100
    else:
        pat_growth = 15  # Default assumption
    
    # 1. Revenue Surprise (Max 35)
    if rev_growth > 20: score += 35
    elif rev_growth > 10: score += 25
    elif rev_growth > 5: score += 15
    else: score += 5
    
    # 2. PAT Growth (Max 20)
    if pat_growth > 25: score += 20
    elif pat_growth > 15: score += 15
    elif pat_growth > 5: score += 8
    else: score += 2
    
    # 3. Margin Quality (Max 20)
    if fin.get('ebitda_margin', 0) > 30: score += 20
    elif fin.get('ebitda_margin', 0) > 20: score += 15
    elif fin.get('ebitda_margin', 0) > 15: score += 8
    else: score += 3
    
    # 4. PAT Margin (Max 15)
    if fin.get('pat_margin', 0) > 20: score += 15
    elif fin.get('pat_margin', 0) > 12: score += 10
    elif fin.get('pat_margin', 0) > 8: score += 5
    else: score += 2
    
    # 5. EPS Strength (Max 10)
    if fin.get('eps', 0) > 30: score += 10
    elif fin.get('eps', 0) > 20: score += 6
    elif fin.get('eps', 0) > 10: score += 3
    
    return {
        'total_score': min(score, 100),  # Cap at 100
        'rev_growth': round(rev_growth, 1),
        'pat_growth': round(pat_growth, 1),
        'ebitda_margin': round(fin.get('ebitda_margin', 0), 1),
        'pat_margin': round(fin.get('pat_margin', 0), 1)
    }

def run_pead_cycle(force_mock=False, reset=False):
    """Main PEAD cycle orchestrator"""
    
    if reset:
        reset_state()
    
    db = AnnouncementDB()
    processed_ids = get_processed_ids()
    
    print(f"\n🚀 Starting PEAD Agent...")
    print(f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 50)
    
    announcements = []
    
    # Try NSE first (most reliable)
    if not force_mock:
        print("📡 Attempting NSE API...")
        try:
            nse = NSEWatcher()
            announcements = nse.get_financial_results()
            if announcements:
                print(f"✅ Found {len(announcements)} announcements via NSE.")
            else:
                print("⚠️ No announcements from NSE. Trying BSE...")
                bse = BSEWatcher()
                announcements = bse.get_financial_results()
                if announcements:
                    print(f"✅ Found {len(announcements)} announcements via BSE.")
                else:
                    print("⚠️ No announcements from BSE either. Falling back to mock data.")
                    force_mock = True  # Fallback to mock
        except Exception as e:
            print(f"❌ Error fetching real data: {e}")
            print("🔄 Falling back to mock data...")
            force_mock = True
    
    # Force mock if requested or real data failed
    if force_mock:
        print("📊 Using MOCK data for testing (no real announcements fetched).")
        # Generate mock announcements for top 10 Nifty stocks
        mock_symbols = ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'HINDUNILVR', 
                        'ICICIBANK', 'SBIN', 'KOTAKBANK', 'LT', 'BHARTIARTL']
        announcements = []
        for i, sym in enumerate(mock_symbols):
            announcements.append({
                'symbol': sym,
                'company': sym + ' Ltd',
                'pdf_url': None,
                'id': f"MOCK_{sym}_{datetime.now().strftime('%Y%m%d')}",
                'date': datetime.now().strftime('%d-%b-%Y'),
                'close_price': 1000 + (i * 200),
                'volume': 1000000,
                'avg_volume': 800000,
                'subject': 'Financial Results Mock'
            })
    
    candidates = []
    processed_count = 0
    skipped_count = 0
    
    for ann in announcements:
        symbol = ann.get('symbol')
        filing_id = ann.get('id')
        
        # Skip if already processed
        if filing_id in processed_ids:
            print(f"⏭️ Skipping {symbol} - already processed.")
            skipped_count += 1
            continue
        
        try:
            print(f"📈 Processing {symbol}...")
            
            # Get financial data
            fin = None
            
            # Try to parse PDF if available
            pdf_path = None
            if ann.get('pdf_url'):
                try:
                    # Try downloading PDF
                    if hasattr(NSEWatcher, 'download_pdf'):
                        watcher = NSEWatcher()
                    else:
                        watcher = BSEWatcher()
                    pdf_path = watcher.download_pdf(ann['pdf_url'])
                except Exception as e:
                    print(f"   ⚠️ PDF download failed: {e}")
            
            if pdf_path:
                try:
                    from analysis.financial_extractor import FinancialExtractor
                    extractor = FinancialExtractor(pdf_path)
                    fin = extractor.extract_standalone_numbers()
                    if fin and fin.get('revenue', 0) == 0:
                        fin = None  # Invalid extraction
                except Exception as e:
                    print(f"   ⚠️ PDF parsing failed: {e}")
                    fin = None
                finally:
                    # Clean up temp PDF
                    if os.path.exists(pdf_path):
                        os.remove(pdf_path)
            
            # If no PDF data, use mock financials
            if not fin:
                fin = get_mock_financials(symbol)
                print(f"   📊 Using mock financials for {symbol}")
            
            # Get historical data (for comparison)
            hist_df = db.get_history(symbol)
            prev_fin = None
            if not hist_df.empty and len(hist_df) > 0:
                prev_fin = hist_df.iloc[0].to_dict()
            
            # Calculate PEAD score
            score_data = calculate_pead_score(fin, prev_fin)
            score = score_data['total_score']
            
            # Liquidity check (if available in DB)
            liquidity = db.get_liquidity(symbol)
            if liquidity < 5_00_00_000 and liquidity > 0:
                print(f"   ⚠️ Low liquidity ({liquidity/1e7:.1f} Cr) - adding penalty")
                score = max(score - 10, 0)
            
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
                'rev_growth': score_data['rev_growth'],
                'pat_growth': score_data['pat_growth'],
                'ebitda_margin': score_data['ebitda_margin'],
                'pat_margin': score_data['pat_margin'],
                'date': ann.get('date', '')
            })
            
            # Mark as processed
            save_processed_id(filing_id)
            processed_count += 1
            print(f"   ✅ Score: {score} | {action}")
            
        except Exception as e:
            print(f"   ❌ Error processing {symbol}: {e}")
            continue
    
    print("-" * 50)
    print(f"📊 Summary: {processed_count} processed, {skipped_count} skipped.")
    
    # Final Top 10 Ranking
    top_10 = sorted(candidates, key=lambda x: x['score'], reverse=True)[:10]
    
    # Send Notification
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
        
        # Send to Telegram (or print locally)
        send_telegram_alert(msg)
        print("\n" + "="*50)
        print("📢 ALERT:")
        print(msg)
        print("="*50)
    else:
        print("ℹ️ No fresh high-quality PEAD candidates found.")
    
    # Update processed count in state
    print(f"\n✅ Cycle complete. {len(get_processed_ids())} total stocks in processed state.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PEAD Earnings Agent')
    parser.add_argument('--reset', action='store_true', 
                        help='Reset state (process all stocks again)')
    parser.add_argument('--force-mock', action='store_true',
                        help='Force use of mock data (for testing)')
    parser.add_argument('--no-real', action='store_true',
                        help='Skip real data fetching, only use mock')
    
    args = parser.parse_args()
    
    # If --no-real is passed, force mock
    if args.no_real:
        args.force_mock = True
    
    run_pead_cycle(force_mock=args.force_mock, reset=args.reset)
