"""GDELT DOC 2.0 API adapter (open discovery source)."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from urllib.parse import urlencode

from dateutil import parser as date_parser

from ..hashing import canonicalise_url, normalise_text

GDELT_ENDPOINT = "https://api.gdeltproject.org/api/v2/doc/doc"


@dataclass
class DiscoveryHit:
    title: str
    url: str
    canonical_url: str
    published_at: dt.datetime | None
    provider: str
    query: str
    domain: str | None = None


def gdelt_url(query: str, *, max_records: int = 25, timespan: str = "30d") -> str:
    params = {
        "query": f"{query} sourcelang:english",
        "mode": "artlist",
        "format": "json",
        "maxrecords": str(max_records),
        "timespan": timespan,
        "sort": "datedesc",
    }
    return f"{GDELT_ENDPOINT}?{urlencode(params)}"


def parse_gdelt(payload: dict, *, query: str) -> list[DiscoveryHit]:
    hits: list[DiscoveryHit] = []
    for article in payload.get("articles", []) or []:
        url = article.get("url")
        if not url:
            continue
        seen = article.get("seendate")
        published = None
        if seen:
            try:
                published = date_parser.parse(seen)
                if published.tzinfo is None:
                    published = published.replace(tzinfo=dt.UTC)
            except (ValueError, OverflowError, TypeError):
                published = None
        hits.append(
            DiscoveryHit(
                title=normalise_text(article.get("title") or ""),
                url=url,
                canonical_url=canonicalise_url(url),
                published_at=published,
                provider="gdelt",
                query=query,
                domain=article.get("domain"),
            )
        )
    return hits
