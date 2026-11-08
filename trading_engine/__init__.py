"""trading_engine — an event-driven trading engine.

You are building this package step by step:

    events.py            Event and typed subclasses         (steps 2-3)
    event_bus.py         pub/sub message board              (step 4)
    order.py             the Order class                    (step 5)
    order_book.py        sorted bids and asks               (steps 6-7)
    position.py          cost basis, realized & unrealized  (steps 8-9)
    position_manager.py  one Position per symbol            (step 10)
    risk_manager.py      guardrails + audit log             (steps 11-12)
    execution_engine.py  submit + match                     (steps 13-14)
    market_data.py       CSV replay                         (step 15)
    strategy.py          moving-average crossover           (step 16)
    backtester.py        run, chart, report                 (steps 17-18)
"""

# TODO (Step 1): give your engine a name, e.g. "Quantt Trading Engine v0.1"
ENGINE_NAME = "Quantt Trading Engine v0.1"
