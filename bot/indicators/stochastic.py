import pandas as pd

from .base import Indicator, IndicatorResult, Signal


class Stochastic(Indicator):
    """%K/%D crossover, gated to the oversold/overbought zones (with a small
    buffer so a cross that happens just as price is leaving the zone still
    counts -- waiting for a strict <20 cross misses most real turns).
    """

    name = "stochastic"

    def __init__(self, k_period: int = 14, d_period: int = 3, oversold: float = 20, overbought: float = 80):
        self.k_period = k_period
        self.d_period = d_period
        self.oversold = oversold
        self.overbought = overbought

    def evaluate(self, df: pd.DataFrame) -> IndicatorResult:
        if len(df) < self.k_period + self.d_period + 2:
            return IndicatorResult(self.name, Signal.HOLD, "недостатъчно данни")

        low_n = df["Low"].rolling(self.k_period).min()
        high_n = df["High"].rolling(self.k_period).max()
        range_n = (high_n - low_n).replace(0, 1e-10)
        k = 100 * (df["Close"] - low_n) / range_n
        d = k.rolling(self.d_period).mean()

        k_prev, k_curr = k.iloc[-2], k.iloc[-1]
        d_prev, d_curr = d.iloc[-2], d.iloc[-1]

        bull_cross = k_prev <= d_prev and k_curr > d_curr
        bear_cross = k_prev >= d_prev and k_curr < d_curr

        if bull_cross and k_curr < self.oversold + 10:
            return IndicatorResult(self.name, Signal.BUY, f"%K премина над %D близо до препродаденост (K={k_curr:.1f})")
        if bear_cross and k_curr > self.overbought - 10:
            return IndicatorResult(self.name, Signal.SELL, f"%K падна под %D близо до превишена покупка (K={k_curr:.1f})")

        return IndicatorResult(self.name, Signal.HOLD, f"%K={k_curr:.1f}, %D={d_curr:.1f}")
