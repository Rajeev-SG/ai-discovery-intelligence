"""RSS/Atom feed adapter (feeds first — cheapest, most polite fetch mode)."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import feedparser
from dateutil import parser as date_parser

from ..hashing import canonicalise_url, normalise_text


@dataclass
class FeedEntry:
    title: str
    url: str
    canonical_url: str
    published_at: dt.datetime | None
    summary: str | None
    publisher_hint: str | None


def _entry_date(entry) -> dt.datetime | None:
    for key in ("published", "updated", "created"):
        value = entry.get(key)
        if not value:
            continue
        try:
            parsed = date_parser.parse(value)
        except (ValueError, OverflowError, TypeError):
            continue
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.UTC)
    return None


def parse_feed(content: bytes, *, limit: int = 20) -> list[FeedEntry]:
    parsed = feedparser.parse(content)
    feed_title = None
    if getattr(parsed, "feed", None):
        feed_title = parsed.feed.get("title")
    entries: list[FeedEntry] = []
    for entry in parsed.entries[:limit]:
        link = entry.get("link")
        if not link:
            continue
        summary = entry.get("summary") or entry.get("description")
        entries.append(
            FeedEntry(
                title=normalise_text(entry.get("title") or ""),
                url=link,
                canonical_url=canonicalise_url(link),
                published_at=_entry_date(entry),
                summary=normalise_text(summary) if summary else None,
                publisher_hint=feed_title,
            )
        )
    return entries
