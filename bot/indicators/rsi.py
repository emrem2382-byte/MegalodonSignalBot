import pandas as pd

from .base import Indicator, IndicatorResult, Signal


class Rsi(Indicator):
    """BUY when RSI crosses back up out of oversold territory."""

    name = "rsi"

    def __init__(self, period: int = 14, oversold: float = 30, overbought: float = 70):
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    def _rsi_series(self, close: pd.Series) -> pd.Series:
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1 / self.period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / self.period, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, 1e-10)
        return 100 - (100 / (1 + rs))

    def evaluate(self, df: pd.DataFrame) -> IndicatorResult:
        if len(df) < self.period + 2:
            return IndicatorResult(self.name, Signal.HOLD, "not enough data")

        rsi = self._rsi_series(df["Close"])
        prev, curr = rsi.iloc[-2], rsi.iloc[-1]

        if prev <= self.oversold < curr:
            return IndicatorResult(self.name, Signal.BUY, f"RSI left oversold ({curr:.1f})")
        if prev >= self.overbought > curr:
            return IndicatorResult(self.name, Signal.SELL, f"RSI left overbought ({curr:.1f})")
        return IndicatorResult(self.name, Signal.HOLD, f"RSI={curr:.1f}")
