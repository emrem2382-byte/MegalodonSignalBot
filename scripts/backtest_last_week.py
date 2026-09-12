"""Backtest: for every ticker, replay each trading day of last calendar
week (Mon-Fri) as if it were "today", and report which days would have
fired a combined BUY/SELL signal.

This re-fetches full history once per ticker (same as a live scan) and
then just re-evaluates the indicators against progressively shorter
slices of it -- no extra network cost per day checked.

Run with:  python -m scripts.backtest_last_week
"""
import time
from datetime import datetime, timedelta

from bot import config, data
from bot.engine import evaluate_ticker
from bot.indicators import Signal


def last_week_range() -> tuple[datetime.date, datetime.date]:
    today = datetime.now().date()
    this_monday = today - timedelta(days=today.weekday())
    last_monday = this_monday - timedelta(days=7)
    last_friday = last_monday + timedelta(days=4)
    return last_monday, last_friday


def main() -> None:
    start_date, end_date = last_week_range()
    print(f"[backtest] replaying {start_date} .. {end_date} (last week)")

    tickers = config.load_tickers()
    hits = []
    start = time.time()

    for i, ticker in enumerate(tickers):
        if i > 0:
            data.polite_delay()

        df = data.fetch_history(ticker)
        if df.empty:
            continue

        week_mask = (df.index.date >= start_date) & (df.index.date <= end_date)
        week_positions = [pos for pos, keep in enumerate(week_mask) if keep]
        if not week_positions:
            continue

        for pos in week_positions:
            sub = df.iloc[: pos + 1]
            fires, results = evaluate_ticker(sub)
            if not fires:
                continue
            bar_date = df.index[pos].date()
            votes = [r.name for r in results if r.signal != Signal.HOLD]
            hits.append((bar_date, ticker, votes, results))

        if (i + 1) % 100 == 0:
            print(f"[backtest] ...{i + 1}/{len(tickers)} tickers checked")

    elapsed = time.time() - start
    print(f"\n[backtest] done in {elapsed / 60:.1f} min, {len(tickers)} tickers, "
          f"{len(hits)} signal day(s) found\n")

    for bar_date, ticker, votes, results in sorted(hits):
        detail = ", ".join(f"{r.name}={r.signal.value}" for r in results if r.signal != Signal.HOLD)
        print(f"{bar_date}  {ticker:6s}  {detail}")

    if not hits:
        print("No BUY/SELL signals would have fired for any ticker last week "
              "under the current SIGNAL_MODE/indicator set.")


if __name__ == "__main__":
    main()
