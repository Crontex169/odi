"""Main polling loop.

Wires the scraper, state diffing and a notifier together. The notifier is a
single ``Callable[[str], bool]`` so the loop is agnostic to whether alerts go
to Telegram, the console (test mode), or both.
"""

from __future__ import annotations

import sys
import time
from datetime import datetime

import requests

from config import (
    HEARTBEAT_INTERVAL_SECONDS,
    POLL_INTERVAL_SECONDS,
    REMINDER_INTERVAL_SECONDS,
    URL,
)
from src.cookie_helper import load_cookies
from src.notifiers import Mode, Notifier, build_notifier
from src.scraper import (
    ButtonStatus,
    CookiesExpiredError,
    build_session,
    fetch_page,
    parse_statuses,
)
from src.state import (
    Transition,
    compute_transitions,
    load_state,
    save_state,
    snapshot,
)


def _format_alert(name: str, *, is_reminder: bool = False) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = "Hatırlatma: Hâlâ açık!" if is_reminder else "Odi siparis acildi!"
    return (
        f"<b>{header}</b>\n"
        f"<b>{name}</b> sipariş almaya başladı.\n"
        f"\n<a href=\"{URL}\">Hemen aç</a>\n"
        f"<i>{timestamp}</i>"
    )


def _format_heartbeat(statuses: list) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = ["<b>\U00002764 Bot çalışıyor</b>\n"]
    for s in statuses:
        icon = "\U0001F7E2" if s.is_active else "\U0001F534"
        lines.append(f"{icon} {s.name}")
    lines.append(f"\n<i>{timestamp}</i>")
    return "\n".join(lines)


def _format_status_line(status: ButtonStatus) -> str:
    marker = "OPEN " if status.is_active else "shut "
    return f"  [{marker}] {status.name} ({status.key})"


def run_once(
    session,
    notify: Notifier,
    state: dict[str, str],
    last_alert_times: dict[str, float],
) -> dict[str, str]:
    """Single poll iteration. Returns the updated state map."""
    html_text = fetch_page(session)
    statuses = parse_statuses(html_text)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] checked:")
    for status in statuses:
        print(_format_status_line(status))

    now = time.time()

    # --- Handle transitions (disabled → active, etc.) ---
    transitions = compute_transitions(state, statuses)
    for transition in transitions:
        if transition.became_active:
            print(f"  -> ALERT: {transition.name} became active, sending notification ...")
            notify(_format_alert(transition.name))
            last_alert_times[transition.key] = now
        else:
            print(
                f"  -> note: {transition.name} {transition.previous} -> {transition.current}"
            )
            # Clear reminder timer when a restaurant goes inactive.
            last_alert_times.pop(transition.key, None)

    # --- Handle reminders for restaurants that stay active ---
    for status in statuses:
        if not status.is_active:
            continue
        # Skip if we just sent a transition alert above.
        if any(t.key == status.key and t.became_active for t in transitions):
            continue
        last_sent = last_alert_times.get(status.key, 0.0)
        if now - last_sent >= REMINDER_INTERVAL_SECONDS:
            print(f"  -> REMINDER: {status.name} still open, re-sending ...")
            notify(_format_alert(status.name, is_reminder=True))
            last_alert_times[status.key] = now

    return snapshot(statuses)


def run(mode: Mode = "telegram", *, max_runtime_minutes: int = 0) -> int:
    print(f"Loading configuration ... (notifier mode: {mode})")
    try:
        notify = build_notifier(mode)
    except (RuntimeError, ValueError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    try:
        cookies = load_cookies()
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    session = build_session(cookies)
    state = load_state()

    # Track when we last sent an alert per restaurant key (in-memory only).
    last_alert_times: dict[str, float] = {}
    last_heartbeat: float = 0.0  # send first heartbeat on startup

    deadline = (
        time.time() + max_runtime_minutes * 60 if max_runtime_minutes > 0 else None
    )

    runtime_msg = f" Max runtime: {max_runtime_minutes}min." if deadline else ""
    print(
        f"Watcher started. Polling {URL} every {POLL_INTERVAL_SECONDS}s. "
        f"Reminders every {REMINDER_INTERVAL_SECONDS}s while open.{runtime_msg} "
        "Press Ctrl+C to stop."
    )

    try:
        while True:
            if deadline and time.time() >= deadline:
                print(f"\nMax runtime ({max_runtime_minutes}min) reached. Exiting.")
                return 0

            try:
                state = run_once(session, notify, state, last_alert_times)
                save_state(state)

                # --- Heartbeat: "I'm alive" every HEARTBEAT_INTERVAL_SECONDS ---
                now = time.time()
                if now - last_heartbeat >= HEARTBEAT_INTERVAL_SECONDS:
                    statuses = parse_statuses(fetch_page(session))
                    print(f"  -> HEARTBEAT: sending alive signal ...")
                    notify(_format_heartbeat(statuses))
                    last_heartbeat = now
            except CookiesExpiredError as exc:
                msg = (
                    "Odi watcher: cookies expired. Please re-run "
                    "<code>python get_cookies.py</code> and start the watcher again.\n"
                    f"<i>{exc}</i>"
                )
                print(msg, file=sys.stderr)
                notify(msg)
                return 3
            except requests.RequestException as exc:
                print(f"Network error (will retry): {exc}", file=sys.stderr)
            except Exception as exc:
                print(f"Unexpected error (will retry): {exc!r}", file=sys.stderr)

            time.sleep(POLL_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\nStopped by user.")
        return 0
