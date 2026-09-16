"""Content hashing + URL canonicalisation (dedup primitive)."""

from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_PREFIXES = ("utm_", "mc_", "pk_", "ref_", "sc_")
TRACKING_EXACT = {
    "fbclid",
    "gclid",
    "igshid",
    "mc_cid",
    "mc_eid",
    "ref",
    "source",
    "s_kwcid",
    "spm",
    "vero_id",
    "wickedid",
    "yclid",
    "_hsenc",
    "_hsmi",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()


def normalise_text(text: str) -> str:
    """Whitespace-normalised text, so a capture hash ignores layout churn."""
    return re.sub(r"\s+", " ", text or "").strip()


def canonicalise_url(url: str) -> str:
    """Strip tracking params, fragment and default ports; lowercase host."""
    parts = urlsplit(url.strip())
    scheme = (parts.scheme or "https").lower()
    netloc = parts.netloc.lower()
    if netloc.endswith(":80") and scheme == "http":
        netloc = netloc[:-3]
    if netloc.endswith(":443") and scheme == "https":
        netloc = netloc[:-4]
    path = parts.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    kept = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=False)
        if k.lower() not in TRACKING_EXACT and not k.lower().startswith(TRACKING_PREFIXES)
    ]
    query = urlencode(sorted(kept))
    return urlunsplit((scheme, netloc, path, query, ""))


def host_of(url: str) -> str:
    host = urlsplit(url).netloc.lower()
    return host.removeprefix("www.")


def candidate_id(canonical_url: str) -> str:
    return sha256_text(canonical_url)[:32]


def evidence_id(canonical_url: str, capture_hash: str) -> str:
    return sha256_text(f"{canonical_url}|{capture_hash}")[:40]
