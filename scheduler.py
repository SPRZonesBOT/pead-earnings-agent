# scheduler.py
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
from main import run_pead_cycle
import config

logging.basicConfig(level=logging.INFO)

sched = BlockingScheduler()

# ----- Quick Scan (Nifty 50) during market hours: 9:15 AM - 3:30 PM, every 30 min -----
# Run at 9:15, 9:45, 10:15, ... 15:15 (3:15 PM)
sched.add_job(
    run_pead_cycle,
    trigger=CronTrigger(
        day_of_week='mon-fri',
        hour='9-15',
        minute='*/30'
    ),
    id='quick_scan',
    replace_existing=True,
    kwargs={
        'reset': False,
        'force_mock': False,
        'no_real': False,
        'scan_mode': 'quick'
    }
)

# ----- Full Scan (All 280 stocks) after market close: 4:30 PM daily -----
sched.add_job(
    run_pead_cycle,
    trigger=CronTrigger(
        day_of_week='mon-fri',
        hour=16,
        minute=30
    ),
    id='full_scan',
    replace_existing=True,
    kwargs={
        'reset': False,
        'force_mock': False,
        'no_real': False,
        'scan_mode': 'full'
    }
)

# Also run full scan once at market open (9:15 AM) with reset to process fresh results
sched.add_job(
    run_pead_cycle,
    trigger=CronTrigger(day_of_week='mon-fri', hour=9, minute=15),
    id='market_open_full',
    replace_existing=True,
    kwargs={
        'reset': True,
        'force_mock': False,
        'no_real': False,
        'scan_mode': 'full'
    }
)

if __name__ == "__main__":
    print("🚀 PEAD Scheduler started.")
    print("   - Quick scan (Nifty 50) every 30 min during market hours")
    print("   - Full scan (280 stocks) at 4:30 PM daily")
    print("   - Full scan at market open (9:15 AM) with reset")
    print("Press Ctrl+C to stop.")
    try:
        sched.start()
    except KeyboardInterrupt:
        print("⏹️ Scheduler stopped.")
