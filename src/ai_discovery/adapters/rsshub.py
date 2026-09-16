"""RSSHub bridge for feedless public sources (optional, config-gated)."""

from __future__ import annotations

from .feed import FeedEntry, parse_feed

DEFAULT_BASE = "http://localhost:1200"


def rsshub_url(route: str, *, base: str = DEFAULT_BASE) -> str:
    route = route if route.startswith("/") else f"/{route}"
    return f"{base}{route}"


def parse_rsshub(content: bytes, *, limit: int = 20) -> list[FeedEntry]:
    return parse_feed(content, limit=limit)
