import datetime as dt

from ai_discovery.adapters.bing_news import bing_news_url, parse_bing_news, unwrap_bing_link
from ai_discovery.adapters.feed import parse_feed
from ai_discovery.adapters.gdelt import gdelt_url, parse_gdelt

RSS = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>Example</title>
<item><title>Hello AI</title><link>https://example.com/post?utm_source=rss</link>
<pubDate>Wed, 16 Sep 2026 10:00:00 +0000</pubDate><description>Body</description></item>
</channel></rss>"""

BING_RSS = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>Bing</title>
<item><title>An AEO study</title><link>http://www.bing.com/news/apiclick.aspx?ref=FexRss&amp;url=https%3a%2f%2fnews.example.com%2faeo&amp;c=1</link></item>
</channel></rss>"""


def test_parse_feed_canonicalises_and_dates():
    entries = parse_feed(RSS)
    assert len(entries) == 1
    entry = entries[0]
    assert entry.canonical_url == "https://example.com/post"
    assert entry.published_at == dt.datetime(2026, 9, 16, 10, 0, tzinfo=dt.UTC)


def test_parse_feed_respects_limit():
    assert len(parse_feed(RSS, limit=0)) == 0


def test_bing_link_unwraps_tracking_redirect():
    link = (
        "http://www.bing.com/news/apiclick.aspx?ref=FexRss"
        "&url=https%3a%2f%2fnews.example.com%2faeo&c=1"
    )
    assert unwrap_bing_link(link) == "https://news.example.com/aeo"


def test_parse_bing_news_stores_publisher_url_only():
    hits = parse_bing_news(BING_RSS, query="aeo")
    assert len(hits) == 1
    assert hits[0].domain == "news.example.com"
    assert hits[0].canonical_url == "https://news.example.com/aeo"
    assert "bing.com" not in hits[0].canonical_url


def test_bing_url_is_rss_format():
    assert "format=RSS" in bing_news_url("x")


def test_parse_gdelt_maps_articles():
    payload = {
        "articles": [
            {
                "url": "https://a.example/x?utm_medium=news",
                "title": "T",
                "seendate": "20260916T101500Z",
            }
        ]
    }
    hits = parse_gdelt(payload, query="q")
    assert hits[0].canonical_url == "https://a.example/x"
    assert hits[0].provider == "gdelt"


def test_gdelt_url_requests_json():
    url = gdelt_url('"AI search"')
    assert "format=json" in url and "mode=artlist" in url
