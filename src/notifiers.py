"""Notifier dispatch - hides which channel(s) are active behind a single callable.

The watcher only ever calls ``notify(text)``. This module knows how to build
that callable for any of the supported modes:

- ``"telegram"``  - send via the Telegram bot only
- ``"console"``   - print to stdout only (test mode)
- ``"both"``      - do both, in that order
"""

from __future__ import annotations

from typing import Callable, Iterable, Literal

from src.console_notifier import send_to_console
from src.notifier import TelegramConfig, send_message as send_telegram

Notifier = Callable[[str], bool]
Mode = Literal["telegram", "console", "both"]


def _telegram_notifier() -> Notifier:
    """Build a Telegram-bound notifier. Reads .env eagerly so failures surface early."""
    config = TelegramConfig.from_env()

    def notify(text: str) -> bool:
        return send_telegram(config, text)

    return notify


def _aggregate(notifiers: Iterable[Notifier]) -> Notifier:
    """Fan out a single message to every notifier; succeeds if any succeed."""
    notifiers = list(notifiers)

    def notify(text: str) -> bool:
        results = [n(text) for n in notifiers]
        return any(results)

    return notify


def build_notifier(mode: Mode) -> Notifier:
    """Return the single ``notify(text)`` callable the watcher should use."""
    if mode == "console":
        return send_to_console
    if mode == "telegram":
        return _telegram_notifier()
    if mode == "both":
        return _aggregate([_telegram_notifier(), send_to_console])
    raise ValueError(f"Unknown notifier mode: {mode!r}")
