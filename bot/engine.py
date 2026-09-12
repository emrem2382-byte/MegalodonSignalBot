"""Combines all registered indicators into one BUY/no-BUY decision per ticker.

Only BUY alerts are ever produced -- this bot is built for a buy-only
account (e.g. Revolut, no shorting). A SELL vote from an indicator is
never its own alert; it only counts as disagreement, vetoing a BUY that
doesn't have real consensus behind it.
"""
import pandas as pd

from . import config
from .indicators import ALL_INDICATORS, IndicatorResult, Signal


def evaluate_ticker(df: pd.DataFrame) -> tuple[bool, list[IndicatorResult]]:
    """Run every indicator against df and decide whether a combined BUY fires.

    Returns (fires, results) where results holds one IndicatorResult per
    registered indicator (useful for the Telegram message breakdown).
    """
    results = [ind.evaluate(df) for ind in ALL_INDICATORS]
    buy_votes = sum(1 for r in results if r.signal == Signal.BUY)
    sell_votes = sum(1 for r in results if r.signal == Signal.SELL)

    # Both conditions matter: enough indicators agreeing, AND buy actually
    # outnumbering sell -- otherwise one stray BUY vote could fire while
    # most of the panel is flashing SELL.
    fires = buy_votes >= config.MIN_BUY_VOTES and buy_votes > sell_votes

    return fires, results
