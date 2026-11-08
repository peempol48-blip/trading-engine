"""Strategy — the brain that turns prices into orders."""

from trading_engine.order import Order


class Strategy:
    """Base class: override on_market_data() in a subclass.

    Return an Order to trade, or None to do nothing on this bar.
    """

    def on_market_data(self, symbol, price, timestamp=None):
        return None


class MovingAverageCrossover(Strategy):
    """Buy when the short MA crosses ABOVE the long MA; sell on the reverse.

    Attributes:
        short_window: number of prices in the fast average (default 5)
        long_window:  number of prices in the slow average  (default 20)
        quantity:     shares per trade (default 100)
        prices:       rolling list of closes seen so far
        prev_short:   previous bar's short MA (None until the first MA bar)
        prev_long:    previous bar's long MA  (None until the first MA bar)

    Signals come purely from the crosses — a SELL can be the very first
    signal, even if the strategy has never bought.
    """

    def __init__(self, short_window=5, long_window=20, quantity=100):
        self.short_window = short_window
        self.long_window = long_window
        self.quantity = quantity
        self.prices = []
        self.prev_short = None
        self.prev_long = None

    def on_market_data(self, symbol, price, timestamp=None):
        self.prices.append(price)
        if len(self.prices) < self.long_window:
            return None

        short = sum(self.prices[-self.short_window:]) / self.short_window
        long_ = sum(self.prices[-self.long_window:])  / self.long_window

        order = None
        if self.prev_short is not None:
            if self.prev_short <= self.prev_long and short > long_:
                order = Order(f"{symbol}-{len(self.prices)}",
                            symbol, "BUY", self.quantity, price)
            elif self.prev_short >= self.prev_long and short < long_:
                order = Order(f"{symbol}-{len(self.prices)}",
                            symbol, "SELL", self.quantity, price)

        self.prev_short, self.prev_long = short, long_
        return order
