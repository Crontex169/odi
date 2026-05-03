"""Persistence + diffing of restaurant button states.

Stored on disk as a small JSON map ``{key: "active" | "disabled"}`` so that
restarting the watcher does not re-fire alerts for buttons that were already
active when the previous run ended.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from config import STATE_FILE
from src.scraper import ButtonStatus


@dataclass(frozen=True)
class Transition:
    key: str
    name: str
    previous: str
    current: str

    @property
    def became_active(self) -> bool:
        return self.previous == "disabled" and self.current == "active"


def load_state(path: Path = STATE_FILE) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_state(state: dict[str, str], path: Path = STATE_FILE) -> None:
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def compute_transitions(
    previous: dict[str, str], statuses: Iterable[ButtonStatus]
) -> list[Transition]:
    """Return the diffs between ``previous`` state and the latest ``statuses``."""
    transitions: list[Transition] = []
    for status in statuses:
        prev_label = previous.get(status.key, "unknown")
        if prev_label != status.state_label:
            transitions.append(
                Transition(
                    key=status.key,
                    name=status.name,
                    previous=prev_label,
                    current=status.state_label,
                )
            )
    return transitions


def snapshot(statuses: Iterable[ButtonStatus]) -> dict[str, str]:
    """Reduce the latest statuses down to the form we persist."""
    return {status.key: status.state_label for status in statuses}
