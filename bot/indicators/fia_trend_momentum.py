"""FIA Trend + Momentum 20/50/200.

EMA 20/50/200 trend structure + RSI(14) momentum + MACD(12,26,9), combined
into a 6-point setup score with an optional higher-timeframe (weekly, by
default) confirmation. Fires BUY/SELL only on a pullback-reclaim of EMA20
or a fresh MACD signal-line crossover, and only above `min_score`.

This is a straight port of the published "FIA Trend + Momentum 20/50/200"
indicator's logic onto our plain OHLCV DataFrame interface. Intended as a
confirmation tool, not a standalone system -- combine with price action,
support/resistance and risk management. Educational purposes only.
"""
import pandas as pd

from .base import Indicator, IndicatorResult, Signal


def _ema(close: pd.Series, span: int) -> pd.Series:
    return close.ewm(span=span, adjust=False).mean()


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-10)
    return 100 - (100 / (1 + rs))


def _macd(close: pd.Series, fast: int, slow: int, signal: int):
    macd_line = _ema(close, fast) - _ema(close, slow)
    signal_line = _ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def _ema_structure(ema20: float, ema50: float, ema200: float) -> str:
    """Classifies the current EMA stack, matching the indicator's background colors."""
    if ema20 > ema50 > ema200:
        return "green"  # clearly bullish
    if ema20 < ema50 and ema50 > ema200:
        return "blue"  # short-term weakness within a broader bullish trend
    if ema20 > ema50 and ema50 < ema200:
        return "orange"  # short-term strength, broader trend not yet bullish
    return "red"  # ema20 < ema50 < ema200 -- clearly bearish


class FiaTrendMomentum(Indicator):
    name = "fia_trend_momentum"

    def __init__(
        self,
        ema_fast: int = 20,
        ema_mid: int = 50,
        ema_slow: int = 200,
        rsi_period: int = 14,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        min_score: int = 5,
        use_higher_timeframe: bool = True,
        higher_timeframe: str = "W",
    ):
        self.ema_fast = ema_fast
        self.ema_mid = ema_mid
        self.ema_slow = ema_slow
        self.rsi_period = rsi_period
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.min_score = min_score
        self.use_higher_timeframe = use_higher_timeframe
        self.higher_timeframe = higher_timeframe

    def _higher_timeframe_bullish(self, df: pd.DataFrame) -> bool | None:
        """Resamples to the higher timeframe and reads its own EMA structure.
        Returns None when there isn't enough history yet to judge (e.g. a
        recent IPO) -- callers should treat that as "no opinion", not bearish.
        """
        htf_close = df["Close"].resample(self.higher_timeframe).last().dropna()
        if len(htf_close) < self.ema_slow + 2:
            return None

        ema20 = _ema(htf_close, self.ema_fast).iloc[-1]
        ema50 = _ema(htf_close, self.ema_mid).iloc[-1]
        ema200 = _ema(htf_close, self.ema_slow).iloc[-1]
        structure = _ema_structure(ema20, ema50, ema200)
        return structure in ("green", "orange")

    def evaluate(self, df: pd.DataFrame) -> IndicatorResult:
        min_bars = self.ema_slow + self.macd_slow + self.macd_signal + 5
        if len(df) < min_bars:
            return IndicatorResult(self.name, Signal.HOLD, "not enough data")

        close = df["Close"]
        ema20 = _ema(close, self.ema_fast)
        ema50 = _ema(close, self.ema_mid)
        ema200 = _ema(close, self.ema_slow)
        rsi = _rsi(close, self.rsi_period)
        macd_line, signal_line, hist = _macd(close, self.macd_fast, self.macd_slow, self.macd_signal)

        structure = _ema_structure(ema20.iloc[-1], ema50.iloc[-1], ema200.iloc[-1])

        rsi_curr, rsi_prev = rsi.iloc[-1], rsi.iloc[-2]
        rsi_rising, rsi_falling = rsi_curr > rsi_prev, rsi_curr < rsi_prev

        macd_bullish = macd_line.iloc[-1] > signal_line.iloc[-1]
        macd_bearish = macd_line.iloc[-1] < signal_line.iloc[-1]
        hist_rising = hist.iloc[-1] > hist.iloc[-2]
        hist_falling = hist.iloc[-1] < hist.iloc[-2]

        macd_bull_cross = macd_line.iloc[-2] <= signal_line.iloc[-2] and macd_line.iloc[-1] > signal_line.iloc[-1]
        macd_bear_cross = macd_line.iloc[-2] >= signal_line.iloc[-2] and macd_line.iloc[-1] < signal_line.iloc[-1]

        htf_bullish = self._higher_timeframe_bullish(df) if self.use_higher_timeframe else None

        # --- setup score, max 6: structure(2) + rsi(1) + macd(1) + momentum(1) + HTF(1) ---
        bull_score = (
            (2 if structure == "green" else 1 if structure == "orange" else 0)
            + (1 if rsi_curr > 50 else 0)
            + (1 if macd_bullish else 0)
            + (1 if hist_rising else 0)
            + (1 if htf_bullish else 0)
        )
        bear_score = (
            (2 if structure == "red" else 1 if structure == "blue" else 0)
            + (1 if rsi_curr < 50 else 0)
            + (1 if macd_bearish else 0)
            + (1 if hist_falling else 0)
            + (1 if htf_bullish is False else 0)
        )

        # --- pullback: price reclaims/loses EMA20 for the first time (avoids repeat labels) ---
        bullish_pullback = (
            structure == "green"
            and close.iloc[-1] > ema20.iloc[-1]
            and close.iloc[-2] <= ema20.iloc[-2]
            and rsi_rising
            and macd_bullish
        )
        bearish_pullback = (
            structure == "red"
            and close.iloc[-1] < ema20.iloc[-1]
            and close.iloc[-2] >= ema20.iloc[-2]
            and rsi_falling
            and macd_bearish
        )

        if bull_score >= self.min_score and (bullish_pullback or macd_bull_cross):
            trigger = "pullback reclaim" if bullish_pullback else "MACD crossover"
            return IndicatorResult(self.name, Signal.BUY, f"score {bull_score}/6, {structure}, {trigger}")

        if bear_score >= self.min_score and (bearish_pullback or macd_bear_cross):
            trigger = "pullback breakdown" if bearish_pullback else "MACD crossover"
            return IndicatorResult(self.name, Signal.SELL, f"score {bear_score}/6, {structure}, {trigger}")

        return IndicatorResult(self.name, Signal.HOLD, f"bull {bull_score}/6, bear {bear_score}/6, {structure}")
