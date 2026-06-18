# scheduler.py
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
from main import run_pead_cycle

logging.basicConfig(level=logging.INFO)

sched = BlockingScheduler()

# Quick scan every 30 min during market hours (IST 9:15-15:15)
sched.add_job(
    run_pead_cycle,
    trigger=CronTrigger(day_of_week='mon-fri', hour='9-15', minute='*/30'),
    id='quick_scan',
    kwargs={'scan_mode': 'quick', 'reset': False}
)

# Full scan at 16:30 IST daily
sched.add_job(
    run_pead_cycle,
    trigger=CronTrigger(day_of_week='mon-fri', hour=16, minute=30),
    id='full_scan',
    kwargs={'scan_mode': 'full', 'reset': False}
)

# Full scan with reset at market open (9:15)
sched.add_job(
    run_pead_cycle,
    trigger=CronTrigger(day_of_week='mon-fri', hour=9, minute=15),
    id='full_reset',
    kwargs={'scan_mode': 'full', 'reset': True}
)

print("🚀 Scheduler started. Quick (30min), Full (16:30), Open Reset (9:15).")
try:
    sched.start()
except KeyboardInterrupt:
    print("Stopped.")
