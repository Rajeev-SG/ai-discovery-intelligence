from ai_discovery.hashing import (
    candidate_id,
    canonicalise_url,
    host_of,
    normalise_text,
    sha256_text,
)


def test_canonicalise_strips_tracking_and_fragment():
    url = "https://Example.com/Post/?utm_source=x&utm_medium=y&b=2&a=1#section"
    assert canonicalise_url(url) == "https://example.com/Post?a=1&b=2"


def test_canonicalise_normalises_trailing_slash_and_host_case():
    # http and https are different origins and must NOT be merged, but a trailing
    # slash and host case are presentation differences and must collapse.
    assert canonicalise_url("https://X.com/a/") == canonicalise_url("https://x.com/a")
    assert canonicalise_url("http://x.com/a") != canonicalise_url("https://x.com/a")


def test_dedup_primitive_groups_tracking_variants():
    a = candidate_id(canonicalise_url("https://a.com/p?utm_campaign=1"))
    b = candidate_id(canonicalise_url("https://a.com/p"))
    assert a == b


def test_host_of_strips_www():
    assert host_of("https://www.ahrefs.com/blog/feed/") == "ahrefs.com"


def test_normalise_text_collapses_whitespace():
    assert normalise_text("a \n\t b   c") == "a b c"


def test_capture_hash_ignores_layout_churn():
    assert sha256_text(normalise_text("x  y")) == sha256_text(normalise_text("x\ny"))
