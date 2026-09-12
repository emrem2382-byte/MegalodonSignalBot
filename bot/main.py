"""Entry point: scan all configured tickers and send Telegram BUY alerts.

Run locally with:   python -m bot.main
Run in CI with:      see .github/workflows/signals.yml
"""
import html

from . import config, data, positions, state, telegram
from .engine import evaluate_ticker
from .indicators.base import IndicatorResult

_MARK = {"BUY": "✅", "SELL": "🔻", "HOLD": "➖"}

# Технически имена (r.name), останали на английски заради backtest скриптовете --
# тук само за показване в Telegram превеждаме/изчистваме за четимост.
_DISPLAY_NAME = {
    "sma_ema_crossover": "SMA/EMA пресичане",
    "rsi": "RSI",
    "macd": "MACD",
    "fia_trend_momentum": "FIA Тренд+Моментум",
    "liquidity_sweep_reversal": "Liquidity Sweep",
    "bollinger_bands": "Bollinger Bands",
    "stochastic": "Stochastic",
    "adx_dmi": "ADX/DMI",
    "golden_cross": "Golden Cross",
}


def format_message(ticker: str, results: list[IndicatorResult]) -> str:
    lines = [f"🟢 <b>BUY сигнал</b> — <code>{html.escape(ticker)}</code>", ""]
    for r in results:
        display_name = _DISPLAY_NAME.get(r.name, r.name)
        lines.append(f"{_MARK[r.signal.value]} {html.escape(display_name)}: {html.escape(r.detail)}")
    lines.append("")
    lines.append("<i>Не е финансов съвет — само автоматичен технически сигнал.</i>")
    return "\n".join(lines)


def main() -> None:
    tickers = config.load_tickers()
    if not tickers:
        print("[main] no tickers configured in config/tickers.txt")
        return

    signal_state = state.load_state()
    sent = 0

    for i, ticker in enumerate(tickers):
        if i > 0:
            data.polite_delay()  # pace requests so Yahoo doesn't throttle/block us

        df = data.fetch_history(ticker)
        if df.empty:
            print(f"[main] {ticker}: no data, skipping")
            continue

        fires, results = evaluate_ticker(df)
        if not fires:
            continue

        if state.already_signaled_today(signal_state, ticker, "buy"):
            print(f"[main] {ticker}: BUY already sent today, skipping")
            continue

        if telegram.send_message(format_message(ticker, results)):
            state.mark_signaled(signal_state, ticker, "buy")
            sent += 1
            print(f"[main] {ticker}: BUY signal sent")
        else:
            print(f"[main] {ticker}: BUY signal detected but Telegram send failed, will retry next scan")

    state.save_state(signal_state)
    print(f"[main] scan complete, {sent} signal(s) sent, {len(tickers)} ticker(s) checked")

    check_tracked_positions()


def check_tracked_positions() -> None:
    """Alerts on any tracked position (data/positions.json) whose stop-loss
    or take-profit was hit today, then drops it from the file.
    """
    tracked = positions.load_positions()
    if not tracked:
        return

    remaining, alerts = positions.check_positions(tracked, data.fetch_history)
    for msg in alerts:
        telegram.send_message(msg)
    positions.save_positions(remaining)
    if alerts:
        print(f"[main] {len(alerts)} position alert(s) sent")


if __name__ == "__main__":
    main()
