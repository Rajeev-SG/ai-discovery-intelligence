"""Robots.txt classification with the project's own User-Agent.

Bug fixed (2026-09-17): ``urllib.robotparser.RobotFileParser.read()`` and
default-User-Agent fetchers hit hosts that 403 untrusted agents and then
mis-read the 403 body (or an HTML error page) as robots directives, producing
a false ``Disallow: /``. This module fetches robots.txt with the project UA,
parses the fetched body explicitly with Protego (the Scrapy 2.19 default
parser) and classifies failure states explicitly: a 401/403 robots fetch is a
*deny*, an unreachable host is *unknown*, and a 404/410 (or a body with no
disallow directives) is *allow with no directives* — never a false deny.
"""

from __future__ import annotations

from urllib.parse import urlsplit

import httpx
from protego import Protego

from .settings import get_settings

ALLOW = "allow"
DENY = "deny"  # 401/403 — access control, never bypassed
UNKNOWN = "unknown"  # unreachable / 5xx — surfaced, never crawled
NO_DIRECTIVES = {404, 410}  # standard "no rules published"


def robots_url_for(url: str) -> str:
    """The robots.txt URL for any page URL."""
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}/robots.txt"


def classify_status(status: int) -> str:
    """HTTP-status-only classification, mirroring the Scrapy spider's policy."""
    if status in (401, 403):
        return DENY
    if status in NO_DIRECTIVES or 200 <= status < 300:
        return ALLOW
    return UNKNOWN


def parse_robots_body(body: str | None) -> Protego:
    """Parse robots.txt directives from a fetched body (never from a guess)."""
    return Protego.parse(body or "")


def robots_policy(
    url: str,
    *,
    client: httpx.Client | None = None,
    user_agent: str | None = None,
    timeout: float = 15.0,
) -> tuple[str, Protego | None]:
    """Fetch and classify robots.txt for ``url``.

    Returns ``(state, parser)``. ``state`` is one of ALLOW / DENY / UNKNOWN.
    The parser is present whenever a body was readable (ALLOW or DENY),
    so the caller can honour real per-path directives instead of a blanket
    host-level guess.
    """
    ua = user_agent or get_settings().user_agent
    robots_url = robots_url_for(url)
    owned = client is None
    client = client or httpx.Client(
        headers={"User-Agent": ua}, follow_redirects=True, timeout=timeout
    )
    try:
        response = client.get(robots_url)
    except (httpx.HTTPError, OSError):
        return UNKNOWN, None
    finally:
        if owned:
            client.close()
    state = classify_status(response.status_code)
    if state == UNKNOWN:
        return UNKNOWN, None
    return state, parse_robots_body(response.text)


def can_fetch(url: str, parser: Protego, *, user_agent: str | None = None) -> bool:
    """True when the project UA may fetch ``url`` under the parsed directives."""
    ua = user_agent or get_settings().user_agent
    return bool(parser.can_fetch(url, ua))
