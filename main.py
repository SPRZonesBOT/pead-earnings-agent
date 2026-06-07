import logging
import time
from database.db import db  # Aapka sahi DB import
from announcements.watcher_bse import get_bse_announcements
from announcements.watcher_nse import get_nse_announcements

# ----------------------------
# Logging Setup (Terminal mein clear output dekhne ke liye)
# ----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    logger.info("🚀 Starting PEAD Earnings Agent...")

    # 1️⃣ Fetch BSE Announcements
    logger.info("Fetching BSE Announcements...")
    bse_data = get_bse_announcements()
    logger.info(f"✅ Total BSE Announcements found: {len(bse_data)}")

    # 2️⃣ Fetch NSE Announcements
    logger.info("Fetching NSE Announcements...")
    nse_data = get_nse_announcements()
    logger.info(f"✅ Total NSE Announcements found: {len(nse_data)}")

    # 3️⃣ Combine Data
    all_announcements = bse_data + nse_data

    if not all_announcements:
        logger.warning("⚠️ No new announcements found right now.")
        return

    logger.info(f"📊 Processing {len(all_announcements)} total announcements...")
    
    # Print the fetched data cleanly
    print("\n" + "="*80)
    print(f"{'SOURCE':<6} | {'DATE':<12} | {'COMPANY':<20} | SUBJECT")
    print("="*80)
    
    for ann in all_announcements:
        # Company name agar lamba ho toh cut kar do display ke liye
        company = ann['company'][:18] + ".." if len(ann['company']) > 20 else ann['company']
        
        print(f"{ann['source']:<6} | {ann['date']:<12} | {company:<20} | {ann['subject']}")
        
        # -------------------------------------------------------------
        # 💾 DATABASE MEIN SAVE KARNE KA LOGIC (Yahan add karein)
        # -------------------------------------------------------------
        # Example:
        # try:
        #     db.collection.insert_one(ann)  # Agar MongoDB hai
        #     # ya
        #     # db.execute("INSERT INTO...", (ann['date'], ...)) # Agar SQL hai
        # except Exception as e:
        #     logger.error(f"DB Save Error: {e}")

    print("="*80)
    logger.info("🎉 Task completed successfully!")

if __name__ == "__main__":
    # Script ko ek baar run karne ke liye:
    main()

    # (Optional) Agar aapko isko har 1 ghante (3600 sec) mein auto-run karna hai, toh upar wali line hata kar neeche wala code use karein:
    # while True:
    #     main()
    #     logger.info("Waiting for 1 hour before next fetch...")
    #     time.sleep(3600)
