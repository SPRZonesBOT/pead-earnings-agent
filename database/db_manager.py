# database/db_manager.py
import sqlite3
import pandas as pd
import os

class AnnouncementDB:
    def __init__(self, db_path="pead_data.db"):
        """Initialize SQLite database connection"""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self._create_tables()
        
    def _create_tables(self):
        """Create required tables if they don't exist"""
        cursor = self.conn.cursor()
        
        # Historical quarterly results table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quarterly_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                quarter TEXT,
                revenue REAL,
                pat REAL,
                ebitda REAL,
                eps REAL,
                ebitda_margin REAL,
                pat_margin REAL,
                debt_to_equity REAL,
                roce REAL,
                operating_cash_flow REAL,
                UNIQUE(symbol, quarter)
            )
        ''')
        
        # Liquidity table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS liquidity (
                symbol TEXT PRIMARY KEY,
                avg_delivery_value REAL,
                avg_volume REAL,
                market_cap REAL
            )
        ''')
        
        self.conn.commit()
        
    def get_history(self, symbol, quarters=8):
        """Fetch last N quarters for a symbol"""
        query = f"""
            SELECT * FROM quarterly_results 
            WHERE symbol = '{symbol}' 
            ORDER BY quarter DESC 
            LIMIT {quarters}
        """
        return pd.read_sql(query, self.conn)
        
    def get_liquidity(self, symbol):
        """Fetch average daily traded value (in INR)"""
        cursor = self.conn.cursor()
        cursor.execute(f"SELECT avg_delivery_value FROM liquidity WHERE symbol = '{symbol}'")
        result = cursor.fetchone()
        if result:
            return result[0]
        return 0  # Default: 0 liquidity (will be filtered out)
    
    def save_quarterly(self, symbol, quarter, data):
        """Save quarterly results to database"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO quarterly_results 
            (symbol, quarter, revenue, pat, ebitda, eps, ebitda_margin, pat_margin, 
             debt_to_equity, roce, operating_cash_flow)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            symbol, quarter,
            data.get('revenue'), data.get('pat'), data.get('ebitda'),
            data.get('eps'), data.get('ebitda_margin'), data.get('pat_margin'),
            data.get('debt_to_equity'), data.get('roce'), data.get('operating_cash_flow')
        ))
        self.conn.commit()
        
    def close(self):
        self.conn.close()
