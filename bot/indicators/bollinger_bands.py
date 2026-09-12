import pandas as pd

from .base import Indicator, IndicatorResult, Signal


class BollingerBands(Indicator):
    """Mean-reversion bounce off a band, or a volume-backed breakout through one.

    BUY on either: price reclaims the lower band after closing at/below it
    (bounce), or closes above the upper band on above-average volume
    (breakout). SELL is the mirror image.
    """

    name = "bollinger_bands"

    def __init__(
        self,
        period: int = 20,
        num_std: float = 2.0,
        breakout_volume_mult: float = 1.5,
        volume_ma_period: int = 20,
    ):
        self.period = period
        self.num_std = num_std
        self.breakout_volume_mult = breakout_volume_mult
        self.volume_ma_period = volume_ma_period

    def evaluate(self, df: pd.DataFrame) -> IndicatorResult:
        min_bars = max(self.period, self.volume_ma_period) + 2
        if len(df) < min_bars:
            return IndicatorResult(self.name, Signal.HOLD, "not enough data")

        close = df["Close"]
        mid = close.rolling(self.period).mean()
        std = close.rolling(self.period).std()
        upper = mid + self.num_std * std
        lower = mid - self.num_std * std
        volume_ma = df["Volume"].rolling(self.volume_ma_period).mean()

        prev_close, curr_close = close.iloc[-2], close.iloc[-1]
        prev_lower, curr_lower = lower.iloc[-2], lower.iloc[-1]
        prev_upper, curr_upper = upper.iloc[-2], upper.iloc[-1]
        vol_ok = df["Volume"].iloc[-1] > volume_ma.iloc[-1] * self.breakout_volume_mult

        bullish_bounce = prev_close <= prev_lower and curr_close > curr_lower
        bullish_breakout = prev_close <= prev_upper and curr_close > curr_upper and vol_ok
        bearish_bounce = prev_close >= prev_upper and curr_close < curr_upper
        bearish_breakdown = prev_close >= prev_lower and curr_close < curr_lower and vol_ok

        if bullish_bounce or bullish_breakout:
            reason = "volume breakout above upper band" if bullish_breakout else "bounce off lower band"
            return IndicatorResult(self.name, Signal.BUY, reason)
        if bearish_bounce or bearish_breakdown:
            reason = "volume breakdown below lower band" if bearish_breakdown else "rejection off upper band"
            return IndicatorResult(self.name, Signal.SELL, reason)

        band_width = upper.iloc[-1] - lower.iloc[-1]
        pct_b = (curr_close - lower.iloc[-1]) / band_width if band_width else 0.5
        return IndicatorResult(self.name, Signal.HOLD, f"%B={pct_b:.2f}")
