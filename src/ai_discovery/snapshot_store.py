"""Private, content-addressed raw snapshot store.

Raw HTML is never served by the API. Snapshots live on local disk under
settings.snapshot_dir, addressed by SHA-256 of the raw bytes, so #3 (claim
extraction) can re-read the exact captured text for a capture hash.
"""

from __future__ import annotations

from pathlib import Path

from .hashing import sha256_bytes
from .settings import get_settings


def snapshot_dir() -> Path:
    path = get_settings().snapshot_dir
    path.mkdir(parents=True, exist_ok=True)
    return path


def store_snapshot(raw: bytes, *, suffix: str = ".html") -> tuple[str, str]:
    """Write raw bytes and return (sha256, absolute path)."""
    digest = sha256_bytes(raw)
    target = snapshot_dir() / f"{digest[:2]}" / f"{digest}{suffix}"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_bytes(raw)
    return digest, str(target)


def read_snapshot(digest: str, *, suffix: str = ".html") -> bytes | None:
    target = snapshot_dir() / f"{digest[:2]}" / f"{digest}{suffix}"
    return target.read_bytes() if target.exists() else None


def store_extracted_text(capture_hash: str, text: str) -> str:
    """Persist extracted plain text privately, addressed by capture hash.

    Issue #3 (claim extraction) re-reads this exact text for a capture hash, so
    claims always trace back to the bytes that were hashed. Never served by the API.
    """
    target = snapshot_dir() / "text" / f"{capture_hash}.txt"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_text(text, encoding="utf-8")
    return str(target)


def read_extracted_text(capture_hash: str) -> str | None:
    target = snapshot_dir() / "text" / f"{capture_hash}.txt"
    return target.read_text(encoding="utf-8") if target.exists() else None
