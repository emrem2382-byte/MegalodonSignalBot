"""One-fetch backtest over last week that reports how many (ticker, day)
combinations would fire BUY under several different vote thresholds --
lets us pick a sensible SIGNAL_MODE without re-fetching data repeatedly.
"""
import time
from datetime import datetime, timedelta

from bot import config, data
from bot.indicators import ALL_INDICATORS, Signal


def last_week_range():
    today = datetime.now().date()
    this_monday = today - timedelta(days=today.weekday())
    last_monday = this_monday - timedelta(days=7)
    last_friday = last_monday + timedelta(days=4)
    return last_monday, last_friday


def main() -> None:
    start_date, end_date = last_week_range()
    print(f"[report] replaying {start_date} .. {end_date}")

    tickers = config.load_tickers()
    total_indicators = len(ALL_INDICATORS)
    rows = []  # (date, ticker, buy_votes, sell_votes)
    start = time.time()

    for i, ticker in enumerate(tickers):
        if i > 0:
            data.polite_delay()
        df = data.fetch_history(ticker)
        if df.empty:
            continue

        mask = (df.index.date >= start_date) & (df.index.date <= end_date)
        positions = [pos for pos, keep in enumerate(mask) if keep]
        for pos in positions:
            sub = df.iloc[: pos + 1]
            results = [ind.evaluate(sub) for ind in ALL_INDICATORS]
            buy_votes = sum(1 for r in results if r.signal == Signal.BUY)
            sell_votes = sum(1 for r in results if r.signal == Signal.SELL)
            if buy_votes or sell_votes:
                rows.append((df.index[pos].date(), ticker, buy_votes, sell_votes))

        if (i + 1) % 100 == 0:
            print(f"[report] ...{i + 1}/{len(tickers)} tickers")

    elapsed = time.time() - start
    print(f"\n[report] done in {elapsed / 60:.1f} min, {len(tickers)} tickers, "
          f"{total_indicators} indicators, {len(rows)} ticker-days with any vote\n")

    print(f"{'threshold':<28}{'count':>8}")
    for min_votes in range(1, total_indicators + 1):
        plain = sum(1 for _, _, b, s in rows if b >= min_votes)
        agree = sum(1 for _, _, b, s in rows if b >= min_votes and b > s)
        print(f"buy_votes >= {min_votes:<15}{plain:>8}   (with buy>sell: {agree})")

    print("\nTop 15 by buy_votes (net of sell disagreement):")
    ranked = sorted(rows, key=lambda r: (r[2] - r[3], r[2]), reverse=True)[:15]
    for date, ticker, b, s in ranked:
        print(f"{date}  {ticker:6s}  buy={b} sell={s}")


if __name__ == "__main__":
    main()
