"""RiskManager — the guardrails that sit in front of every order.

Three limits, checked in order:

    1. Position limit  — no single symbol can grow past max_position_size shares
    2. Exposure limit  — Σ |quantity| × price across the book ≤ max_total_exposure
    3. Daily-loss halt — no new orders once today's P&L is below −max_daily_loss

Every decision (approve / reject + reason) is appended to self.log for
compliance-style auditing.
"""

from datetime import datetime


class RiskManager:
    """Pre-trade risk checks with an audit trail."""

    def __init__(self, max_position_size, max_total_exposure, max_daily_loss):
        self.max_position_size = max_position_size
        self.max_total_exposure = max_total_exposure
        self.max_daily_loss = max_daily_loss
        self.log = []

    def check_position_limit(self, current_quantity, order_quantity):
        return abs(current_quantity + order_quantity) <= self.max_position_size

    def check_exposure_limit(self, positions, current_prices):
        total = 0.0
        for sym, pos in positions.items():
            if sym in current_prices:
                total += abs(pos.quantity) * current_prices[sym]
        return total <= self.max_total_exposure


    def check_daily_loss(self, current_daily_pnl):
        return current_daily_pnl >= -self.max_daily_loss

    def check_order(self, order, position_manager, current_prices, daily_pnl):
    # 1. Position limit
        existing = position_manager.get_position(order.symbol)
        current_qty = existing.quantity if existing else 0
        signed_qty = order.quantity if order.side == "BUY" else -order.quantity
        if not self.check_position_limit(current_qty, signed_qty):
            return self._record(order, False, "position limit")

        # 2. Exposure limit
        if not self.check_exposure_limit(position_manager.positions, current_prices):
            return self._record(order, False, "exposure limit")

        # 3. Daily loss halt
        if not self.check_daily_loss(daily_pnl):
            return self._record(order, False, "daily loss")

        return self._record(order, True, None)

    def _record(self, order, approved, reason):
        self.log.append({
            "timestamp": datetime.now(),
            "order_id": order.order_id,
            "approved": approved,
            "reason": reason,
        })
        return approved, reason

