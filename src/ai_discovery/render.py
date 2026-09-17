"""Crawl4AI rendering + clean/fit Markdown (adopted renderer, OSS_STACK update).

Crawl4AI owns browser rendering, readiness, lazy-load handling, main-content
identification and HTML -> Markdown conversion. This module only maps the
source registry's configuration onto Crawl4AI configuration and returns both
the raw rendered HTML and the cleaned Markdown document. Source-specific
behaviour belongs in Crawl4AI configuration (selectors, waits, waits), not in
custom parsing code.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Self

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

from .normalise import normalise_markdown


@dataclass
class RenderResult:
    """One rendered capture: raw evidence plus the cleaned document."""

    raw_html: bytes
    cleaned_markdown: bytes
    tables: list[dict[str, Any]]
    url: str
    http_status: int | None = None


class RenderError(RuntimeError):
    """Raised when Crawl4AI cannot render a URL (surfaced, never retried in code)."""


def crawl_config_for(
    *,
    css_selector: str | None = None,
    excluded_selector: str | None = None,
    wait_for: str | None = None,
    wait_timeout_ms: int | None = None,
    settle_ms: int | None = None,
    content_filter_threshold: float | None = None,
) -> CrawlerRunConfig:
    """Build a Crawl4AI config from source-registry settings."""
    threshold = content_filter_threshold if content_filter_threshold is not None else 0.45
    generator = DefaultMarkdownGenerator(
        content_filter=PruningContentFilter(threshold=threshold),
    )
    kwargs: dict[str, Any] = {
        "cache_mode": CacheMode.BYPASS,
        "markdown_generator": generator,
        "verbose": False,
    }
    if css_selector:
        kwargs["css_selector"] = css_selector
    if excluded_selector:
        kwargs["excluded_selector"] = excluded_selector
    if wait_for:
        kwargs["wait_for"] = wait_for
    if wait_timeout_ms is not None:
        kwargs["wait_for_timeout"] = wait_timeout_ms
    if settle_ms is not None:
        kwargs["delay_before_return_html"] = settle_ms / 1000
    return CrawlerRunConfig(**kwargs)


class RenderClient:
    """Run-scoped Crawl4AI context: one browser across every source of a run.

    Crawl4AI's ``AsyncWebCrawler`` exposes only an async lifecycle; this
    context owns one dedicated event loop and drives it synchronously, so
    Dagster assets can use it as a plain ``with`` block.
    """

    def __init__(self, *, headless: bool = True) -> None:
        self._loop = asyncio.new_event_loop()
        self._crawler = AsyncWebCrawler(config=BrowserConfig(headless=headless, verbose=False))

    def __enter__(self) -> Self:
        try:
            self._loop.run_until_complete(self._crawler.start())
        except RuntimeError as error:
            self._loop.close()
            raise RenderError(
                "Crawl4AI rendering failed. Ensure the Crawl4AI browser runtime "
                "is installed: uv run crawl4ai-setup"
            ) from error
        return self

    def __exit__(self, *exc: object) -> None:
        try:
            self._loop.run_until_complete(self._crawler.close())
        finally:
            self._loop.close()

    def fetch(
        self,
        url: str,
        *,
        css_selector: str | None = None,
        excluded_selector: str | None = None,
        wait_for: str | None = None,
        wait_timeout_ms: int | None = None,
        settle_ms: int | None = None,
        content_filter_threshold: float | None = None,
    ) -> RenderResult:
        """Render one URL. Raw HTML is stored unmodified; cleaned doc is normalised."""
        config = crawl_config_for(
            css_selector=css_selector,
            excluded_selector=excluded_selector,
            wait_for=wait_for,
            wait_timeout_ms=wait_timeout_ms,
            settle_ms=settle_ms,
            content_filter_threshold=content_filter_threshold,
        )
        result = self._loop.run_until_complete(self._crawler.arun(url=url, config=config))
        if not result.success:
            raise RenderError(f"Crawl4AI render failed for {url}: {result.error_message}")
        markdown = result.markdown
        cleaned = markdown.fit_markdown or markdown.raw_markdown or str(markdown)
        tables = list(result.tables or [])
        status = getattr(result, "status_code", None) or getattr(result, "status", None)
        return RenderResult(
            raw_html=result.html.encode("utf-8"),
            cleaned_markdown=normalise_markdown(cleaned).encode("utf-8"),
            tables=tables,
            url=result.url or url,
            http_status=int(status) if status else None,
        )
