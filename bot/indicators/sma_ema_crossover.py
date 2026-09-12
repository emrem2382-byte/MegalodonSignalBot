import pandas as pd

from .base import Indicator, IndicatorResult, Signal


class SmaEmaCrossover(Indicator):
    """BUY when the fast EMA crosses above the slow SMA (golden-cross style)."""

    name = "sma_ema_crossover"

    def __init__(self, fast: int = 20, slow: int = 50):
        self.fast = fast
        self.slow = slow

    def evaluate(self, df: pd.DataFrame) -> IndicatorResult:
        if len(df) < self.slow + 2:
            return IndicatorResult(self.name, Signal.HOLD, "недостатъчно данни")

        fast_ma = df["Close"].ewm(span=self.fast, adjust=False).mean()
        slow_ma = df["Close"].rolling(window=self.slow).mean()

        prev_diff = fast_ma.iloc[-2] - slow_ma.iloc[-2]
        curr_diff = fast_ma.iloc[-1] - slow_ma.iloc[-1]

        if prev_diff <= 0 and curr_diff > 0:
            return IndicatorResult(self.name, Signal.BUY, f"EMA{self.fast} премина над SMA{self.slow}")
        if prev_diff >= 0 and curr_diff < 0:
            return IndicatorResult(self.name, Signal.SELL, f"EMA{self.fast} падна под SMA{self.slow}")
        return IndicatorResult(self.name, Signal.HOLD, "няма пресичане")
