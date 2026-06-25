name: PEAD Agent Scheduler

on:
  schedule:
    # Quick Scan: Har 30 min during market hours (IST 9:15 AM to 3:15 PM)
    - cron: '15 3,4,5,6,7,8,9 * * 1-5'
    - cron: '45 3,4,5,6,7,8 * * 1-5'
    # Full Scan: Daily at 4:30 PM IST (11:00 UTC)
    - cron: '0 11 * * 1-5'
  workflow_dispatch:

jobs:
  run-pead:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.10'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        # Explicitly install scipy if requirements.txt doesn't have it
        pip install scipy

    - name: Run PEAD Quick Scan
      if: github.event.schedule == '15 3,4,5,6,7,8,9 * * 1-5' || github.event.schedule == '45 3,4,5,6,7,8 * * 1-5'
      run: python main.py --scan-mode quick
      env:
        TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
        TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}

    - name: Run PEAD Full Scan
      if: github.event.schedule == '0 11 * * 1-5'
      run: python main.py --scan-mode full
      env:
        TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
        TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
