import os
from datetime import datetime

# ==================== DATABASE ====================
DB_PATH = "data/announcements.db"
DB_CHECK_INTERVAL = 5

# ==================== TELEGRAM ====================
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # Apna token yahan dalna
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID_HERE"      # Apna chat ID yahan dalna

# ==================== SCRAPING ====================
POLLING_INTERVAL = 30
REQUEST_TIMEOUT = 20

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# ==================== URLS ====================
BSE_ANNOUNCEMENTS_URL = "https://www.bseindia.com/corporates/ann.html"
NSE_ANNOUNCEMENTS_URL = "https://www.nseindia.com/corporate/board_meetings.html"

# ==================== KEYWORDS ====================
RESULT_KEYWORDS = [
    "financial results",
    "quarterly results",
    "annual results",
    "audited results",
    "unaudited results",
    "q1 results", "q2 results", "q3 results", "q4 results",
    "standalone results",
    "consolidated results",
    "earnings",
    "outcome of board meeting",
    "investor presentation",
    "press release",
]

FOCUS_COMPANIES = [
    "RELIANCE", "TCS", "INFOSYS", "HDFCBANK", "ICICIBANK", "SBIN",
    "LT", "ITC", "BHARTI", "AXISBANK", "KOTAKBANK", "MARUTI",
    "SUNPHARMA", "M&M", "ULTRACEMCO", "HCLTECH", "WIPRO", "TITAN",
    "BAJFINANCE", "NTPC", "POWERGRID", "ONGC", "COALINDIA",
    "ASIANPAINT", "HINDUNILVR"
]

# ==================== LOGGING ====================
LOG_FILE = "logs/watcher.log"
os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)
os.makedirs("data/downloads", exist_ok=True)
