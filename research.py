"""Reproduce the next-open SMA and volatility-sizing experiment."""

import argparse
import csv
import math
import random
import statistics as stats
from collections import deque
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from trading_engine.strategy import MovingAverageCrossover


ROOT = Path(__file__).resolve().parent
MODELS = ("hold", "sma", "sma_vol")
CAPITAL = 100_000
SHARES = 100


@dataclass(frozen=True)
class Bar:
    day: date
    opening: float
    close: float
    dividend: float = 0
    rf_return: float = 0


def load_bars(path):
    bars = []
    symbol = None
    with path.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            current = row["symbol"].strip()
            if not current or (symbol is not None and symbol != current):
                raise ValueError("Supply one symbol per CSV")
            symbol = current
            bar = Bar(date.fromisoformat(row["timestamp"]), float(row["open"]),
                      float(row["close"]), float(row.get("dividend", 0)),
                      float(row.get("rf_return", 0)))
            if not all(map(math.isfinite, (bar.opening, bar.close, bar.dividend, bar.rf_return))):
                raise ValueError(f"Non-finite price or dividend at {bar.day}")
            if min(bar.opening, bar.close) <= 0 or (bars and bar.day <= bars[-1].day):
                raise ValueError(f"Invalid price or out-of-order date at {bar.day}")
            bars.append(bar)
    if not bars:
        raise ValueError("CSV has no bars")
    return bars, symbol


def close_signals(bars, symbol):
    """Base share targets and trailing vol known immediately after each close."""
    strategy = MovingAverageCrossover(5, 20, SHARES)
    window = deque(maxlen=20)
    position = 0
    targets, vols = [], []
    for i, bar in enumerate(bars):
        if i:
            window.append((bar.close + bar.dividend) / bars[i-1].close - 1)
        order = strategy.on_market_data(symbol, bar.close, bar.day)
        if order:
            position += order.quantity if order.side == "BUY" else -order.quantity
        targets.append(position)
        vols.append(stats.stdev(window) if len(window) == 20 else None)
    return targets, vols


@dataclass(frozen=True)
class Costs:
    commission_bps: float = 10
    slippage_bps: float = 5
    borrow_pct: float = 3

    def __post_init__(self):
        if any(not math.isfinite(x) or x < 0 for x in
               (self.commission_bps, self.slippage_bps, self.borrow_pct)):
            raise ValueError("Costs must be finite and nonnegative")
        if self.slippage_bps >= 10_000:
            raise ValueError("Slippage must be below 100%")


def calibration(bars, targets, vols, stop):
    observed = [v for v in vols[:stop] if v is not None]
    if len(observed) < 252:
        raise ValueError("Need at least 252 pre-test volatility observations")
    cutoff = stats.quantiles(observed, n=4, method="inclusive")[2]
    # Match training gross dollar exposure on average, using only lagged positions.
    hold = round(sum(abs(targets[i-1]) * bars[i].close for i in range(1, stop))
                 / sum(bar.close for bar in bars[1:stop]))
    return cutoff, hold


