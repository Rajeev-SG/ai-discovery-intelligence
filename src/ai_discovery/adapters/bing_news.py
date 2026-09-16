"""Bing News RSS discovery adapter.

Bing News RSS is robots-allowed. (Google News RSS is NOT used: news.google.com
robots.txt disallows /rss/search.) Entries link through
www.bing.com/news/apiclick.aspx?url=<real-url>; the publisher URL is decoded and
canonicalised so the tracking wrapper is never stored as a candidate.
"""

from __future__ import annotations

from urllib.parse import parse_qsl, quote_plus, urlsplit

from ..hashing import canonicalise_url, host_of, normalise_text
from .gdelt import DiscoveryHit

BING_NEWS_RSS = "https://www.bing.com/news/search"


def bing_news_url(query: str, *, mkt: str = "en-GB") -> str:
    return f"{BING_NEWS_RSS}?q={quote_plus(query)}&format=RSS&mkt={mkt}"


def unwrap_bing_link(link: str) -> str:
    """Return the publisher URL hidden behind Bing's apiclick redirect."""
    parts = urlsplit(link)
    if "bing.com" in parts.netloc and parts.path.endswith("apiclick.aspx"):
        for key, value in parse_qsl(parts.query):
            if key == "url" and value.startswith("http"):
                return value
    return link


def parse_bing_news(content: bytes, *, query: str) -> list[DiscoveryHit]:
    import feedparser

    parsed = feedparser.parse(content)
    hits: list[DiscoveryHit] = []
    for entry in parsed.entries:
        raw_link = entry.get("link")
        if not raw_link:
            continue
        url = unwrap_bing_link(raw_link)
        hits.append(
            DiscoveryHit(
                title=normalise_text(entry.get("title") or ""),
                url=url,
                canonical_url=canonicalise_url(url),
                published_at=None,
                provider="bing_news",
                query=query,
                domain=host_of(url),
            )
        )
    return hits
