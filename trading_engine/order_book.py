"""The OrderBook — two sorted lists of resting orders.

Buyers descending (highest bid first), sellers ascending (lowest ask first).
The top of each list is the "best" price on that side. Because Python's
sort is stable, orders that arrive at the same price keep their arrival
order — this is called "price-time priority" and it matters for fairness.

One book per symbol. An OrderBook holds the resting orders for a single
instrument — that's why it doesn't carry a `symbol` attribute (each Order
does). A multi-symbol exchange keeps a `dict[str, OrderBook]` and routes
each incoming order to the right book by `order.symbol`. This engine trades
a single symbol (AAPL), so we hold one book directly.
"""


class OrderBook:
    """A sorted book of resting limit orders for a single symbol."""

    def __init__(self):
        self.buy_orders = []
        self.sell_orders = []

    def add_order(self, order):
        if order.side == "BUY":
            self.buy_orders.append(order)
            self.buy_orders.sort(key=lambda o: o.price, reverse=True)
        else:  # 'SELL'
            self.sell_orders.append(order)
            self.sell_orders.sort(key=lambda o: o.price)

    def get_best_bid(self):
        return self.buy_orders[0].price if self.buy_orders else None

    def get_best_ask(self):
        return self.sell_orders[0].price if self.sell_orders else None

    def get_spread(self):
        bid, ask = self.get_best_bid(), self.get_best_ask()
        return ask - bid if bid is not None and ask is not None else None

    def remove_order(self, order_id):
        for book_side in (self.buy_orders, self.sell_orders):
            for i, o in enumerate(book_side):
                if o.order_id == order_id:
                    return book_side.pop(i)
        return None

