"""
Trading Engine — entry point.

Press Run (or Cmd/Ctrl+Enter) to execute this file. As you complete steps,
you'll orchestrate the full pipeline here: the event bus, the order book,
positions, risk checks, execution, market data, a strategy, and finally a
backtest that pushes charts into the Analytics panel via the `quantt` module.
"""

from trading_engine import ENGINE_NAME
from trading_engine.event_bus import EventBus
from trading_engine.events import MarketDataEvent

from trading_engine.position_manager import PositionManager


#1
bus = EventBus()

bus.subscribe(
    "MARKET_DATA",
    lambda e: print("tick:", e.data)
)

bus.publish(
    MarketDataEvent(
        data={"symbol": "AAPL", "price": 150.0}
    )
)
#2

pm = PositionManager()

pm.update_position("AAPL", 100, 150.0)
pm.update_position("MSFT", 50, 340.0)
pm.update_position("AAPL", -50, 160.0)

print("Total P&L:", pm.get_total_pnl({
    "AAPL": 165.0,
    "MSFT": 350.0
}))
#3
from trading_engine.event_bus import EventBus
from trading_engine.market_data import MarketDataFeed

bus = EventBus()
feed = MarketDataFeed(bus)
feed.load_csv("data/prices.csv")
print(len(feed.data), "bars loaded")

feed.simulate_feed()
print("Latest AAPL:", feed.get_latest_price("AAPL"))
print("Last 5:", feed.get_price_history("AAPL", 5))



import csv
import quantt

from trading_engine import ENGINE_NAME
from trading_engine.backtester import Backtester
from trading_engine.strategy import MovingAverageCrossover


def load_bars(path="data/prices.csv"):
    bars = []
    with open(path) as f:
        for row in csv.DictReader(f):
            bars.append((row["symbol"], float(row["close"]), row["timestamp"]))
    return bars


def main():
    print(f"📈  {ENGINE_NAME} running backtest…")
    bars = load_bars()
    strategy = MovingAverageCrossover(short_window=5, long_window=20, quantity=100)
    bt = Backtester(strategy, starting_cash=100_000, fee_per_trade=0.001)
    bt.run(bars)

    print()
    bt.print_report()

    # Metrics
    quantt.metric("Starting cash",  bt.starting_cash,                 format="currency")
    quantt.metric("Ending value",   bt.equity_curve[-1][1],            format="currency")
    quantt.metric("Total return",   bt.total_return(),                 format="percent")
    quantt.metric("Trades",         float(len(bt.trade_log)))
    quantt.metric("Max drawdown",   bt.max_drawdown(),                 format="percent")

    # Equity curve
    quantt.line(
        {"x": [ts for ts, _ in bt.equity_curve],
         "Equity": [v for _, v in bt.equity_curve]},
        title="Backtest equity curve",
        format="currency",
    )

    # Price with the moving averages we traded on
    closes = [p for _, p, _ in bars]
    dates = [ts for _, _, ts in bars]
    def rolling(x, w):
        out = [None] * (w - 1)
        for i in range(w - 1, len(x)):
            out.append(sum(x[i - w + 1: i + 1]) / w)
        return out
    quantt.line(
        {"x": dates, "Price": closes,
         "SMA-5": rolling(closes, 5), "SMA-20": rolling(closes, 20)},
        title="AAPL: price and moving averages",
        format="currency",
    )

    # Trade cash impact bars (one per fill, buys negative, sells positive)
    quantt.bar(
        [t["timestamp"] for t in bt.trade_log],
        [(-1 if t["side"] == "BUY" else 1) * t["quantity"] * t["price"] for t in bt.trade_log],
        title="Trade cash impact (positive = sell proceeds)",
        format="currency",
    )


if __name__ == "__main__":
    main()
