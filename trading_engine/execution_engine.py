"""ExecutionEngine — the heart of the engine.

Ties together the OrderBook, PositionManager, RiskManager and EventBus:

    submit_order()  → risk-check, add to book, publish, look for a match
    match_orders()  → cross the book: partial fills, price-time priority
"""

from trading_engine.events import (
    OrderCancelledEvent,
    OrderFilledEvent,
    OrderSubmittedEvent,
)


class ExecutionEngine:
    """Orchestrates order flow through the engine.

    daily_pnl is a scratch number you'd wire to the P&L blotter in
    production. For the risk check we pass it in explicitly.
    """

    def __init__(self, order_book, position_manager, risk_manager, event_bus):
        self.order_book = order_book
        self.position_manager = position_manager
        self.risk_manager = risk_manager
        self.event_bus = event_bus
        self.fills = []  # every OrderFilledEvent data payload, in order
        self.daily_pnl = 0.0

    def submit_order(self, order, current_prices=None):
        current_prices = current_prices or {}

        approved, reason = self.risk_manager.check_order(
            order, self.position_manager, current_prices, self.daily_pnl,
        )
        if not approved:
            order.status = "REJECTED"
            self.event_bus.publish(OrderCancelledEvent(data={
                "order_id": order.order_id, "reason": reason,
            }))
            return

        order.status = "ACTIVE"
        self.order_book.add_order(order)
        self.event_bus.publish(OrderSubmittedEvent(data={
            "order_id": order.order_id,
            "symbol": order.symbol,
            "side": order.side,
            "quantity": order.quantity,
            "price": order.price,
        }))

        self.match_orders(order.symbol)

    def match_orders(self, symbol):
        while True:
            bid = self.order_book.get_best_bid()
            ask = self.order_book.get_best_ask()
            if bid is None or ask is None or bid < ask:
                return

            buy = self.order_book.buy_orders[0]
            sell = self.order_book.sell_orders[0]

            fill_qty = min(buy.quantity, sell.quantity)
            fill_price = sell.price   # this engine always trades at the ask

            # Buyer +qty, seller −qty at fill_price — both in the SAME
            # PositionManager, so the two updates net out.
            self.position_manager.update_position(symbol, +fill_qty, fill_price)
            self.position_manager.update_position(symbol, -fill_qty, fill_price)

            # Reduce quantities on the two orders.
            buy.quantity -= fill_qty
            sell.quantity -= fill_qty

            for o in (buy, sell):
                if o.quantity == 0:
                    o.status = "FILLED"
                    self.order_book.remove_order(o.order_id)
                else:
                    o.status = "PARTIALLY_FILLED"

            fill_data = {
                "symbol": symbol,
                "price": fill_price,
                "quantity": fill_qty,
                "buy_order_id": buy.order_id,
                "sell_order_id": sell.order_id,
            }
            self.fills.append(fill_data)
            self.event_bus.publish(OrderFilledEvent(data=fill_data))
