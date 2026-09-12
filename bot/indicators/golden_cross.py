import pandas as pd

from .base import Indicator, IndicatorResult, Signal


class GoldenCross(Indicator):
    """The classic long-term trend cross: SMA50 vs SMA200.

    Distinct from sma_ema_crossover.py (which is a faster EMA20/SMA50
    read) -- this one is the textbook Golden Cross / Death Cross, a much
    slower, higher-conviction, longer-horizon signal.
    """

    name = "golden_cross"

    def __init__(self, fast: int = 50, slow: int = 200):
        self.fast = fast
        self.slow = slow

    def evaluate(self, df: pd.DataFrame) -> IndicatorResult:
        if len(df) < self.slow + 2:
            return IndicatorResult(self.name, Signal.HOLD, "not enough data")

        fast_ma = df["Close"].rolling(self.fast).mean()
        slow_ma = df["Close"].rolling(self.slow).mean()

        prev_diff = fast_ma.iloc[-2] - slow_ma.iloc[-2]
        curr_diff = fast_ma.iloc[-1] - slow_ma.iloc[-1]

        if prev_diff <= 0 and curr_diff > 0:
            return IndicatorResult(self.name, Signal.BUY, f"Golden Cross: SMA{self.fast} crossed above SMA{self.slow}")
        if prev_diff >= 0 and curr_diff < 0:
            return IndicatorResult(self.name, Signal.SELL, f"Death Cross: SMA{self.fast} crossed below SMA{self.slow}")

        return IndicatorResult(self.name, Signal.HOLD, "no crossover")
