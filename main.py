"""Entry point for the Odi watcher.

Usage:
    python main.py                # default: send alerts via Telegram
    python main.py --test         # alias for --console (no Telegram, prints to stdout)
    python main.py --console      # print alerts to stdout only (test mode)
    python main.py --telegram     # explicit Telegram-only (default)
    python main.py --both         # send to Telegram AND print to stdout
    python main.py --max-runtime 350  # auto-stop after 350 minutes (for CI)
"""

from __future__ import annotations

import argparse
import sys

from src.notifiers import Mode
from src.watcher import run


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Watch Odi restaurant buttons and alert on disabled -> active."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--telegram",
        dest="mode",
        action="store_const",
        const="telegram",
        help="Send alerts via Telegram only (default).",
    )
    group.add_argument(
        "--console",
        dest="mode",
        action="store_const",
        const="console",
        help="Print alerts to the terminal only (test mode, no Telegram).",
    )
    group.add_argument(
        "--test",
        dest="mode",
        action="store_const",
        const="console",
        help="Alias for --console.",
    )
    group.add_argument(
        "--both",
        dest="mode",
        action="store_const",
        const="both",
        help="Send via Telegram AND print to terminal.",
    )
    parser.add_argument(
        "--max-runtime",
        type=int,
        default=0,
        metavar="MINUTES",
        help="Auto-stop after this many minutes (0 = unlimited). Useful for CI.",
    )
    parser.set_defaults(mode="telegram")
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args(sys.argv[1:])
    sys.exit(run(args.mode, max_runtime_minutes=args.max_runtime))
