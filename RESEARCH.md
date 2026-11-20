# AAPL next-open volatility experiment

Run the following from the trading-engine folder with Python 3.10 or later. The research runner uses the existing moving-average strategy, the standard library and an included data snapshot. It can run offline.

```console
python research.py --output results
python -m unittest -v test_research
```

The daily ledgers include the opening price, simulated fill, signed share change, end-of-day shares, cash, trading costs, interest and marked equity. The summary includes dollar P&L relative to cash and annualized Sharpe. To reproduce the cost stress, run the following.

```console
python research.py --slippage-bps 10 --borrow-pct 6 --output stress_results
```

## Experiment

- Each account starts with USD 100,000. The existing 5/20 SMA strategy submits signed changes of 100 split-adjusted shares on crosses. The resulting long/flat or short/flat path depends on the first cross. On this snapshot the holdout SMA targets were 0 or +100.
- Determine targets after the close and transact the next session at the open. Both SMA accounts see the same history. The volatility variant halves the base position when trailing 20-session total-return volatility exceeds the training sample's 75th percentile. It may resize without a new crossover.
- Use 2010–2014 for initial calibration. Carry development portfolios through 2015–2023, recalibrating at the start of each calendar year using earlier observations. Restart each account in cash for the final 2024–2025 holdout, retain the signal history and freeze calibration at the end of 2023. No parameter search was performed. The holdout daily volatility cutoff was 1.9372%.
- The long-only benchmark holds a training-estimated share count chosen to approximate the base SMA's average absolute dollar exposure. It rebalances annually in development and holds 64 shares throughout the holdout. Realized average gross exposures in the holdout were 13.1% for buy-and-hold, 12.2% for SMA and 11.3% for volatility sizing.
- Charge 10 basis points commission and 5 basis points adverse slippage per side, and a hypothetical 3% annual short borrow fee on prior close short market value using calendar days. Pay dividends on signed prior close shares at the ex-date. Prior close cash earns the daily one-month Treasury bill proxy, including weekends as represented in the published trading-day return. This is a cash-sweep assumption. Cash funding and short-sale proceeds use this same rate. Open ending positions are marked at the last close.
- Sharpe is the daily portfolio return less the daily bill return, averaged and divided by the sample standard deviation of excess returns, multiplied by the square root of 252. The interval for the Sharpe difference resamples matching dates for both strategies in circular 20-session blocks, with 2,000 replicates and seed 1701. It measures uncertainty conditional on this sample. It cannot account for regimes missing from the sample.

## Holdout findings

| Portfolio | Net P&L | P&L vs cash | Sharpe | Max drawdown |
|---|---:|---:|---:|---:|
| Buy-and-hold | $14,835.56 | $4,275.36 | 0.563 | −3.88% |
| SMA | $9,336.80 | −$1,223.40 | −0.129 | −5.22% |
| Volatility-sized SMA | $10,706.87 | $146.67 | 0.037 | −2.91% |

Cash alone earned $10,560.20. Sizing reduced drawdown and improved Sharpe by 0.166 in this sample. The paired 95% interval of −0.277 to +0.568 includes zero. Under the cost stress, volatility-sized Sharpe was −0.011. Buy-and-hold had the highest holdout Sharpe. These results cover one stock, assumed execution costs and one historical holdout already inspected.

## Data

The snapshot has 4,024 AAPL sessions from January 4, 2010 through December 31, 2025. Open and close use the provider's split-adjusted series, with cash dividends tracked separately. The signal uses split-adjusted closes and volatility uses dividend-inclusive close-to-close returns. The price data and daily risk-free proxy can be fetched again into a new filename. Upstream data revisions may change the results. [Yahoo Finance AAPL history](https://finance.yahoo.com/quote/AAPL/history/) and [Kenneth French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html)

```console
python fetch_research_data.py --symbol AAPL --output data/aapl_refreshed.csv
python research.py --data data/aapl_refreshed.csv
```

Snapshot SHA-256: `d5622d9b6087dba942a718e8a01733a41dcc84ee74be82d55c4728233c3230be`.

For custom single-symbol CSVs supply symbol, timestamp (ISO date), open and close. Optional dividend is cash per share and rf_return is the daily rate in decimal units. Omitted columns default to zero. Supply at least 252 volatility estimates before the first evaluation date and nonempty development and holdout periods. Use `python research.py --help` for dates and costs.
