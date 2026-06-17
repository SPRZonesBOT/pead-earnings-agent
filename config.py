# config.py
import os

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8944262472:AAF8IOk8si-_hMNxvRs588evNZWe1gEwQ_o')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '1715733436')

# Data sources
PREFER_SCREENER = True
ENABLE_PRICE_FETCH = True
STOCKS_LIST = None  # None means use default list from screener_watcher

# Scoring
BUY_THRESHOLD = 70
WATCH_THRESHOLD = 50

# Liquidity filter (in INR)
MIN_LIQUIDITY = 5_00_00_000  # 5 Crore
