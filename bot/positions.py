"""Tracks positions you've manually entered (ticker + stop-loss / take-profit)
and alerts in Telegram when price breaches either level.

This bot never places real orders -- it doesn't know what you actually did
with your broker. This is a parallel awareness alert only: you add a
position to data/positions.json yourself (ticker, entry price, stop-loss,
optional take-profit), and every scan checks whether the day's range
crossed either level. Once triggered, the position is removed from the
file so it doesn't alert again.
"""
import html
from typing import Callable

import pandas as pd

from . import config

POSITIONS_FILE = config.BASE_DIR / "data" / "positions.json"


def load_positions() -> dict:
    if not POSITIONS_FILE.exists():
        return {}
    import json
    try:
        return json.loads(POSITIONS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_positions(positions: dict) -> None:
    import json
    POSITIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    POSITIONS_FILE.write_text(
        json.dumps(positions, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )


def _format_alert(ticker: str, label: str, level: float, current: float, entry: float | None) -> str:
    lines = [f"{label} — <code>{html.escape(ticker)}</code>", ""]
    lines.append(f"Ниво: {level:.2f}")
    lines.append(f"Текуща цена: {current:.2f}")
    if entry is not None:
        pnl_pct = (current / entry - 1) * 100
        lines.append(f"Вход: {entry:.2f} (P&L: {pnl_pct:+.1f}%)")
    lines.append("")
    lines.append("<i>Информативно известие — не е автоматична поръчка. Провери и реши сам.</i>")
    return "\n".join(lines)


def check_positions(
    positions: dict, fetch_history: Callable[[str], pd.DataFrame]
) -> tuple[dict, list[str]]:
    """Checks every tracked position against fresh price data.

    Returns (remaining_positions, alert_messages). A position that hits
    its stop-loss or take-profit is dropped from remaining_positions --
    the watch is considered complete once it fires once.
    """
    remaining: dict = {}
    messages: list[str] = []

    for ticker, pos in positions.items():
        df = fetch_history(ticker)
        if df.empty:
            remaining[ticker] = pos  # couldn't fetch this run, keep watching
            continue

        bar = df.iloc[-1]
        stop_loss = pos.get("stop_loss")
        take_profit = pos.get("take_profit")
        entry_price = pos.get("entry_price")

        hit_stop = stop_loss is not None and bar["Low"] <= stop_loss
        hit_target = take_profit is not None and bar["High"] >= take_profit

        if hit_stop:
            messages.append(_format_alert(ticker, "🔴 STOP LOSS", stop_loss, bar["Close"], entry_price))
        elif hit_target:
            messages.append(_format_alert(ticker, "🎯 TAKE PROFIT", take_profit, bar["Close"], entry_price))
        else:
            remaining[ticker] = pos

    return remaining, messages
