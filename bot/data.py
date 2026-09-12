"""Price data fetching (free, via yfinance) with pacing + retries.

Yahoo Finance has no official quota, but it will start throttling/blocking
an IP that fires requests too fast or too aggressively -- a real risk once
we're scanning hundreds of tickers from a shared GitHub Actions runner. So
every request is paced with a small randomized delay, and transient
failures (timeouts, "rate limited" style errors) get a couple of backed-off
retries before we give up on that one ticker and move on.
"""
import random
import time

import pandas as pd
import yfinance as yf

from . import config

# Tuned to keep a full scan of ~500-600 tickers comfortably under the
# 30-minute schedule interval while staying polite to Yahoo's servers.
BASE_DELAY_SECONDS = 0.35
JITTER_SECONDS = 0.25
MAX_RETRIES = 2
RETRY_BACKOFF_SECONDS = 3


def polite_delay() -> None:
    """Small randomized pause -- call this between tickers, not just on retry."""
    time.sleep(BASE_DELAY_SECONDS + random.uniform(0, JITTER_SECONDS))


def fetch_history(ticker: str) -> pd.DataFrame:
    """Download recent OHLCV history for one ticker.

    Retries a couple of times on transient failures (network hiccups, Yahoo
    rate-limit responses), then gives up and returns an empty DataFrame so
    the caller can just skip the ticker instead of failing the whole run.
    """
    df = None

    for attempt in range(1, MAX_RETRIES + 2):  # e.g. 1 try + 2 retries
        try:
            df = yf.download(
                ticker,
                period=config.LOOKBACK_PERIOD,
                interval=config.LOOKBACK_INTERVAL,
                progress=False,
                auto_adjust=True,
                threads=False,
            )
        except Exception as exc:  # noqa: BLE001 -- yfinance can raise many things
            print(f"[data] {ticker}: attempt {attempt} failed: {exc}")
            df = None

        if df is not None and not df.empty:
            break

        if attempt <= MAX_RETRIES:
            time.sleep(RETRY_BACKOFF_SECONDS * attempt)

    if df is None or df.empty:
        return pd.DataFrame()

    # yfinance sometimes returns MultiIndex columns (ticker, field) even for
    # a single symbol -- flatten to just the field names.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    return df.dropna()
