"""Sends alert messages to a Telegram chat via the Bot API."""
import requests

from . import config


def send_message(text: str) -> None:
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        print("[telegram] TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID not set, printing instead:")
        print(text)
        return

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    resp = requests.post(
        url,
        data={
            "chat_id": config.TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        },
        timeout=15,
    )
    if not resp.ok:
        print(f"[telegram] send failed: {resp.status_code} {resp.text}")
