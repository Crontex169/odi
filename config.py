"""Static configuration for the Odi watcher.

All file-system paths are anchored to this file's directory so the app behaves
the same regardless of where it is launched from.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

URL = "https://getodi.com/student/?city=6"

POLL_INTERVAL_SECONDS = 10

REMINDER_INTERVAL_SECONDS = 300  # Re-send alert every 5 min while still open


REQUEST_TIMEOUT_SECONDS = 15

COOKIES_FILE = BASE_DIR / "cookies.json"
STATE_FILE = BASE_DIR / "state.json"
ENV_FILE = BASE_DIR / ".env"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/147.0.0.0 Safari/537.36"
)

TARGETS = [
    {
        "key": "pilavita_city",
        "menu_name": "Pilav - Döner Menü",
    },
    {
        "key": "sinyor_chef",
        "menu_name": "seçmeli sos makarna tavuk menü",
    },
    {
        "key": "queens_burger",
        "menu_name": "Classic Burger Menü",
    },
]
