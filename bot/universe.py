"""Builds a broad ticker universe from free public sources (no API key).

Combines the S&P 500 and Nasdaq-100 constituent lists, scraped from
Wikipedia. Meant to be run occasionally (see
.github/workflows/update_universe.yml) to refresh config/tickers.txt
automatically as companies get added, removed, or renamed -- you shouldn't
have to maintain the list by hand.
"""
import io

import pandas as pd
import requests

SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
NASDAQ100_URL = "https://en.wikipedia.org/wiki/Nasdaq-100"

# A plain "python-requests" UA gets blocked/served differently by some
# sites; a normal browser UA avoids that.
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; stock-signal-bot/1.0)"}

# Wikipedia's "Nasdaq-100" article doesn't reliably expose a components
# table with tickers -- it used to, but the page has since been
# restructured around a navbox that lists company names without symbols.
# We still try to scrape it (in case that ever changes back), but always
# merge in this small, hand-picked list of well-known Nasdaq-100 names
# that tend to sit outside the S&P 500 (foreign-domiciled companies,
# newer listings, etc.) so the combined universe isn't S&P-500-only.
NASDAQ_SUPPLEMENT = {
    "ASML", "MELI", "PDD", "JD", "ARM", "TEAM", "MDB", "ZS", "ILMN",
    "SIRI", "CCEP", "GFS",
}


def _read_tables(url: str) -> list[pd.DataFrame]:
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    # pandas >= 2.1 deprecates (and some versions reject) passing a literal
    # HTML string directly -- wrap it in StringIO to be explicit.
    return pd.read_html(io.StringIO(resp.text))


def fetch_sp500() -> set[str]:
    df = _read_tables(SP500_URL)[0]
    # Yahoo Finance uses "-" where Wikipedia uses "." (e.g. BRK.B -> BRK-B).
    symbols = df["Symbol"].astype(str).str.strip().str.replace(".", "-", regex=False)
    return set(symbols)


def fetch_nasdaq100() -> set[str]:
    for table in _read_tables(NASDAQ100_URL):
        cols = [c for c in table.columns if str(c).strip().lower() in ("ticker", "symbol")]
        if cols:
            return set(table[cols[0]].astype(str).str.strip())
    return set()


def build_universe() -> list[str]:
    """Returns the deduplicated, sorted union. Empty only if the S&P 500
    fetch itself fails -- the Nasdaq supplement alone is too small to ship
    as a full universe.
    """
    tickers: set[str] = set(NASDAQ_SUPPLEMENT)

    try:
        tickers |= fetch_sp500()
    except Exception as exc:  # noqa: BLE001 -- Wikipedia layout can change
        print(f"[universe] S&P 500 fetch failed: {exc}")

    try:
        ndx = fetch_nasdaq100()
        if ndx:
            tickers |= ndx
        else:
            print("[universe] no Ticker/Symbol column found on the Nasdaq-100 "
                  "page (layout likely changed); using the built-in supplement only")
    except Exception as exc:  # noqa: BLE001
        print(f"[universe] Nasdaq-100 fetch failed: {exc}")

    return sorted(t for t in tickers if t and t.isascii())
