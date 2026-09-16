"""Typed access to config/sources.yaml (the source registry config)."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

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
    return SourcesConfig.model_validate(raw)


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
