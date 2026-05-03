"""One-shot notification test.

Fires a fake "disabled -> active" alert through the chosen notifier so you can
verify the wiring without waiting for a real transition on getodi.com.

Usage:
    python test_notify.py             # console (default for the test script)
    python test_notify.py --telegram  # send a real Telegram message
    python test_notify.py --both      # both
"""

from __future__ import annotations

import argparse
import sys

from src.notifiers import Mode, build_notifier
from src.state import Transition
from src.watcher import _format_alert


def _parse_mode(argv: list[str]) -> Mode:
    parser = argparse.ArgumentParser(description="Send a one-off test alert.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--console", dest="mode", action="store_const", const="console",
        help="Print to stdout (default for this script).",
    )
    group.add_argument(
        "--telegram", dest="mode", action="store_const", const="telegram",
        help="Send via Telegram.",
    )
    group.add_argument(
        "--both", dest="mode", action="store_const", const="both",
        help="Send via Telegram AND print to stdout.",
    )
    parser.set_defaults(mode="console")
    return parser.parse_args(argv).mode


def main() -> int:
    mode = _parse_mode(sys.argv[1:])
    print(f"Sending test alert via: {mode}")

    try:
        notify = build_notifier(mode)
    except (RuntimeError, ValueError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    fake = Transition(
        key="queens_burger",
        name="Queen's Burger (Hacettepe BAM) [TEST]",
        previous="disabled",
        current="active",
    )
    ok = notify(_format_alert(fake))

    if ok:
        print("Test alert delivered.")
        return 0
    print("Test alert FAILED to deliver.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
