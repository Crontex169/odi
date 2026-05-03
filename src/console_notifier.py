"""Console notifier - prints alerts to stdout.

Drop-in replacement for the Telegram notifier, intended for local testing so
you can watch the transition logic without sending real Telegram messages.
"""

from __future__ import annotations

import re
from datetime import datetime

BANNER = "=" * 70

_HTML_TAG = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    """Drop the HTML tags Telegram understands so the console output stays clean."""
    return _HTML_TAG.sub("", text)


def send_to_console(text: str) -> bool:
    """Render an alert to stdout. Returns True so it matches the Telegram contract."""
    cleaned = _strip_html(text)

    print()
    print(BANNER)
    print(f"  ALERT  [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
    print(BANNER)
    for line in cleaned.splitlines():
        print(f"  {line}")
    print(BANNER)
    print()
    return True
