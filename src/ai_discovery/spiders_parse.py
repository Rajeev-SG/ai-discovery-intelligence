"""Discovery-lane provider parsing (domain glue, no transport).

Moved from the deleted Scrapy spider; the logic is unchanged: each provider's
raw payload maps to typed DiscoveryHit rows. The transport is the direct
crawler (crawler.run_discovery_jobs); this module owns provider semantics.
"""

from __future__ import annotations

import json
from typing import Any

from .adapters.bing_news import parse_bing_news
from .adapters.gdelt import parse_gdelt
from .adapters.searxng import parse_searxng


def parse_provider(query: dict[str, Any], body: bytes):
    """Map a raw provider payload to DiscoveryHit rows (domain glue only)."""
    provider = query["provider"]
    if provider == "gdelt":
        return parse_gdelt(json.loads(body.decode("utf-8", "replace")), query=query["query"])
    if provider == "bing_news":
        return parse_bing_news(body, query=query["query"])
    if provider == "searxng":
        return parse_searxng(json.loads(body.decode("utf-8", "replace")), query=query["query"])
    msg = f"unknown discovery provider: {provider}"
    raise ValueError(msg)
