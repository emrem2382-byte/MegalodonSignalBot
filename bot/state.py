"""Tracks which (ticker, signal) pairs already fired today, to avoid spam."""
import json
from datetime import datetime, timezone

from . import config


def load_state() -> dict:
    if not config.STATE_FILE.exists():
        return {}
    try:
        return json.loads(config.STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_state(state: dict) -> None:
    config.STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    config.STATE_FILE.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def _key(ticker: str, signal_name: str) -> str:
    return f"{ticker}:{signal_name}"


def already_signaled_today(state: dict, ticker: str, signal_name: str) -> bool:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return state.get(_key(ticker, signal_name)) == today


def mark_signaled(state: dict, ticker: str, signal_name: str) -> None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    state[_key(ticker, signal_name)] = today
