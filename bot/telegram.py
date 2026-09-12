"""Sends alert messages to a Telegram chat via the Bot API."""
import requests

from . import config


def send_message(text: str) -> bool:
    """Returns True only if Telegram actually accepted the message."""
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        print("[telegram] TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID not set, printing instead:")
        print(text)
        return False

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    resp = requests.post(
        url,
        data={
            "chat_id": config.TELEGRAM_CHAT_ID,
            "text": text,
            # HTML, not Markdown: indicator names contain underscores
            # (sma_ema_crossover, fia_trend_momentum, ...), which Telegram's
            # legacy Markdown parser reads as italic markers and then fails
            # on ("can't find end of the entity") whenever there's an odd
            # count. HTML only needs &/</> escaped, which format_message
            # already does via html.escape.
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=15,
    )
    if not resp.ok:
        print(f"[telegram] send failed: {resp.status_code} {resp.text}")
        return False

    return True
