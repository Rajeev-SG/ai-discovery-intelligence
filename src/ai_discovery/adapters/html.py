"""Static-HTML adapter: fetch a page and extract it via Trafilatura."""

from __future__ import annotations

import datetime as dt

from ..hashing import canonicalise_url
from .feed import FeedEntry


def html_entry(
    url: str,
    *,
    title: str | None = None,
    published_at: dt.datetime | None = None,
    summary: str | None = None,
    publisher_hint: str | None = None,
) -> FeedEntry:
    return FeedEntry(
        title=title or url,
        url=url,
        canonical_url=canonicalise_url(url),
        published_at=published_at,
        summary=summary,
        publisher_hint=publisher_hint,
    )
