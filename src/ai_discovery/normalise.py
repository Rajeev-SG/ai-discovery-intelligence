"""Deterministic stability normalisation for the cleaned document.

Vendor pages embed short-lived tracking tokens inside their links, so two
renders of an unchanged page can produce different Markdown. The cleaned
hash drives incremental re-extraction, so that volatility would make
"only a changed document re-extracts" false and re-bill the semantic stage
for pages whose content never moved.

This step removes only known volatile tracking parameters and drops
lazily-injected UI chrome lines. It never drops content; the raw document
is stored unmodified with its own hash, so provenance is unaffected.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit

# Parameters whose values are opaque, short-lived tracking tokens.
VOLATILE_QUERY_PARAMS = frozenset(
    {
        "h",  # Meta/Instagram signed-redirect hash
        "__rf__",
        "__rf__s",  # Meta rapid-feedback tokens
        "privacy_mutation_token",
        "__tn__",
        "_nc_cat",
        "_nc_oc",
        "_nc_sid",
        "__cft__",
        "__cf__",
        "fbclid",
        "gclid",
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_content",
        "utm_term",
    }
)

# Markdown link targets are wrapped in parentheses; bare URLs end at whitespace.
_URL_PATTERN = re.compile(r"https?://[^\s)\]>\"']+")
_TRAILING = ".,;:!?"


def _normalise_url(url: str) -> str:
    split = urlsplit(url)

    # Meta wraps outbound links in its own redirector; unwrap to the real
    # destination: stable, and a better evidence locator for a human.
    if split.netloc == "l.facebook.com" and split.path.endswith("/l.php"):
        target = dict(parse_qsl(split.query)).get("u")
        if target:
            return unquote(target)

    if not split.query:
        return url

    kept = [
        (key, value)
        for key, value in parse_qsl(split.query, keep_blank_values=True)
        if key not in VOLATILE_QUERY_PARAMS
    ]
    return urlunsplit((split.scheme, split.netloc, split.path, urlencode(kept), split.fragment))


# Standalone widget labels that vendors inject lazily; UI chrome, never content.
_VOLATILE_STANDALONE_LINES = frozenset(
    {"Feedback", "Was this information helpful?", "Log in", "Sign up"}
)


def normalise_markdown(text: str) -> str:
    """Return ``text`` with volatile render noise removed."""

    def replace(match: re.Match[str]) -> str:
        raw = match.group(0)
        trailing = ""
        while raw and raw[-1] in _TRAILING:
            trailing = raw[-1] + trailing
            raw = raw[:-1]
        return _normalise_url(raw) + trailing

    normalised = _URL_PATTERN.sub(replace, text)
    return "\n".join(
        line for line in normalised.split("\n") if line.strip() not in _VOLATILE_STANDALONE_LINES
    )
