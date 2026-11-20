import math
import unittest
from datetime import date, timedelta

from research import (Bar, CAPITAL, Costs, ROOT, calibration, close_signals,
                      load_bars, paired_interval, simulate, summarize)


class StudyTests(unittest.TestCase):
    def setUp(self):
        self.bars = [Bar(date(2019, 1, 1) + timedelta(days=i), 100, 100)
                     for i in range(320)]

    def test_legacy_crossover_count_and_direction(self):
        bars, symbol = load_bars(ROOT / "data/prices.csv")
        targets, _ = close_signals(bars, symbol)
        changes = [(b.day.isoformat(), curr-prev)
                   for b, prev, curr in zip(bars[1:], targets, targets[1:]) if curr != prev]
        self.assertEqual(changes, [("2024-02-27", -100), ("2024-03-20", 100)])

    def test_fill_gap_short_dividend_borrow_and_interest(self):
        i = 300
        self.bars[i+1] = Bar(self.bars[i].day + timedelta(days=3), 108, 110, 1, 0.0001)
        targets = [0]*len(self.bars)
        targets[i-1] = -100
        rows = simulate(self.bars, targets, [0.01]*320, i, i+2, Costs(10, 5, 3), False)
        short, cover = [r for r in rows if r["model"] == "sma"]
        self.assertAlmostEqual(short["fill"], 99.95)
        self.assertAlmostEqual(cover["fill"], 108.054)
        self.assertEqual(cover["dividend"], -100)
        self.assertAlmostEqual(cover["borrow"], 10_000 * 0.03 * 3 / 365)
        self.assertAlmostEqual(cover["interest"], short["cash"] * 0.0001)
        expected = (CAPITAL + 100*(short["fill"]-cover["fill"]) - 100
                    - short["commission"] - cover["commission"] - cover["borrow"] + cover["interest"])
        self.assertAlmostEqual(cover["equity"], expected)

    def test_high_vol_rebalance_executes_next_open(self):
        vols = [0.01]*320
        vols[300] = 0.03
        rows = simulate(self.bars, [100]*320, vols, 300, 303, Costs(0, 0, 0), False)
        self.assertEqual([r["shares"] for r in rows if r["model"] == "sma_vol"], [100, 50, 100])
        self.assertEqual([r["delta"] for r in rows if r["model"] == "sma"], [100, 0, 0])

    def test_future_prices_do_not_change_past_decisions(self):
        bars = [Bar(b.day, 100, 100+5*math.sin(i/6)) for i, b in enumerate(self.bars)]
        changed = bars[:303] + [Bar(b.day, 500, 400) for b in bars[303:]]
        def run(seq):
            targets, vols = close_signals(seq, "TEST")
            return simulate(seq, targets, vols, 285, 310, Costs(), False)
        self.assertEqual(run(bars)[:18*3], run(changed)[:18*3])
        with self.assertRaises(ValueError):
            calibration(bars, [0]*320, [None]*320, 300)

    def test_paired_bootstrap_identical_series(self):
        rows = [dict(model=model, excess_return=math.sin(i)/100)
                for i in range(100) for model in ("sma", "sma_vol")]
        self.assertEqual(paired_interval(rows, repetitions=200), (0, 0))

    def test_cash_only_has_no_excess_gain(self):
        bars = [Bar(b.day, 100, 100, 0, 0.0001) for b in self.bars]
        rows = simulate(bars, [0]*320, [0.01]*320, 300, 320, Costs(), False)
        for result in summarize(rows):
            self.assertAlmostEqual(result["pnl_vs_cash"], 0, places=7)
            self.assertIsNone(result["sharpe"])


if __name__ == "__main__":
    unittest.main()
