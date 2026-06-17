# scheduler.py
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
from main import run_pead_cycle
import os

logging.basicConfig(level=logging.INFO)

# Set environment variables for Telegram if not set
# os.environ['TELEGRAM_BOT_TOKEN'] = 'your_token'
# os.environ['TELEGRAM_CHAT_ID'] = 'your_chat_id'

sched = BlockingScheduler()

# Run every 30 minutes during market hours (9:15 AM to 3:30 PM IST)
# Use cron: Mon-Fri, 9:15-15:30, every 30 min
sched.add_job(
    run_pead_cycle,
    trigger=CronTrigger(
        day_of_week='mon-fri',
        hour='9-15',
        minute='*/30'
    ),
    id='pead_job',
    replace_existing=True,
    kwargs={'reset': False, 'force_mock': False, 'no_real': False}
)

# Also run once at market open (9:15)
sched.add_job(
    run_pead_cycle,
    trigger=CronTrigger(day_of_week='mon-fri', hour=9, minute=15),
    id='pead_open',
    replace_existing=True,
    kwargs={'reset': True, 'force_mock': False, 'no_real': False}
)

if __name__ == "__main__":
    print("🚀 PEAD Scheduler started. Press Ctrl+C to exit.")
    try:
        sched.start()
    except KeyboardInterrupt:
        print("⏹️ Scheduler stopped.")
