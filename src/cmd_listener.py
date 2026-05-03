"""Telegram /working command listener.

Runs in a background thread and responds to /working commands with the
current status of all watched restaurants.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime

import requests

from config import REQUEST_TIMEOUT_SECONDS, URL
from src.notifier import TelegramConfig, send_message


POLL_INTERVAL = 2  # seconds between checking for new commands


class CommandListener:
    """Polls Telegram getUpdates and responds to /working."""

    def __init__(self, config: TelegramConfig, get_statuses_fn):
        self._config = config
        self._get_statuses = get_statuses_fn
        self._offset = 0
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print("  Telegram /working command listener started.")

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._check_updates()
            except Exception as exc:
                print(f"  [cmd-listener] error: {exc!r}")
            self._stop.wait(POLL_INTERVAL)

    def _check_updates(self) -> None:
        url = f"https://api.telegram.org/bot{self._config.bot_token}/getUpdates"
        params = {"offset": self._offset, "timeout": 1, "allowed_updates": ["message"]}

        try:
            resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
            if not resp.ok:
                return
            data = resp.json()
        except (requests.RequestException, ValueError):
            return

        for update in data.get("result", []):
            self._offset = update["update_id"] + 1
            message = update.get("message", {})
            text = (message.get("text") or "").strip().lower()

            if text == "/working" or text.startswith("/working@"):
                self._handle_working(message)

    def _handle_working(self, message: dict) -> None:
        chat_id = message.get("chat", {}).get("id")
        if chat_id is None:
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        statuses = self._get_statuses()
        if statuses is None:
            reply = (
                "<b>\u2705 Bot çalışıyor</b>\n"
                "\n<i>Henüz ilk kontrol yapılmadı.</i>\n"
                f"<i>{timestamp}</i>"
            )
        else:
            lines = ["<b>\u2705 Bot çalışıyor</b>\n"]
            for s in statuses:
                icon = "\U0001F7E2" if s.is_active else "\U0001F534"
                lines.append(f"{icon} {s.name}")
            lines.append(f"\n<a href=\"{URL}\">Odi'ye git</a>")
            lines.append(f"<i>{timestamp}</i>")
            reply = "\n".join(lines)

        # Send reply to the same chat the command came from.
        send_url = f"https://api.telegram.org/bot{self._config.bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": reply,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        try:
            requests.post(send_url, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
        except requests.RequestException:
            pass
