import pandas as pd

from .base import Indicator, IndicatorResult, Signal


def _wilder_smooth(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(alpha=1 / period, adjust=False).mean()


class AdxDmi(Indicator):
    """Directional Movement Index: +DI/-DI crossover, confirmed by ADX trend strength.

    Unlike a plain crossover, this only fires while ADX shows the market is
    actually trending (above `adx_threshold`) -- a DI cross in a flat,
    choppy market is noise.
    """

    name = "adx_dmi"

    def __init__(self, period: int = 14, adx_threshold: float = 20.0):
        self.period = period
        self.adx_threshold = adx_threshold

    def evaluate(self, df: pd.DataFrame) -> IndicatorResult:
        if len(df) < self.period * 3 + 5:
            return IndicatorResult(self.name, Signal.HOLD, "not enough data")

        high, low, close = df["High"], df["Low"], df["Close"]
        prev_high, prev_low, prev_close = high.shift(1), low.shift(1), close.shift(1)

        up_move = high - prev_high
        down_move = prev_low - low
        plus_dm = pd.Series(0.0, index=df.index)
        minus_dm = pd.Series(0.0, index=df.index)
        plus_dm[(up_move > down_move) & (up_move > 0)] = up_move
        minus_dm[(down_move > up_move) & (down_move > 0)] = down_move

        tr = pd.concat(
            [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
            axis=1,
        ).max(axis=1)

        atr = _wilder_smooth(tr, self.period)
        plus_di = 100 * _wilder_smooth(plus_dm, self.period) / atr.replace(0, 1e-10)
        minus_di = 100 * _wilder_smooth(minus_dm, self.period) / atr.replace(0, 1e-10)
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, 1e-10)
        adx = _wilder_smooth(dx, self.period)

        plus_prev, plus_curr = plus_di.iloc[-2], plus_di.iloc[-1]
        minus_prev, minus_curr = minus_di.iloc[-2], minus_di.iloc[-1]
        adx_curr = adx.iloc[-1]

        bull_cross = plus_prev <= minus_prev and plus_curr > minus_curr
        bear_cross = plus_prev >= minus_prev and plus_curr < minus_curr

        if bull_cross and adx_curr > self.adx_threshold:
            return IndicatorResult(self.name, Signal.BUY, f"+DI crossed above -DI, ADX={adx_curr:.1f}")
        if bear_cross and adx_curr > self.adx_threshold:
            return IndicatorResult(self.name, Signal.SELL, f"-DI crossed above +DI, ADX={adx_curr:.1f}")

        return IndicatorResult(
            self.name, Signal.HOLD,
            f"+DI={plus_curr:.1f}, -DI={minus_curr:.1f}, ADX={adx_curr:.1f}",
        )