def simulate(bars, targets, vols, start, end, costs, refit_yearly):
    """Carry each account through the period. Every fill uses yesterday's target."""
    if not 0 < start < end <= len(bars):
        raise ValueError("Evaluation period must have training history and test rows")
    cash = dict.fromkeys(MODELS, float(CAPITAL))
    shares = dict.fromkeys(MODELS, 0)
    equity = cash.copy()
    records = []
    for i in range(start, end):
        bar, prev = bars[i], bars[i-1]
        if i == start or (refit_yearly and bar.day.year != prev.day.year):
            cutoff, hold = calibration(bars, targets, vols, i)
        base = targets[i-1]
        reduced = vols[i-1] is not None and vols[i-1] > cutoff
        desired = {"hold": hold, "sma": base, "sma_vol": base // 2 if reduced else base}
        for model, target in desired.items():
            old = shares[model]
            dividend = old * bar.dividend
            interest = cash[model] * bar.rf_return
            borrow = max(-old, 0) * prev.close * costs.borrow_pct / 100 * (bar.day-prev.day).days / 365
            delta = target - old
            slip = abs(delta) * bar.opening * costs.slippage_bps / 10_000
            fill = bar.opening * (1 + (int(delta > 0) - int(delta < 0)) * costs.slippage_bps / 10_000)
            commission = abs(delta) * fill * costs.commission_bps / 10_000
            cash[model] += interest + dividend - borrow - delta * fill - commission
            shares[model] = target
            value = cash[model] + target * bar.close
            if value <= 0:
                raise ValueError(f"{model} depleted capital on {bar.day}")
            daily_return = value / equity[model] - 1
            records.append(dict(day=bar.day, model=model, shares=target, delta=delta,
                                open=bar.opening, fill=fill if delta else None,
                                equity=value, daily_return=daily_return,
                                excess_return=daily_return-bar.rf_return, rf_return=bar.rf_return,
                                interest=interest, cash=cash[model],
                                commission=commission, slippage=slip, borrow=borrow,
                                dividend=dividend, gross_exposure=abs(target)*bar.close/value,
                                vol_cutoff=cutoff, previous_vol=vols[i-1], high_vol=reduced))
            equity[model] = value
    return records


def sharpe(returns):
    vol = stats.stdev(returns) if len(returns) >= 2 else 0
    return math.sqrt(252) * stats.mean(returns) / vol if vol > 1e-14 else None


def summarize(records):
    summary = []
    for model in MODELS:
        rows = [r for r in records if r["model"] == model]
        peak = CAPITAL
        drawdown = 0
        for row in rows:
            peak = max(peak, row["equity"])
            drawdown = min(drawdown, row["equity"] / peak - 1)
        cash_value = CAPITAL * math.prod(1+r["rf_return"] for r in rows)
        summary.append(dict(model=model, bars=len(rows), pnl=rows[-1]["equity"]-CAPITAL,
                            pnl_vs_cash=rows[-1]["equity"]-cash_value,
                            sharpe=sharpe([r["excess_return"] for r in rows]),
                            drawdown=drawdown, fills=sum(r["delta"] != 0 for r in rows),
                            cost=sum(r["commission"]+r["slippage"]+r["borrow"] for r in rows),
                            mean_exposure=stats.mean(r["gross_exposure"] for r in rows)))
    return summary


def paired_interval(records, repetitions=2000, block=20):
    """Paired circular block bootstrap of holdout daily returns, using prefix sums."""
    series = [[r["excess_return"] for r in records if r["model"] == model]
              for model in ("sma", "sma_vol")]
    n = len(series[0])
    if n < 2 * block:
        return None
    rng = random.Random(1701)
    prefixes = []
    for returns in series:
        sums, squares = [0.0], [0.0]
        for x in returns + returns:
            sums.append(sums[-1] + x)
            squares.append(squares[-1] + x*x)
        prefixes.append((sums, squares))
    deltas = []
    for _ in range(repetitions):
        totals, squared = [0.0, 0.0], [0.0, 0.0]
        for offset in range(0, n, block):
            a = rng.randrange(n)
            b = a + min(block, n-offset)
            for j, (sums, squares) in enumerate(prefixes):
                totals[j] += sums[b] - sums[a]
                squared[j] += squares[b] - squares[a]
        variances = [(ss - s*s/n)/(n-1) for s, ss in zip(totals, squared)]
        if min(variances) > 1e-28:
            s0, s1 = [math.sqrt(252/v)*s/n for v, s in zip(variances, totals)]
            deltas.append(s1 - s0)
    if len(deltas) < 2:
        return None
    q = stats.quantiles(deltas, n=40, method="inclusive")
    return q[0], q[-1]


def save_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def display(value):
    return "n/a" if value is None else f"{value:.3f}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data/aapl_research.csv")
    parser.add_argument("--start", type=date.fromisoformat, default=date(2015, 1, 1))
    parser.add_argument("--holdout", type=date.fromisoformat, default=date(2024, 1, 1))
    parser.add_argument("--commission-bps", type=float, default=10)
    parser.add_argument("--slippage-bps", type=float, default=5)
    parser.add_argument("--borrow-pct", type=float, default=3)
    parser.add_argument("--output", type=Path, help="Directory for daily ledger and summary CSVs")
    args = parser.parse_args()
    bars, symbol = load_bars(args.data)
    targets, vols = close_signals(bars, symbol)
    start, split = [next((i for i, b in enumerate(bars) if b.day >= day), len(bars))
                    for day in (args.start, args.holdout)]
    if not 0 < start < split < len(bars):
        parser.error("Dates must leave nonempty training, development and holdout periods")
    costs = Costs(args.commission_bps, args.slippage_bps, args.borrow_pct)
    combined = []
    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
    for name, first, end, annual in (("development", start, split, True),
                                     ("holdout", split, len(bars), False)):
        rows = simulate(bars, targets, vols, first, end, costs, annual)
        print(f"{symbol} {name}  {bars[first].day} through {bars[end-1].day}")
        for row in summarize(rows):
            print(f"  {row['model']:8} P&L {row['pnl']:10,.2f}  Sharpe {display(row['sharpe'])}"
                  f"  max DD {row['drawdown']:.2%}  costs {row['cost']:,.2f}  fills {row['fills']}")
            combined.append({"period": name, **row})
        if args.output:
            save_csv(args.output / f"{name}_daily.csv", rows)
        if name == "holdout":
            ci = paired_interval(rows)
            print("  Paired 95% interval for Sharpe difference (sma_vol minus sma):",
                  f"[{ci[0]:.3f}, {ci[1]:.3f}]" if ci else "n/a")
            if args.output and ci:
                save_csv(args.output / "holdout_interval.csv",
                         [dict(block_days=20, repetitions=2000, seed=1701, low=ci[0], high=ci[1])])
    if args.output:
        save_csv(args.output / "summary.csv", combined)


if __name__ == "__main__":
    main()
