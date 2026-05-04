"""HTTP scraper for getodi.com.

Builds a ``requests.Session`` from cookies captured by ``cookie_helper`` and
parses the response with ``lxml`` so the XPaths the user supplied work
verbatim - no rewrite into CSS selectors.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import requests
from lxml import html as lxml_html

from config import REQUEST_TIMEOUT_SECONDS, TARGETS, URL, USER_AGENT


class CookiesExpiredError(RuntimeError):
    """Raised when the response indicates we are no longer logged in."""


@dataclass(frozen=True)
class ButtonStatus:
    """Snapshot of a single restaurant button at one point in time."""

    key: str
    name: str
    is_active: bool
    raw_class: str

    @property
    def state_label(self) -> str:
        return "active" if self.is_active else "disabled"


def build_session(cookies: Iterable[dict]) -> requests.Session:
    """Build a Session pre-loaded with Selenium-style cookie dicts."""
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
        }
    )
    for cookie in cookies:
        session.cookies.set(
            name=cookie["name"],
            value=cookie["value"],
            domain=cookie.get("domain"),
            path=cookie.get("path", "/"),
        )
    return session


def fetch_page(session: requests.Session, url: str = URL) -> str:
    """GET the watch URL, raising ``CookiesExpiredError`` if logged out."""
    response = session.get(url, timeout=REQUEST_TIMEOUT_SECONDS, allow_redirects=True)

    final_url = response.url.lower()
    if response.status_code in (401, 403):
        raise CookiesExpiredError(
            f"HTTP {response.status_code} from {url} - session is no longer valid."
        )
    if "login" in final_url or "sign-in" in final_url:
        raise CookiesExpiredError(
            f"Redirected to login page ({response.url}) - cookies have expired."
        )
    response.raise_for_status()
    return response.text


def _xpath_first_text(tree, xpath: str) -> str:
    """Return the first text node matched by ``xpath`` (stripped), or ''."""
    matches = tree.xpath(xpath)
    if not matches:
        return ""
    first = matches[0]
    if hasattr(first, "text_content"):
        return first.text_content().strip()
    return str(first).strip()


def parse_statuses(html_text: str) -> list[ButtonStatus]:
    """Extract a :class:`ButtonStatus` for every configured target.

    Instead of relying on fragile positional XPaths (``div[N]``), we iterate
    over **all** ``div.menu-box`` cards on the page and match each target by
    its ``menu_name`` against the text inside ``div.menu-restaurant``.  This
    makes the scraper resilient to card reordering.
    """
    tree = lxml_html.fromstring(html_text)

    # Build a lookup: lowercase menu-restaurant text → (name, button element)
    menu_boxes = tree.xpath("//div[contains(@class, 'menu-box')]")

    # Map: (lowercased menu_name, lowercased restaurant_title) → (display_name, restaurant_title, button_classes)
    card_map: dict[tuple[str, str], tuple[str, str, str]] = {}
    for box in menu_boxes:
        name_els = box.xpath(".//div[contains(@class, 'menu-restaurant')]")
        title_els = box.xpath(".//div[contains(@class, 'menu-title')]")
        btn_els = box.xpath(".//div[contains(@class, 'menu-btn-take')]")

        display_name = name_els[0].text_content().strip() if name_els else ""
        restaurant_title = title_els[0].text_content().strip() if title_els else ""

        # The second menu-btn-take is the "Askıdan al" button that toggles
        # between active and disabled.  Fall back to the first if only one.
        if len(btn_els) >= 2:
            btn_el = btn_els[1]
        elif btn_els:
            btn_el = btn_els[0]
        else:
            btn_el = None

        raw_class = (btn_el.get("class") if btn_el is not None else "") or ""

        # Use both menu name and restaurant title as the key to distinguish
        # different restaurants offering the same menu.
        key = (display_name.lower(), restaurant_title.lower())
        # Only keep the first occurrence (the "indirimli al" section at the top
        # of the page usually duplicates cards; the second, with the disabled
        # button, is the one we care about).
        if key not in card_map:
            card_map[key] = (display_name, restaurant_title, raw_class)

    results: list[ButtonStatus] = []
    for target in TARGETS:
        target_menu = target["menu_name"].lower()
        target_rest = target.get("restaurant_name", "").lower()

        found_card = None
        for (menu_key, rest_key), (display_name, restaurant_title, raw_class) in card_map.items():
            if menu_key == target_menu:
                if target_rest:
                    if target_rest in rest_key:
                        found_card = (display_name, restaurant_title, raw_class)
                        break
                else:
                    found_card = (display_name, restaurant_title, raw_class)
                    break

        if found_card:
            display_name, restaurant_title, raw_class = found_card
            class_tokens = raw_class.split()
            is_active = "disabled" not in class_tokens
            label = f"{display_name} — {restaurant_title}" if restaurant_title else display_name
        else:
            # Target not found on page — treat as disabled and warn.
            raw_class = ""
            is_active = False
            label = f"{target['menu_name']} (NOT FOUND ON PAGE)"

        results.append(
            ButtonStatus(
                key=target["key"],
                name=label,
                is_active=is_active,
                raw_class=raw_class,
            )
        )
    return results

