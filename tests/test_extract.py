import datetime as dt

from ai_discovery.acquisition.extract import extract_document

ARTICLE = """
<html><head>
<title>AI search visibility report</title>
<meta property="article:published_time" content="2026-08-26T08:21:00Z"/>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"NewsArticle","headline":"AI search visibility report",
 "datePublished":"2026-08-26T08:21:00Z","dateModified":"2026-09-02T04:33:15+00:00",
 "author":{"@type":"Person","name":"Cecilia Meis"}}
</script></head>
<body><article><h1>AI search visibility report</h1>
<p>Reddit held a steady share of citations across the measured window.</p>
<p>Between the event dates that share fell substantially.</p>
<p>Second paragraph continues with enough content for extraction heuristics.</p>
</article></body></html>
"""


def test_extract_keeps_published_and_modified_distinct():
    doc = extract_document(ARTICLE, url="https://example.com/post")
    assert doc.published_at == dt.datetime(2026, 8, 26, 8, 21, tzinfo=dt.UTC)
    assert doc.modified_at == dt.datetime(2026, 9, 2, 4, 33, 15, tzinfo=dt.UTC)
    # a living page's modified date must never be promoted to publication date
    assert doc.published_at != doc.modified_at


def test_extract_returns_text_and_metadata():
    doc = extract_document(ARTICLE, url="https://example.com/post")
    assert "citations" in doc.text
    assert doc.extractor in {"trafilatura", "html_fallback"}
    assert doc.author == "Cecilia Meis"


def test_feed_date_used_only_when_page_has_no_date():
    doc = extract_document(
        "<html><body><article><p>" + "word " * 60 + "</p></article></body></html>",
        url="https://example.com/x",
        feed_published=dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
    )
    assert doc.published_at == dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
    assert doc.published_at_source == "feed"


def test_js_shell_still_returns_normalised_text_not_empty():
    # A JS-only shell has no readable article; we must still store something
    # honest rather than silently dropping the item.
    doc = extract_document("<html><body><div id='app'></div></body></html>", url="https://x/y")
    assert doc.text is not None
