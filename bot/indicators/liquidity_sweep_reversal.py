"""Liquidity Sweep Reversal.

Trades the stop-hunt reversal pattern: price wicks through a confirmed
prior swing high/low (clearing the stops resting there) then closes back
inside the range, suggesting the break was a liquidity grab rather than a
genuine breakout. Longs trigger on swept lows, shorts on swept highs.

Differences from the original strategy description, due to how this bot
works (a stateless per-scan check, not a live position manager):
  - The session-window filter (London/NY overlap) doesn't apply -- we
    only have daily bars, not intraday timestamps -- so it's omitted.
  - Breakeven stop management, the live performance dashboard, and
    persisted chart lines are position-tracking features; this bot
    doesn't hold open positions between scans. The SL/TP levels below
    are computed and included in the alert as reference info only.

Warning (carried over from the original): this is fundamentally a
mean-reversion pattern. In a strongly trending market, sweeps frequently
continue rather than reverse -- no filter here eliminates that risk. Not
financial advice.
"""
import pandas as pd

from .base import Indicator, IndicatorResult, Signal


def _atr(df: pd.DataFrame, period: int) -> pd.Series:
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


def _find_pivots(values: pd.Series, bars: int, is_high: bool) -> list[tuple[int, float]]:
    """Confirmed pivots: a bar whose value is the strict max/min within
    `bars` bars on both sides. Returns (index-into-`values`, price) pairs.
    """
    pivots = []
    n = len(values)
    for i in range(bars, n - bars):
        window = values.iloc[i - bars: i + bars + 1]
        val = values.iloc[i]
        if is_high and val == window.max() and (window == val).sum() == 1:
            pivots.append((i, val))
        elif not is_high and val == window.min() and (window == val).sum() == 1:
            pivots.append((i, val))
    return pivots


