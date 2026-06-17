# config.py
import os

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', 'YOUR_CHAT_ID')

# Data sources
PREFER_SCREENER = True
ENABLE_PRICE_FETCH = True
STOCKS_LIST = None  # None means use default list from screener_watcher

# Scoring
BUY_THRESHOLD = 70
WATCH_THRESHOLD = 50

# Liquidity filter (in INR)
MIN_LIQUIDITY = 5_00_00_000  # 5 Crore
