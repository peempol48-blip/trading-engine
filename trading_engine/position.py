"""Position — how many shares you own, at what price, and what you've made.

The two P&L numbers to keep straight:

    realized_pnl    — profit locked in by closing (selling) shares
    unrealized_pnl  — paper profit on shares you still hold, at today's price
"""


class Position:
    """A running position in a single symbol.

    Attributes:
        symbol:              e.g. 'AAPL'
        quantity:            shares held (long-only: never sell more than
                             you hold, so this never goes below 0)
        average_entry_price: weighted-average cost of the shares you still hold
        realized_pnl:        cumulative profit from closed trades
    """

    def __init__(self, symbol):
        self.symbol = symbol
        self.quantity = 0
        self.average_entry_price = 0.0
        self.realized_pnl = 0.0

    def update(self, fill_quantity, fill_price):
        if fill_quantity > 0:  # BUY branch (Step 8)
            if self.quantity == 0:
                self.average_entry_price = fill_price
            else:
                self.average_entry_price = (
                    (self.quantity * self.average_entry_price
                    + fill_quantity * fill_price)
                    / (self.quantity + fill_quantity)
                )
            self.quantity += fill_quantity
        else:  # SELL
            self.realized_pnl += (
                fill_price - self.average_entry_price
            ) * abs(fill_quantity)

            self.quantity += fill_quantity

    def unrealized_pnl(self, current_price):
        return (current_price - self.average_entry_price) * self.quantity

    def market_value(self, current_price):
        return abs(self.quantity) * current_price

    def __repr__(self):
        return (
            f"Position({getattr(self, 'symbol', '?')}, "
            f"qty={getattr(self, 'quantity', '?')}, "
            f"avg={getattr(self, 'average_entry_price', '?')}, "
            f"realized={getattr(self, 'realized_pnl', '?')})"
        )
