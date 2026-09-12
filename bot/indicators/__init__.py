from .adx_dmi import AdxDmi
from .base import Indicator, IndicatorResult, Signal
from .bollinger_bands import BollingerBands
from .fia_trend_momentum import FiaTrendMomentum
from .golden_cross import GoldenCross
from .liquidity_sweep_reversal import LiquiditySweepReversal
from .macd import Macd
from .rsi import Rsi
from .sma_ema_crossover import SmaEmaCrossover
from .stochastic import Stochastic

# Registry of active indicators -- add new instances here as they're built.
# Every entry runs on every ticker, every scan.
ALL_INDICATORS: list[Indicator] = [
    SmaEmaCrossover(),
    Rsi(),
    Macd(),
    FiaTrendMomentum(),
    LiquiditySweepReversal(),
    BollingerBands(),
    Stochastic(),
    AdxDmi(),
    GoldenCross(),
]

__all__ = ["Indicator", "IndicatorResult", "Signal", "ALL_INDICATORS"]
