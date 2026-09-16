"""Page → normalised document, via Trafilatura (adopted extraction OSS)."""

from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import dataclass

from dateutil import parser as date_parser

from ..hashing import normalise_text


@dataclass
class ExtractedDocument:
    title: str | None
    author: str | None
    published_at: dt.datetime | None
    published_at_source: str | None
    modified_at: dt.datetime | None
    text: str
    language: str | None
    site_name: str | None
    extractor: str


def _parse_dt(value: object) -> dt.datetime | None:
    if not value:
        return None
    try:
        parsed = date_parser.parse(str(value))
    except (ValueError, OverflowError, TypeError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.UTC)
    return parsed


def _json_ld_dates(html: str) -> tuple[dt.datetime | None, dt.datetime | None, str | None]:
    published = modified = None
    author = None
    for match in re.finditer(
        r"<script[^>]+application/ld\+json[^>]*>(.*?)</script>", html, re.DOTALL | re.IGNORECASE
    ):
        try:
            payload = json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            continue
        for node in payload if isinstance(payload, list) else [payload]:
            if not isinstance(node, dict):
                continue
            graph = node.get("@graph") if isinstance(node.get("@graph"), list) else [node]
            for entry in graph:
                if not isinstance(entry, dict):
                    continue
                published = published or _parse_dt(entry.get("datePublished"))
                modified = modified or _parse_dt(entry.get("dateModified"))
                if not author:
                    raw_author = entry.get("author")
                    if isinstance(raw_author, dict):
                        author = raw_author.get("name")
                    elif isinstance(raw_author, list) and raw_author:
                        first = raw_author[0]
                        author = first.get("name") if isinstance(first, dict) else str(first)
                    elif isinstance(raw_author, str):
                        author = raw_author
    return published, modified, author


def _is_day_precision(value: dt.datetime, reference: dt.datetime) -> bool:
    """True when `value` is midnight on the same day as a more precise `reference`."""
    return (
        value.hour == value.minute == value.second == value.microsecond == 0
        and value.date() == reference.date()
        and (reference.hour or reference.minute or reference.second)
    )


def extract_document(
    html: str, *, url: str, feed_published: dt.datetime | None = None
) -> ExtractedDocument:
    """Extract main text + metadata. Distinguishes published vs modified dates.

    Published date precedence: explicit page metadata/JSON-LD `datePublished`
    beats a feed-supplied date, which beats nothing. `dateModified` is stored
    separately and never presented as the publication date (see issue #4
    finding on the Ahrefs living page).
    """
    import trafilatura

    published = modified = None
    author = None
    site_name = None
    language = None
    extractor = "trafilatura"
    text = ""
    title = None

    try:
        doc = trafilatura.bare_extraction(html, url=url, with_metadata=True, include_comments=False)
    except Exception:
        doc = None

    if doc is not None:
        title = getattr(doc, "title", None)
        author = getattr(doc, "author", None)
        published = _parse_dt(getattr(doc, "date", None))
        text = getattr(doc, "text", "") or ""
        site_name = getattr(doc, "sitename", None)
        language = getattr(doc, "language", None)

    html_published, html_modified, html_author = _json_ld_dates(html)

    published_source: str | None = None
    # Trafilatura normalises a date to day precision (midnight). When structured
    # data carries the same day with a real time, keep the precise value so the
    # stored publication timestamp is not silently coarsened.
    if html_published is not None and (
        published is None or _is_day_precision(published, html_published)
    ):
        published = html_published
        published_source = "json_ld"
    elif published is not None:
        published_source = "meta"
    elif feed_published is not None:
        published = feed_published
        published_source = "feed"
    # `dateModified` is captured separately and is never presented as publication.
    modified = html_modified
    if not author:
        author = html_author

    if not text:
        # Last resort: keep a whitespace-normalised HTML-stripped excerpt so an
        # item is never stored with empty text and silently dropped.
        stripped = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
        stripped = re.sub(r"(?s)<[^>]+>", " ", stripped)
        text = normalise_text(stripped)
        extractor = "html_fallback"

    return ExtractedDocument(
        title=normalise_text(title) if title else None,
        author=author,
        published_at=published,
        published_at_source=published_source,
        modified_at=modified,
        text=normalise_text(text),
        language=language,
        site_name=site_name,
        extractor=extractor,
    )
