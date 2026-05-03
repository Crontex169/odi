"""One-time cookie capture for getodi.com.

Opens a visible Chrome window, takes you to the login page, waits for you to
sign in manually, then dumps the resulting session cookies to ``cookies.json``
in a format the requests-based watcher can load directly.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from config import COOKIES_FILE, URL


def _build_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--start-maximized")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    return webdriver.Chrome(options=options)


def capture_cookies(target_url: str = URL, output_path: Path = COOKIES_FILE) -> Path:
    """Open Chrome, wait for manual login, then persist cookies to disk.

    Returns the path the cookies were written to.
    """
    print("Launching Chrome ...")
    driver = _build_driver()
    try:
        print(f"Navigating to {target_url}")
        driver.get(target_url)

        print()
        print("=" * 70)
        print("  Log in to Odi in the Chrome window that just opened.")
        print("  Once you can see the restaurant list, come back here and")
        print("  press ENTER to save the session cookies.")
        print("=" * 70)
        print()
        try:
            input("Press ENTER after you have logged in ... ")
        except EOFError:
            print("No interactive stdin available - aborting.", file=sys.stderr)
            return output_path

        cookies = driver.get_cookies()
        if not cookies:
            print("WARNING: no cookies found. Are you sure you logged in?", file=sys.stderr)

        output_path.write_text(json.dumps(cookies, indent=2), encoding="utf-8")
        print(f"Saved {len(cookies)} cookies to {output_path}")
        return output_path
    finally:
        try:
            driver.quit()
        except Exception:
            pass


def load_cookies(path: Path = COOKIES_FILE) -> list[dict]:
    """Load cookies previously saved by :func:`capture_cookies`."""
    if not path.exists():
        raise FileNotFoundError(
            f"Cookie file not found at {path}. Run `python get_cookies.py` first."
        )
    return json.loads(path.read_text(encoding="utf-8"))
