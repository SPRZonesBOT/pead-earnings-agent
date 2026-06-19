# scheduler.py
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
from main import run_pead_cycle

logging.basicConfig(level=logging.INFO)

sched = BlockingScheduler()

# ----- Quick scan every 30 min during market hours (IST 9:15 to 15:15) -----
sched.add_job(
    run_pead_cycle,
    trigger=CronTrigger(day_of_week='mon-fri', hour='9-15', minute='*/30'),
    id='quick_scan',
    replace_existing=True,
    kwargs={'reset': False, 'scan_mode': 'quick'}
)

# ----- Full scan at 16:30 IST (after market close) -----
sched.add_job(
    run_pead_cycle,
    trigger=CronTrigger(day_of_week='mon-fri', hour=16, minute=30),
    id='full_scan',
    replace_existing=True,
    kwargs={'reset': False, 'scan_mode': 'full'}
)

# ----- Full scan with reset at market open (9:15) -----
sched.add_job(
    run_pead_cycle,
    trigger=CronTrigger(day_of_week='mon-fri', hour=9, minute=15),
    id='full_reset',
    replace_existing=True,
    kwargs={'reset': True, 'scan_mode': 'full'}
)

# ----- Auto‑shutdown job at 16:45 IST (after full scan) -----
sched.add_job(
    lambda: sched.shutdown(wait=False),
    trigger=CronTrigger(day_of_week='mon-fri', hour=16, minute=45),
    id='shutdown',
    replace_existing=True
)

print("🚀 PEAD Scheduler started.")
print("   - Quick scan (Nifty 50) every 30 min during market hours")
print("   - Full scan (280 stocks) at 4:30 PM daily")
print("   - Full scan with reset at market open (9:15 AM)")
print("   - Auto-shutdown at 4:45 PM IST")
print("Press Ctrl+C to stop manually.")

try:
    sched.start()
except (KeyboardInterrupt, SystemExit):
    print("⏹️ Scheduler stopped.")
