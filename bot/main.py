"""Entry point: scan all configured tickers and send Telegram BUY alerts.

Run locally with:   python -m bot.main
Run in CI with:      see .github/workflows/signals.yml
"""
import html

from . import config, data, state, telegram
from .engine import evaluate_ticker
from .indicators.base import IndicatorResult

_MARK = {"BUY": "✅", "SELL": "🔻", "HOLD": "➖"}


def format_message(ticker: str, results: list[IndicatorResult]) -> str:
    lines = [f"🟢 <b>BUY signal</b> — <code>{html.escape(ticker)}</code>", ""]
    for r in results:
        lines.append(f"{_MARK[r.signal.value]} {html.escape(r.name)}: {html.escape(r.detail)}")
    lines.append("")
    lines.append("<i>Not financial advice -- automated technical signal only.</i>")
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


if __name__ == "__main__":
    main()
