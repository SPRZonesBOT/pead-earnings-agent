# main.py
import os
import json
from datetime import datetime
from announcements.bse_watcher import BSEWatcher  # Assuming you have this
from database.db_manager import AnnouncementDB   # Assuming you have this
from analysis.financial_extractor import FinancialExtractor
from analysis.pead_analyzer import PEADAnalyzer       # Your existing file
from analysis.confirmation_scorer import ConfirmationScorer  # Your existing file
from notifier_telegram import send_telegram_alert

# State file to track already processed announcements (to avoid spam)
STATE_FILE = "state.json"

def get_processed_ids():
    try:
        with open(STATE_FILE, 'r') as f:
            return set(json.load(f).get('processed', []))
    except:
        return set()

def save_processed_id(filing_id):
    existing = get_processed_ids()
    existing.add(filing_id)
    with open(STATE_FILE, 'w') as f:
        json.dump({'processed': list(existing)}, f)

def run_pead_cycle():
    db = AnnouncementDB()
    watcher = BSEWatcher()
    processed_ids = get_processed_ids()
    
    print(f"[{datetime.now()}] Fetching new announcements...")
    announcements = watcher.get_financial_results()  # Returns list of dicts
    
    candidates = []
    
    for ann in announcements[:30]:  # Process latest 30 to save time
        filing_id = ann.get('id') or ann.get('pdf_url')  # Unique identifier
        
        if filing_id in processed_ids:
            continue  # Already processed, skip
            
        try:
            # 1. Download & Parse PDF
            pdf_path = watcher.download_pdf(ann['pdf_url'])  # Assuming download function exists
            extractor = FinancialExtractor(pdf_path)
            current_q_fin = extractor.extract_standalone_numbers()
            
            if not current_q_fin:
                continue  # PDF parse nahi hua toh skip
                
            # 2. Fetch Historical Data (Last 8 quarters)
            hist_df = db.get_history(ann['symbol'])
            if hist_df.empty:
                continue
                
            # 3. Run PEAD Fundamental Analyzer (Your existing module)
            pead_obj = PEADAnalyzer(current_q_fin, hist_df)
            fundamental_score = pead_obj.calculate_score()  # Assume returns dict

            # 4. Run Confirmation Scorer (Your existing module)
            # Isko price/volume data chahiye. Maan lo ann dict mein `close_price`, `volume` hai.
            conf_obj = ConfirmationScorer(ann.get('close_price'), ann.get('volume'), ann.get('avg_volume'))
            confirmation_score = conf_obj.get_score()  # Assume returns int

            # 5. Final PEAD Score (Combine both)
            # Agar aapka pead_analyzer already 100-point de raha hai, toh confirmation ko weight do.
            # Example: 80% Fundamental + 20% Confirmation
            final_score = (fundamental_score['total_score'] * 0.8) + (confirmation_score * 0.2)
            
            # 6. Liquidity Filter (Check from DB)
            liquidity = db.get_liquidity(ann['symbol'])
            if liquidity < 5_00_00_000:  # Less than 5 Crore avg delivery, reject
                print(f"Skipping {ann['symbol']} due to low liquidity")
                continue

            candidates.append({
                'symbol': ann['symbol'],
                'company': ann['company'],
                'score': round(final_score, 2),
                'action': 'BUY' if final_score >= 70 else 'WATCH' if final_score >= 50 else 'AVOID',
                'fundamental': fundamental_score,
                'confirmation': confirmation_score
            })
            
            # Mark as processed so it never alerts again
            save_processed_id(filing_id)
            
        except Exception as e:
            print(f"Error processing {ann.get('symbol')}: {e}")
            continue

    # Final Ranking: Top 10 by Score
    top_10 = sorted(candidates, key=lambda x: x['score'], reverse=True)[:10]
    
    # Send Notification
    if top_10:
        msg = f"📈 *Top 10 PEAD Stocks for this Quarter*\n"
        msg += f"🕒 {datetime.now().strftime('%d-%b %I:%M %p')}\n\n"
        for i, stock in enumerate(top_10, 1):
            msg += f"{i}. *{stock['company']}* ({stock['symbol']})\n"
            msg += f"   Score: {stock['score']} | Action: {stock['action']}\n"
            msg += f"   └─ Fund: {stock['fundamental'].get('total_score',0)} | Conf: {stock['confirmation']}\n\n"
        
        send_telegram_alert(msg)
        print("Alert sent successfully!")
    else:
        print("No fresh high-quality PEAD candidates found.")

if __name__ == "__main__":
    run_pead_cycle()  # Pehle manually test karo
