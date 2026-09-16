import pytest

from ai_discovery.registry import load_sources_config, resolve_fetch_mode


@pytest.fixture(scope="module")
def config():
    return load_sources_config()


def test_registry_parses_and_has_discovery_queries(config):
    assert len(config.sources) >= 40
    assert len(config.discovery_queries) >= 3


def test_every_discovery_query_has_supported_provider(config):
    allowed = {"gdelt", "bing_news", "searxng", "openalex"}
    for query in config.discovery_queries:
        assert query.provider in allowed, query.id


def test_verified_fetch_plans_present_for_seed_adapters(config):
    required = {
        "openai-platform-bots",  # official
        "ahrefs-blog-ai",  # visibility research (Ahrefs family)
        "semrush-blog-ai",  # visibility research (Semrush family)
        "sistrix-blog",  # visibility research (SISTRIX family)
        "questmobile-research",  # regional/China
    }
    ids = {s.id for s in config.sources if s.fetch is not None}
    assert required <= ids


def test_feed_preferred_over_browser(config):
    for source in config.sources:
        if source.fetch:
            assert source.fetch.mode in {"rss", "api", "http", "sitemap", "rsshub"}, source.id


def test_google_news_rss_not_configured(config):
    # robots.txt disallows /rss/search, so it must not appear as a provider.
    assert all(q.provider != "google_news" for q in config.discovery_queries)


def test_resolve_fetch_mode_prefers_feed(config):
    source = config.by_id("sistrix-blog")
    mode, url = resolve_fetch_mode(source)
    assert mode == "rss"
    assert url == "https://www.systrix.com/feed/".replace("systrix", "sistrix")
