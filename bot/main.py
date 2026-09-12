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


def format_message(ticker: str, results: list[IndicatorResult], auto_levels: dict | None) -> str:
    lines = [f"🟢 <b>BUY сигнал</b> — <code>{html.escape(ticker)}</code>", ""]
    for r in results:
        display_name = _DISPLAY_NAME.get(r.name, r.name)
        lines.append(f"{_MARK[r.signal.value]} {html.escape(display_name)}: {html.escape(r.detail)}")
    lines.append("")
    if auto_levels:
        lines.append(
            f"📍 Автоматично следене: вход {auto_levels['entry_price']:.2f}, "
            f"стоп {auto_levels['stop_loss']:.2f}, цел {auto_levels['take_profit']:.2f}"
        )
        lines.append("<i>Ще получиш известие, ако цената пробие стопа или целта.</i>")
        lines.append("")
    lines.append("<i>Не е финансов съвет — само автоматичен технически сигнал.</i>")
    return "\n".join(lines)


def main() -> None:
    tickers = config.load_tickers()
    if not tickers:
        print("[main] no tickers configured in config/tickers.txt")
        return

    signal_state = state.load_state()
    tracked_positions = positions.load_positions()

    # 1. Check positions tracked from earlier scans BEFORE this scan can add
    #    new ones -- a position should never be checked on the same bar it
    #    was created on.
    tracked_positions, position_alerts = positions.check_positions(tracked_positions, data.fetch_history)
    for msg in position_alerts:
        telegram.send_message(msg)
    if position_alerts:
        print(f"[main] {len(position_alerts)} position alert(s) sent")

    # 2. Scan for new BUY signals, auto-tracking each one that fires.
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

        auto_levels = positions.compute_auto_levels(df) if ticker not in tracked_positions else None
        message = format_message(ticker, results, auto_levels)

        if telegram.send_message(message):
            state.mark_signaled(signal_state, ticker, "buy")
            sent += 1
            print(f"[main] {ticker}: BUY signal sent")
            if positions.auto_track(ticker, auto_levels, tracked_positions):
                print(f"[main] {ticker}: auto-tracking (entry {auto_levels['entry_price']}, "
                      f"SL {auto_levels['stop_loss']}, TP {auto_levels['take_profit']})")
        else:
            print(f"[main] {ticker}: BUY signal detected but Telegram send failed, will retry next scan")

    state.save_state(signal_state)
    positions.save_positions(tracked_positions)
    print(f"[main] scan complete, {sent} signal(s) sent, {len(tickers)} ticker(s) checked")


if __name__ == "__main__":
    main()
