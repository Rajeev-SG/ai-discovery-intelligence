"""SearXNG metasearch adapter — discovery SIGNAL ONLY (never canonical)."""

from __future__ import annotations

from ..hashing import canonicalise_url, host_of, normalise_text
from .gdelt import DiscoveryHit


def parse_searxng(payload: dict, *, query: str) -> list[DiscoveryHit]:
    hits: list[DiscoveryHit] = []
    for result in payload.get("results", []) or []:
        url = result.get("url")
        if not url:
            continue
        hits.append(
            DiscoveryHit(
                title=normalise_text(result.get("title") or ""),
                url=url,
                canonical_url=canonicalise_url(url),
                published_at=None,
                provider="searxng",
                query=query,
                domain=host_of(url),
            )
        )
    return hits
