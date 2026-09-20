"""Typed access to config/sources.yaml (the source registry config)."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import get_args

import yaml
from pydantic import BaseModel, Field

from .settings import get_settings


class FetchPlan(BaseModel):
    """Concrete acquisition plan for one source (verified in config)."""

    model_config = {"arbitrary_types_allowed": True}

    mode: str  # rss|api|http|sitemap|rsshub|browser
    url: str | None = None
    limit: int | None = None
    rate_limit_per_minute: int | None = None
    notes: str | None = None
    verified_at: dt.date | None = None


class SourceConfig(BaseModel):
    id: str
    publisher: str
    source_class: str = Field(alias="class")
    url: str
    topics: list[str] = Field(default_factory=list)
    preferred_fetch: str = "http"
    region: str | None = None
    language: str | None = None
    enabled: bool = True
    fetch: FetchPlan | None = None

    model_config = {"populate_by_name": True}


class DiscoveryQuery(BaseModel):
    id: str
    provider: str  # gdelt|bing_news|searxng|openalex
    query: str
    class_hint: str | None = None
    topics: list[str] = Field(default_factory=list)
    enabled: bool = True


class SourcesConfig(BaseModel):
    version: int = 1
    last_reviewed: dt.date | None = None
    sources: list[SourceConfig]
    discovery_queries: list[DiscoveryQuery] = Field(default_factory=list)

    def by_id(self, source_id: str) -> SourceConfig | None:
        return next((s for s in self.sources if s.id == source_id), None)

    def enabled_sources(self) -> list[SourceConfig]:
        return [s for s in self.sources if s.enabled]

    def registered_hosts(self) -> set[str]:
        from .hashing import host_of

        return {host_of(s.url) for s in self.sources}


def load_sources_config(path: Path | None = None) -> SourcesConfig:
    config_path = path or get_settings().sources_config
    with Path(config_path).open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    config = SourcesConfig.model_validate(raw)
    # Fail at load time when the registry uses a source class the ledger cannot
    # represent: otherwise every otherwise-verified claim from that source is
    # silently rejected at record construction (issue #48's second root cause).
    # This is the drift guard the failure needs, in the loader, not a copy in a test.
    from .claim_models import SourceClass

    valid = set(get_args(SourceClass))
    unknown = sorted({s.source_class for s in config.sources} - valid)
    if unknown:
        raise ValueError(
            f"config/{config_path.name} uses source classes absent from the ledger "
            f"SourceClass literal: {unknown}. Add them to SourceClass (and "
            f"SOURCE_AUTHORITY) or correct the config."
        )
    return config


def resolve_fetch_mode(source: SourceConfig) -> tuple[str, str]:
    """Return (fetch_mode, fetch_url) preferring feed/API over browser rendering."""
    if source.fetch and source.fetch.mode:
        return source.fetch.mode, (source.fetch.url or source.url)
    preferred = source.preferred_fetch
    if preferred.startswith("api"):
        return "api", source.url
    if "rss" in preferred:
        return "rss", source.url
    if "sitemap" in preferred:
        return "sitemap", source.url
    if "rsshub" in preferred:
        return "rsshub", source.url
    return "http", source.url


# --------------------------------------------------------------------------- #
# Canonical surface registry (config/surfaces.yaml)
# --------------------------------------------------------------------------- #


class SurfaceConfig(BaseModel):
    """One consumer AI discovery surface from the canonical registry."""

    model_config = {"coerce_numbers_to_str": True}

    id: str
    vendor: str
    name: str
    family: str
    type: str
    tier: str
    regions: list[str] = Field(default_factory=list)
    distribution: list[str] = Field(default_factory=list)
    discovery_modes: list[str] = Field(default_factory=list)
    retrieval_status: str
    official_urls: list[str] = Field(default_factory=list)


class SurfacesConfig(BaseModel):
    version: int = 1
    last_reviewed: dt.date | None = None
    surfaces: list[SurfaceConfig]

    def ids(self) -> list[str]:
        return [s.id for s in self.surfaces]

    def by_id(self, surface_id: str) -> SurfaceConfig | None:
        return next((s for s in self.surfaces if s.id == surface_id), None)

    def core_ids(self) -> list[str]:
        """Core surfaces (the marketer-facing landscape), in registry order."""

        return [s.id for s in self.surfaces if s.tier.startswith("core")]


def load_surfaces_config(path: Path | None = None) -> SurfacesConfig:
    config_path = path or (get_settings().sources_config.parent / "surfaces.yaml")
    with Path(config_path).open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return SurfacesConfig.model_validate(raw)


#: Claim ``surfaces`` values that are genuine aliases for a canonical registry id.
#: Extraction emits a surface name as the source page wrote it (e.g. "deepseek",
#: "naver-ai-tab"); the registry carries the canonical id. Resolution happens at
#: READ time only — stored claims are append-only and are never rewritten — so a
#: real claim attaches to its surface without mutating the ledger. Values that are
#: NOT surfaces (a category like "answer-engines", or a cited domain like
#: "reddit") are deliberately absent: they stay unmapped and are reported, not
#: silently coerced onto a surface.
SURFACE_ALIASES: dict[str, str] = {
    "deepseek": "deepseek-chat",
    "naver-ai-tab": "naver-ai",
    "kanana-in-kakaotalk": "kakao-kanana",
    "qwen": "qwen-consumer",
    "yuanbao": "tencent-yuanbao",
    "wenxin": "baidu-wenxin-assistant",
    "kimi-chat": "kimi",
}


def resolve_surface_id(value: str) -> str:
    """Map a claim's surface value to a canonical registry id (identity if unknown)."""

    return SURFACE_ALIASES.get(value, value)