class LiquiditySweepReversal(Indicator):
    name = "liquidity_sweep_reversal"

    def __init__(
        self,
        pivot_bars: int = 10,
        atr_period: int = 14,
        atr_stop_buffer: float = 0.25,
        min_stop_atr: float = 0.5,
        reward_risk_ratio: float = 2.0,
        level_expiry_bars: int = 60,
        min_level_distance_atr: float = 0.5,
        require_volume_spike: bool = True,
        volume_spike_mult: float = 1.5,
        volume_ma_period: int = 20,
        require_rejection_wick: bool = True,
        wick_body_ratio: float = 1.3,
        require_next_bar_confirmation: bool = True,
        allow_long: bool = True,
        allow_short: bool = True,
    ):
        self.pivot_bars = pivot_bars
        self.atr_period = atr_period
        self.atr_stop_buffer = atr_stop_buffer
        self.min_stop_atr = min_stop_atr
        self.reward_risk_ratio = reward_risk_ratio
        self.level_expiry_bars = level_expiry_bars
        self.min_level_distance_atr = min_level_distance_atr
        self.require_volume_spike = require_volume_spike
        self.volume_spike_mult = volume_spike_mult
        self.volume_ma_period = volume_ma_period
        self.require_rejection_wick = require_rejection_wick
        self.wick_body_ratio = wick_body_ratio
        self.require_next_bar_confirmation = require_next_bar_confirmation
        self.allow_long = allow_long
        self.allow_short = allow_short

    def _active_levels(self, df: pd.DataFrame, as_of: int, atr: pd.Series, is_high: bool) -> list[float]:
        """Confirmed pivot levels still active (not expired, not a near-duplicate
        of one already kept) as of bar index `as_of`.
        """
        series = df["High"] if is_high else df["Low"]
        lookback_start = max(0, as_of - self.level_expiry_bars - self.pivot_bars * 2)
        window = series.iloc[lookback_start: as_of + 1].reset_index(drop=True)
        pivots = _find_pivots(window, self.pivot_bars, is_high)

        levels: list[float] = []
        for local_idx, price in pivots:
            global_idx = lookback_start + local_idx
            confirmed_at = global_idx + self.pivot_bars
            if confirmed_at > as_of:
                continue  # not confirmed yet as of this bar
            if as_of - confirmed_at > self.level_expiry_bars:
                continue  # expired

            atr_here = atr.iloc[global_idx]
            if pd.isna(atr_here):
                atr_here = atr.iloc[as_of]
            if any(abs(price - lvl) < self.min_level_distance_atr * atr_here for lvl in levels):
                continue  # too close to an already-kept level, skip to reduce clutter
            levels.append(price)

        return levels

    def evaluate(self, df: pd.DataFrame) -> IndicatorResult:
        min_bars = max(self.level_expiry_bars, self.volume_ma_period, self.atr_period) + self.pivot_bars * 2 + 5
        if len(df) < min_bars:
            return IndicatorResult(self.name, Signal.HOLD, "not enough data")

        atr = _atr(df, self.atr_period)
        volume_ma = df["Volume"].rolling(self.volume_ma_period).mean()

        i = len(df) - 1  # latest closed bar
        check_i = i - 1 if self.require_next_bar_confirmation else i

        swing_lows = self._active_levels(df, check_i, atr, is_high=False)
        swing_highs = self._active_levels(df, check_i, atr, is_high=True)

        bar = df.iloc[check_i]
        body = abs(bar["Close"] - bar["Open"])
        lower_wick = min(bar["Open"], bar["Close"]) - bar["Low"]
        upper_wick = bar["High"] - max(bar["Open"], bar["Close"])

        # Sweep = wicked past the level, but closed back on the safe side of it.
        bullish_level = next((lvl for lvl in swing_lows if bar["Low"] < lvl <= bar["Close"]), None)
        bearish_level = next((lvl for lvl in swing_highs if bar["High"] > lvl >= bar["Close"]), None)

        if self.require_rejection_wick:
            if bullish_level is not None and lower_wick < body * self.wick_body_ratio:
                bullish_level = None
            if bearish_level is not None and upper_wick < body * self.wick_body_ratio:
                bearish_level = None

        if self.require_volume_spike:
            vol_avg = volume_ma.iloc[check_i]
            vol_ok = not pd.isna(vol_avg) and bar["Volume"] > vol_avg * self.volume_spike_mult
            if not vol_ok:
                bullish_level = None
                bearish_level = None

        if self.require_next_bar_confirmation:
            confirm_bar = df.iloc[i]
            if bullish_level is not None and confirm_bar["Close"] <= bar["Close"]:
                bullish_level = None
            if bearish_level is not None and confirm_bar["Close"] >= bar["Close"]:
                bearish_level = None

        entry_price = df["Close"].iloc[i]
        atr_now = atr.iloc[i]

        if self.allow_long and bullish_level is not None:
            stop = min(bar["Low"] - atr_now * self.atr_stop_buffer, entry_price - atr_now * self.min_stop_atr)
            risk = entry_price - stop
            target = entry_price + risk * self.reward_risk_ratio
            return IndicatorResult(
                self.name, Signal.BUY,
                f"swept low {bullish_level:.2f} -> entry {entry_price:.2f}, "
                f"SL {stop:.2f}, TP {target:.2f} (R:R {self.reward_risk_ratio:.1f})",
            )

        if self.allow_short and bearish_level is not None:
            stop = max(bar["High"] + atr_now * self.atr_stop_buffer, entry_price + atr_now * self.min_stop_atr)
            risk = stop - entry_price
            target = entry_price - risk * self.reward_risk_ratio
            return IndicatorResult(
                self.name, Signal.SELL,
                f"swept high {bearish_level:.2f} -> entry {entry_price:.2f}, "
                f"SL {stop:.2f}, TP {target:.2f} (R:R {self.reward_risk_ratio:.1f})",
            )

        return IndicatorResult(self.name, Signal.HOLD, "no active sweep")
