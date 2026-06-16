# scheduler.py
from apscheduler.schedulers.blocking import BlockingScheduler
from main import run_pead_cycle
import logging

logging.basicConfig(level=logging.INFO)

sched = BlockingScheduler()

# Market hours mein har 30 minute chalega (9:15 AM se 3:30 PM)
sched.add_job(run_pead_cycle, 'cron', day_of_week='mon-fri', hour='9-15', minute='*/30')

if __name__ == "__main__":
    print("PEAD Agent is live and waiting for results...")
    sched.start()
