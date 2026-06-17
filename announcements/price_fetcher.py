# announcements/price_fetcher.py
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

class PriceFetcher:
    def __init__(self):
        pass

    def get_price_confirmation(self, symbol, announcement_date=None):
        """
        Fetch price before and after announcement to compute return.
        Returns:
            - price_before: price on announcement day (or day before)
            - price_after: price 5 days after announcement
            - return_pct: percentage change
        """
        try:
            ticker = yf.Ticker(f"{symbol}.NS")
            # Get historical data for last 30 days
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            hist = ticker.history(start=start_date, end=end_date)
            if hist.empty:
                return None

            # If announcement_date is given, use it; else use the latest available date
            if announcement_date:
                # Convert to datetime
                try:
                    ann_date = pd.to_datetime(announcement_date, format='%d-%b-%Y')
                except:
                    ann_date = pd.to_datetime(announcement_date)
                # Find the closest trading day on or before announcement date
                hist.index = pd.to_datetime(hist.index)
                price_before = None
                # Find the row with date <= ann_date
                mask = hist.index <= ann_date
                if mask.any():
                    price_before = hist.loc[hist.index[mask].max(), 'Close']
            else:
                # Use last available close as "before" (current price)
                price_before = hist['Close'].iloc[-1]

            # Get price 5 days after announcement (or last available if less)
            if price_before is not None:
                # Find the date 5 days after announcement
                if announcement_date:
                    after_date = ann_date + timedelta(days=5)
                else:
                    after_date = hist.index[-1]  # today
                # Find the closest trading day after after_date
                mask_after = hist.index >= after_date
                if mask_after.any():
                    price_after = hist.loc[hist.index[mask_after].min(), 'Close']
                else:
                    price_after = hist['Close'].iloc[-1]

                if price_before > 0:
                    return_pct = ((price_after - price_before) / price_before) * 100
                    return {
                        'price_before': price_before,
                        'price_after': price_after,
                        'return_pct': return_pct,
                        'price_available': True
                    }
            return None
        except Exception as e:
            print(f"  Price fetch error for {symbol}: {e}")
            return None
