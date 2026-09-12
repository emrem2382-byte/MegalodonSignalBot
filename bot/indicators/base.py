"""Common interface every indicator implements.

To add a new indicator:
1. Create a new file in this folder (e.g. bollinger.py).
2. Subclass Indicator and implement evaluate().
3. Register an instance of it in indicators/__init__.py's ALL_INDICATORS list.
That's it -- the engine and the Telegram message will pick it up automatically.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import pandas as pd


class Signal(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class IndicatorResult:
    name: str
    signal: Signal
    detail: str = ""


class Indicator:
    """Base class for all indicators."""

    name: str = "indicator"

    def evaluate(self, df: pd.DataFrame) -> IndicatorResult:
        """df has columns Open/High/Low/Close/Volume, indexed by date, ascending order.

        Must return exactly one IndicatorResult (BUY, SELL, or HOLD).
        """
        raise NotImplementedError
