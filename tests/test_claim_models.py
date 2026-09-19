"""Domain invariants: unknown, locators, distinct dates, LLM-is-not-evidence."""

from __future__ import annotations

import datetime as dt

import pytest
from pydantic import ValidationError

from ai_discovery.claim_models import (
    CaptureEvidence,
    DateProfile,
    ExtractionProvenance,
    Locator,
    Provenanced,
    StudyMethodology,
    claim_id_for,
)


def test_unknown_has_no_value_and_no_locator():
    field = Provenanced[int]()
    assert field.known is False
    assert field.value is None and field.locator is None


def test_known_value_requires_a_locator():
    with pytest.raises(ValidationError):
        Provenanced[int](value=42)


def test_unknown_must_not_carry_a_locator():
    with pytest.raises(ValidationError):
        Provenanced[int](locator=Locator(kind="verbatim_quote", quote="x"))


def test_locator_requires_a_pointer():
    # Every constructed locator is re-verifiable: a quote or a selector (issue #24).
    assert Locator(kind="verbatim_quote", quote="q").checkable
    assert Locator(kind="page_stamp", selector="2026.06.26").checkable
    with pytest.raises(ValidationError):
        Locator(kind="verbatim_quote")


def test_locator_quote_matching_normalises_typography_and_whitespace():
    loc = Locator(kind="verbatim_quote", quote="can\u2019t rule out  a problem")
    assert loc.present_in("Promptwatch says it can't rule out a problem in its data.")


def test_selector_locator_must_resolve_not_assume_true():
    """Issue #24: a selector is re-verified, never assumed true."""

    loc = Locator(kind="jsonld_field", selector="datePublished")
    # Present in the raw markup (JSON-LD), absent from the parsed text.
    assert loc.present_in("nothing here", '<script>{"datePublished":"2026-05-14"}</script>')
    # A selector that names nothing in either haystack must fail.
    assert not loc.present_in("nothing here", "<html><body>hi</body></html>")
    assert not Locator(kind="section", selector="div#never-exists").present_in("hi", "<div>hi</div>")


def test_selector_value_is_bound_to_its_key():
    """A short value alone must not match an unrelated substring (issue #24)."""

    loc = Locator(kind="jsonld_field", selector="datePublished=2026-05-14")
    assert loc.present_in("", '"datePublished":"2026-05-14T01:54:23+00:00"')
    # The value appears, but under a different key: not the same anchor.
    assert not loc.present_in("", '"dateModified":"2026-05-14T01:54:23+00:00"')


def test_name_only_selector_must_not_validate_an_arbitrary_value():
    """F1: a name-only selector resolves a location, not a licence for any number.

    ``value.verifies`` requires the claimed value to appear in the content the
    selector resolves to, so a fabricated number on ``datePublished`` fails.
    """

    raw = '<script>{"datePublished":"2026-05-14T01:54:23+00:00"}</script>'
    loc = Locator(kind="jsonld_field", selector="datePublished")
    assert loc.present_in("", raw)  # the key exists...
    import datetime as _dt

    assert loc.verifies(_dt.date(2026, 5, 14), "", raw)  # ...and the value is consistent
    assert not loc.verifies("9.9M", "", raw)  # a fabricated value is not


def test_value_must_bind_to_its_own_key_not_the_whole_page():
    """F2: key and value must co-occur, not be two independent substring hits."""

    raw = '{"datePublished":"2026-05-14"} <p>in 2026 the market grew</p> <span>dateModified</span>'
    stray = Locator(kind="jsonld_field", selector="dateModified=2026")
    # 'dateModified' and '2026' both appear, but never as a pair.
    assert not stray.present_in("", raw)


def test_css_section_and_table_row_selectors_resolve():
    """F3: section/table_row use real CSS, not verbatim literals."""

    html = '<section id="results">Result body</section>'
    section = Locator(kind="section", selector="section#results")
    assert section.present_in("", html)
    assert not Locator(kind="section", selector="section#missing").present_in("", html)
    table = '<table><tr><td>1.2M</td></tr></table>'
    assert Locator(kind="table_row", selector="table tr").present_in("", table)


def test_selector_present_in_fails_closed_without_raw_text():
    """F4: a selector with only parsed text must not read as success."""

    loc = Locator(kind="jsonld_field", selector="datePublished")
    assert loc.present_in("datePublished") is False
    assert loc.verifies("2026-05-14", "datePublished") is False


def test_selector_with_multiple_anchors_requires_all():
    loc = Locator(kind="jsonld_field", selector="datePublished=A / dateModified=B")
    assert loc.present_in("", '"datePublished":"A","dateModified":"B"')
    assert not loc.present_in("", '"datePublished":"A"')


def test_dates_are_four_distinct_fields():
    profile = DateProfile(
        published_at=Provenanced[dt.date](
            value=dt.date(2026, 5, 14),
            locator=Locator(kind="jsonld_field", selector="datePublished"),
        ),
        modified_at=Provenanced[dt.date](
            value=dt.date(2026, 6, 11),
            locator=Locator(kind="jsonld_field", selector="dateModified"),
        ),
        measured_window=Provenanced[str](
            value="~Apr 2026", locator=Locator(kind="verbatim_quote", quote="one month ago")
        ),
        observed_at=dt.datetime(2026, 9, 16, tzinfo=dt.UTC),
    )
    assert profile.published_at.value != profile.modified_at.value
    assert profile.measured_window.value != profile.published_at.value


def test_modified_before_published_is_rejected():
    with pytest.raises(ValidationError):
        DateProfile(
            published_at=Provenanced[dt.date](
                value=dt.date(2026, 6, 1), locator=Locator(kind="page_stamp", selector="stamp")
            ),
            modified_at=Provenanced[dt.date](
                value=dt.date(2026, 5, 1), locator=Locator(kind="page_stamp", selector="stamp")
            ),
        )


def test_naive_observed_at_is_rejected():
    naive = dt.datetime(2026, 9, 16, 12, 0, 0)  # noqa: DTZ001 - the point of the test
    with pytest.raises(ValidationError):
        DateProfile(observed_at=naive)


def test_llm_proposal_is_not_evidence_without_human_review():
    with pytest.raises(ValidationError):
        ExtractionProvenance(method="llm_proposal", tool="instructor", version="0.1")
    ok = ExtractionProvenance(
        method="llm_proposal", tool="instructor", version="0.1", human_reviewed=True
    )
    assert ok.human_reviewed


def test_known_geography_needs_a_basis():
    with pytest.raises(ValidationError):
        StudyMethodology(
            surfaces=["chatgpt"],
            measurement_mode="vendor_estimate",
            geography=Provenanced[str](
                value="US", locator=Locator(kind="verbatim_quote", quote="United States")
            ),
        )


def test_claim_id_is_deterministic_and_content_addressed():
    a = claim_id_for("src", "audience_usage", "ChatGPT share is 52.7%")
    b = claim_id_for("src", "audience_usage", "ChatGPT   share is 52.7%")
    c = claim_id_for("src", "audience_usage", "ChatGPT share is 61.2%")
    assert a == b and a != c and len(a) == 32


def test_evidence_hash_must_be_sha256_hex():
    with pytest.raises(ValidationError):
        CaptureEvidence(
            source_id="s",
            publisher="p",
            url="u",
            canonical_url="u",
            source_class="vendor_research",
            capture_hash="not-a-hash",
        )
