import pandas as pd

from .base import Indicator, IndicatorResult, Signal


class Macd(Indicator):
    """BUY when the MACD line crosses above its signal line."""

    name = "macd"

    def __init__(self, fast: int = 12, slow: int = 26, signal_period: int = 9):
        self.fast = fast
        self.slow = slow
        self.signal_period = signal_period

    def evaluate(self, df: pd.DataFrame) -> IndicatorResult:
        if len(df) < self.slow + self.signal_period + 2:
            return IndicatorResult(self.name, Signal.HOLD, "недостатъчно данни")

        close = df["Close"]
        ema_fast = close.ewm(span=self.fast, adjust=False).mean()
        ema_slow = close.ewm(span=self.slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self.signal_period, adjust=False).mean()

        prev_diff = macd_line.iloc[-2] - signal_line.iloc[-2]
        curr_diff = macd_line.iloc[-1] - signal_line.iloc[-1]

        if prev_diff <= 0 and curr_diff > 0:
            return IndicatorResult(self.name, Signal.BUY, "MACD премина над сигналната линия")
        if prev_diff >= 0 and curr_diff < 0:
            return IndicatorResult(self.name, Signal.SELL, "MACD падна под сигналната линия")
        return IndicatorResult(self.name, Signal.HOLD, "няма пресичане")
