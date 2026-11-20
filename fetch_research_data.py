"""Download a fixed single-symbol Yahoo Finance daily snapshot for the study."""

import csv
import io
import json
import zipfile
from argparse import ArgumentParser
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


def date_string(timestamp):
    return datetime.fromtimestamp(timestamp, timezone.utc).date().isoformat()


def download(symbol):
    params = urlencode(dict(period1=1262304000, period2=1767225600, interval="1d",
                            events="div,splits"))
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol, safe='')}?{params}"
    with urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30) as response:
        return json.load(response)["chart"]["result"][0]


RF_URL = ("https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
          "F-F_Research_Data_Factors_daily_CSV.zip")


def parse_rf(raw):
    lines = raw.decode("utf-8-sig").splitlines()
    header = next(i for i, line in enumerate(lines) if line.strip().endswith(",RF"))
    result = {}
    for row in csv.DictReader(lines[header:]):
        token = (row.get("") or "").strip()
        if len(token) == 8 and token.isdigit():
            day = datetime.strptime(token, "%Y%m%d").date().isoformat()
            result[day] = float(row["RF"]) / 100
    return result


def download_rf():
    with urlopen(RF_URL, timeout=30) as response:
        with zipfile.ZipFile(io.BytesIO(response.read())) as archive:
            return parse_rf(archive.read(archive.namelist()[0]))


def write_csv(snapshot, rates, output):
    prices = snapshot["indicators"]["quote"][0]
    dates = [date_string(t) for t in snapshot["timestamp"]]
    dividends = {}
    for event in snapshot.get("events", {}).get("dividends", {}).values():
        day = date_string(event["date"])
        dividends[day] = dividends.get(day, 0) + event["amount"]
    if not set(dividends).issubset(dates):
        raise ValueError("Dividend without a matching price bar")
    symbol = snapshot["meta"]["symbol"]
    rows = []
    for day, opening, close in zip(dates, prices["open"], prices["close"], strict=True):
        if opening is None or close is None or min(opening, close) <= 0:
            raise ValueError(f"Missing or invalid bar for {day}")
        rows.append((symbol, day, opening, close, dividends.get(day, 0), rates[day]))
    output.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(mode="w", dir=output.parent, newline="", delete=False) as f:
        writer = csv.writer(f)
        writer.writerow(("symbol", "timestamp", "open", "close", "dividend", "rf_return"))
        writer.writerows(rows)
    Path(f.name).replace(output)
    print(f"{symbol}: {len(rows)} bars, {dates[0]} to {dates[-1]}")


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="AAPL")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    write_csv(download(args.symbol), download_rf(), args.output)
