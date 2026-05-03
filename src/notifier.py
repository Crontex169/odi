"""Telegram notifier - one HTTP POST, no third-party SDK."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

import requests
from dotenv import load_dotenv

from config import ENV_FILE, REQUEST_TIMEOUT_SECONDS

TELEGRAM_API_TEMPLATE = "https://api.telegram.org/bot{token}/sendMessage"

MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2


@dataclass(frozen=True)
class TelegramConfig:
    bot_token: str
    chat_id: str

    @classmethod
    def from_env(cls) -> "TelegramConfig":
        load_dotenv(ENV_FILE)
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
        if not token or not chat_id:
            raise RuntimeError(
                "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in .env "
                "(see .env.example)."
            )
        return cls(bot_token=token, chat_id=chat_id)


def send_message(config: TelegramConfig, text: str) -> bool:
    """Send ``text`` to the configured chat. Returns True on success.

    Retries up to ``MAX_RETRIES`` times on transient network errors.
    """
    url = TELEGRAM_API_TEMPLATE.format(token=config.bot_token)
    payload = {
        "chat_id": config.chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
            if response.ok:
                return True
            last_error = RuntimeError(
                f"Telegram API returned {response.status_code}: {response.text[:200]}"
            )
        except requests.RequestException as exc:
            last_error = exc

        if attempt < MAX_RETRIES:
            time.sleep(RETRY_BACKOFF_SECONDS * attempt)

    print(f"Failed to send Telegram message after {MAX_RETRIES} attempts: {last_error}")
    return False
