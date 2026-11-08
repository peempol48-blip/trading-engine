"""MarketDataFeed — replay a CSV of historical bars through the event bus."""

import csv

from trading_engine.events import MarketDataEvent


class MarketDataFeed:
    """A file-backed market data source.

    Loads a CSV with columns:  symbol, timestamp, open, high, low, close, volume
    """

    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.data = []
        self.latest_prices = {}
        self.price_history = {}

    def load_csv(self, filepath):
        with open(filepath) as f:
            for i, row in enumerate(csv.DictReader(f), start=1):
                try:
                    row["open"]   = float(row["open"])
                    row["high"]   = float(row["high"])
                    row["low"]    = float(row["low"])
                    row["close"]  = float(row["close"])
                    row["volume"] = int(row["volume"])
                except (KeyError, ValueError):
                    print(f"Skipping invalid row {i}")
                    continue
                self.data.append(row)

    def simulate_feed(self):
        for row in self.data:
            symbol = row["symbol"]
            
            self.event_bus.publish(MarketDataEvent(data=row))
            self.latest_prices[symbol] = row["close"]
            self.price_history.setdefault(symbol, []).append(row["close"])

    

    def get_latest_price(self, symbol):
        """Return the last close for `symbol`, or None."""
        return self.latest_prices.get(symbol) if hasattr(self, "latest_prices") else None

    def get_price_history(self, symbol, n_periods=None):
        """Return the price history for `symbol` (optionally last N)."""
        history = getattr(self, "price_history", {}).get(symbol, [])
        return history[-n_periods:] if n_periods else list(history)
