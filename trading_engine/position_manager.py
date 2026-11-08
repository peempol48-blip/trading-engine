"""PositionManager — one Position per symbol, plus portfolio-wide P&L."""

from trading_engine.position import Position


class PositionManager:
    """A dictionary of {symbol: Position}."""

    def __init__(self):
        self.positions = {}

    def update_position(self, symbol, fill_quantity, fill_price):
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol)
        self.positions[symbol].update(fill_quantity, fill_price)

    def get_position(self, symbol):
        return self.positions.get(symbol)

    def get_total_pnl(self, current_prices):
        total = 0.0
        for symbol, pos in self.positions.items():
            total += pos.realized_pnl
            if symbol in current_prices:
                total += pos.unrealized_pnl(current_prices[symbol])
        return total
