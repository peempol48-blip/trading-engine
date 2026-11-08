"""The Order class — a single buy or sell instruction.

An order carries everything the engine needs to decide what to do:
symbol, side, quantity, a price (for LIMIT), and a type (LIMIT vs MARKET).
Its status changes as it moves through the pipeline.
"""

from datetime import datetime


class Order:
    """A single buy or sell instruction.

    Attributes:
        order_id:   unique string identifier
        symbol:     e.g. 'AAPL'
        side:       'BUY' or 'SELL'
        quantity:   integer number of shares
        price:      limit price (float); ignored for MARKET orders
        order_type: 'LIMIT' or 'MARKET'
        timestamp:  when the order was created
        status:     'PENDING' → 'ACTIVE' → 'FILLED'/'PARTIALLY_FILLED'/'REJECTED'
    """

    def __init__(self, order_id, symbol, side, quantity, price, order_type="LIMIT", timestamp=None):
        self.order_id = order_id
        self.symbol = symbol
        self.side = side
        self.quantity = quantity
        self.price = price
        self.order_type = order_type
        self.timestamp = timestamp if timestamp is not None else datetime.now()
        self.status = "PENDING"

    def __repr__(self):
        return (
            f"Order({getattr(self, 'order_id', '?')}, "
            f"{getattr(self, 'side', '?')} {getattr(self, 'quantity', '?')} "
            f"{getattr(self, 'symbol', '?')} @ {getattr(self, 'price', '?')}, "
            f"{getattr(self, 'status', '?')})"
        )
