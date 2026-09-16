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
    assert Locator(kind="verbatim_quote", quote="q").checkable
    assert not Locator(kind="page_stamp", selector="2026.06.26").checkable
    with pytest.raises(ValidationError):
        Locator(kind="verbatim_quote")


def test_locator_quote_matching_normalises_typography_and_whitespace():
    loc = Locator(kind="verbatim_quote", quote="can\u2019t rule out  a problem")
    assert loc.present_in("Promptwatch says it can't rule out a problem in its data.")


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
