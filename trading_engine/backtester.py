"""Backtester — replay historical bars through a strategy and score it.

At each bar:
    1. Give the price to strategy.on_market_data() and see if it emits an order.
    2. If it does, simulate a fill at that price with a proportional fee.
    3. Snapshot portfolio_value = cash + position × price.

At the end, report total return, number of trades, fees paid, and max drawdown.
"""


class Backtester:
    """A minimal event-driven backtester.

    fee_per_trade is a fraction of each trade's value (0.001 = 0.1%), not a
    flat dollar fee. position_qty can go negative: the backtester acts on
    every signal, so a SELL with no shares held opens a short.
    """

    def __init__(self, strategy, starting_cash=100_000.0, fee_per_trade=0.001):
        self.strategy = strategy
        self.starting_cash = starting_cash
        self.fee_per_trade = fee_per_trade
        self.reset()

    def reset(self):
        self.cash = self.starting_cash
        self.position_qty = 0
        self.equity_curve = []  # list of (timestamp, portfolio_value)
        self.trade_log = []     # list of dicts: {ts, side, qty, price, fee}
        self.total_fees = 0.0

    def run(self, price_data):
        self.reset()
        for symbol, price, ts in price_data:
            order = self.strategy.on_market_data(symbol, price, ts)
            if order is not None:
                self._fill(order, price, ts)
            value = self.cash + self.position_qty * price
            self.equity_curve.append((ts, value))

    def _fill(self, order, price, ts):
        fee = price * order.quantity * self.fee_per_trade
        self.total_fees += fee
        if order.side == "BUY":
            self.cash -= price * order.quantity + fee
            self.position_qty += order.quantity
        else:
            self.cash += price * order.quantity - fee
            self.position_qty -= order.quantity
        self.trade_log.append({
            "timestamp": ts, "side": order.side,
            "quantity": order.quantity, "price": price, "fee": fee,
        })

    def max_drawdown(self):
        if not self.equity_curve:
            return 0.0
        peak, worst = self.equity_curve[0][1], 0.0
        for _, v in self.equity_curve:
            peak = max(peak, v)
            worst = min(worst, (v - peak) / peak)
        return worst


    def total_return(self):
        """(final_value / starting_cash) − 1, or 0.0 if the run is empty."""
        if not self.equity_curve:
            return 0.0
        final_value = self.equity_curve[-1][1]
        return final_value / self.starting_cash - 1

    def print_report(self):
        """One-line-per-metric text summary."""
        if not self.equity_curve:
            print("Backtest hasn't been run.")
            return
        final = self.equity_curve[-1][1]
        dd = self.max_drawdown()
        print(f"Starting cash:    ${self.starting_cash:,.2f}")
        print(f"Ending value:     ${final:,.2f}")
        print(f"Total return:     {self.total_return() * 100:+.2f}%")
        print(f"Trades:           {len(self.trade_log)}")
        print(f"Fees paid:        ${self.total_fees:,.2f}")
        print(f"Max drawdown:     {(dd or 0.0) * 100:+.2f}%")
