"""Central configuration: env vars, paths, and the ticker watchlist."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()  # no-op if there's no .env file (e.g. in GitHub Actions)
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

TICKERS_FILE = BASE_DIR / "config" / "tickers.txt"
STATE_FILE = BASE_DIR / "data" / "state.json"

# Minimum number of indicators that must say BUY before a combined signal
# fires. This account is buy-only (no shorting), so SELL votes are never
# their own alert -- they only count as disagreement: a BUY only fires if
# buy_votes also outnumbers sell_votes (see engine.py). Backtested against
# the S&P 500 + Nasdaq universe over one week: threshold 1 ("any") fired
# 422 times and included cases where most indicators actually said SELL;
# threshold 5 ("majority" of 9) fired 0 times. 3 was the sweet spot --
# ~1-2 genuinely-agreeing signals a day across the whole universe.
MIN_BUY_VOTES = int(os.environ.get("MIN_BUY_VOTES", "3"))

# yfinance history window used to compute indicators.
# 5y so daily EMA200 has a solid warm-up AND the FIA indicator's weekly
# higher-timeframe EMA200 (needs ~200 weeks) has enough bars too.
LOOKBACK_PERIOD = os.environ.get("LOOKBACK_PERIOD", "5y")
LOOKBACK_INTERVAL = os.environ.get("LOOKBACK_INTERVAL", "1d")


def load_tickers() -> list[str]:
    """Read config/tickers.txt -- one symbol per line, '#' comments allowed."""
    if not TICKERS_FILE.exists():
        return []

    tickers = []
    for line in TICKERS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        tickers.append(line.upper())
    return tickers
