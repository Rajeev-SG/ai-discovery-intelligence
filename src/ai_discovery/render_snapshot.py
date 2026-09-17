"""Hash-addressed rendered-capture store: raw HTML + cleaned Markdown + tables.

Raw source bodies and Crawl4AI-cleaned Markdown are both evidence and stay in
the private snapshot directory, never in Git. Both documents are hashed
separately: the raw hash preserves auditability of the exact capture, the
cleaned hash drives incremental re-extraction (only changed cleaned documents
reach the semantic stage).
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from .render import RenderResult
from .settings import get_settings
from .snapshot_store import snapshot_dir


def canonicalise_tables(tables: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Order-stable table representation for hashing.

    Table order and row order are render artifacts, not semantic signals;
    sorting keeps the skip hash stable across crawls of an identical page
    regardless of extraction ordering.
    """
    canonical = []
    for table in tables:
        canonical.append(
            {
                "caption": table.get("caption") or "",
                "headers": sorted(str(h) for h in (table.get("headers") or [])),
                "rows": sorted([str(cell) for cell in row] for row in (table.get("rows") or [])),
            }
        )
    return sorted(
        canonical, key=lambda t: (t["caption"], json.dumps(t["headers"], sort_keys=True))
    )


class RenderSnapshot:
    """One rendered source: raw evidence plus cleaned Markdown.

    ``content_sha256`` is the incremental-detection hash over the cleaned
    document AND canonicalised tables. ``raw_sha256`` covers the stored raw
    body. They are different concepts and must never be used interchangeably.
    """

    def __init__(
        self,
        *,
        source_id: str,
        url: str,
        raw: bytes,
        cleaned_markdown: bytes,
        captured_at: datetime,
        tables: list[dict[str, Any]] | None = None,
    ) -> None:
        self.source_id = source_id
        self.url = url
        self.raw = raw
        self.cleaned_markdown = cleaned_markdown
        self.captured_at = captured_at
        self.tables = tables or []
        self.raw_sha256 = hashlib.sha256(raw).hexdigest()
        tables_bytes = (
            json.dumps(
                canonicalise_tables(self.tables), sort_keys=True, ensure_ascii=False
            ).encode("utf-8")
            if self.tables
            else b""
        )
        self.content_sha256 = hashlib.sha256(
            cleaned_markdown + b"\n\x00structured-tables:\n" + tables_bytes
        ).hexdigest()

    @classmethod
    def from_render(cls, *, source_id: str, captured_at: datetime, render: RenderResult):
        return cls(
            source_id=source_id,
            url=render.url,
            raw=render.raw_html,
            cleaned_markdown=render.cleaned_markdown,
            captured_at=captured_at,
            tables=render.tables,
        )

    def store(self, directory: Path | None = None) -> tuple[Path, Path]:
        """Write raw evidence and the cleaned document; return both paths."""
        base = directory or snapshot_dir()
        base.mkdir(parents=True, exist_ok=True)
        safe_id = re.sub(r"[^a-z0-9._-]", "-", self.source_id)
        raw_path = base / f"{safe_id}-{self.raw_sha256}.html"
        raw_path.write_bytes(self.raw)
        cleaned_path = base / f"{safe_id}-{self.content_sha256}.md"
        cleaned_path.write_bytes(self.cleaned_markdown)
        if self.tables:
            tables_path = base / f"{safe_id}-{self.content_sha256}.tables.json"
            tables_path.write_text(json.dumps(self.tables, indent=1), encoding="utf-8")
        return raw_path, cleaned_path


def read_cleaned_markdown(source_id: str, content_sha256: str) -> bytes | None:
    base = snapshot_dir()
    safe_id = re.sub(r"[^a-z0-9._-]", "-", source_id)
    path = base / f"{safe_id}-{content_sha256}.md"
    return path.read_bytes() if path.exists() else None


def snapshot_settings():
    return get_settings()
