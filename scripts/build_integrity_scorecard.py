"""Offline evidence-integrity and editorial scorecard (issue #29).

Runs the *real* modules against a checked-in fixture set and writes a
machine-readable scorecard to ``proof/integrity/scorecard.json``. Nothing here is
hand-scored: each check calls the production code path and records what it did.

Checks (each is a negative control — a naive or regressed implementation fails it):

1. fabricated / unsupported claims admitted (must be 0)
2. unknown values rendered as known (must be 0)
3. contradictions preserved and not falsely resolved
4. corrections retained through dedupe
5. old-study vs new-event classification (event-time window)
6. brief inclusion/exclusion against a frozen expected set

Each result is classed ``verified`` (the real module made the call) or
``warning`` (a hypothesis-level note), so a defect is distinguishable from a
suspicion. Removing the fabrication guard or the correction-dedupe rule makes the
scorecard fail (exit non-zero).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
# Overridable so tests can point at an isolated copy of the package instead of
# mutating the real tree, and write the artifact elsewhere.
SRC_ROOT = Path(os.environ.get("INTEGRITY_SRC_ROOT", REPO / "src"))
sys.path.insert(0, str(SRC_ROOT))
# The scorer resolves config/significance.yaml relative to the imported package, so
# when the package is an isolated copy point it at the real repo's config.

from ai_discovery import claims as C
from ai_discovery import confidence as CONF
from ai_discovery.brief import (
    BriefGenerator,
    BriefItem,
    ConfidenceLabel,
    build_weekly_brief,
)
from ai_discovery.change_events import ChangeEvent, EventStore, EventType

UTC = dt.UTC
OUT = Path(
    os.environ.get("INTEGRITY_SCORECARD_OUT", REPO / "proof" / "integrity" / "scorecard.json")
)
FIXTURES = REPO / "proof" / "integrity" / "fixtures"


def _platform_capture() -> C.Capture:
    raw = (
        b'<html><head><script type="application/ld+json">'
        b'{"datePublished":"2026-01-02T00:00:00+00:00"}</script></head><body>'
        b"<p>Widget Search had 1.2M monthly visits in January 2026.</p>"
        b"</body></html>"
    )
    return C.Capture(raw=raw, text=C.extract_capture_text(raw.decode()))


def _spec(**overrides) -> dict:
    spec = {
        "source": {
            "source_id": "widget",
            "publisher": "Widget Inc",
            "url": "https://example.test/a",
            "canonical_url": "https://example.test/a",
            "source_class": "vendor_research",
        },
        "topic": "audience_usage",
        "statement": "Widget Search had 1.2M monthly visits in January 2026.",
        "surfaces": ["widget-search"],
        "methodology": {"measurement_mode": "vendor_estimate"},
        "metrics": [
            {
                "metric_id": "visits",
                "label": "Monthly visits",
                "definition": {"value": "monthly visits", "quote": "1.2M monthly visits"},
                "value": {"value": "1.2M", "quote": "1.2M monthly visits in January 2026"},
                "unit": {"value": "visits", "quote": "monthly visits"},
                "window": {"value": "Jan 2026", "quote": "in January 2026"},
                "scope": {"value": "Widget Search", "quote": "Widget Search"},
            }
        ],
        "dates": {
            "published_at": "2026-01-02",
            "published_at_selector": "datePublished",
            "modified_at": None,
            "measured_window": {"value": "Jan 2026", "quote": "January 2026"},
            "observed_at": "2026-09-16T00:00:00+00:00",
        },
        "capture_anchors": [{"kind": "verbatim_quote", "quote": "1.2M monthly visits"}],
    }
    spec.update(overrides)
    return spec


# --- checks ----------------------------------------------------------------- #


def check_fabricated_claims_rejected() -> dict:
    """A plausible-but-unsupported figure must be rejected (negative control 1)."""

    spec = _spec()
    spec["metrics"][0]["value"] = {
        "value": "9.9M",
        "quote": "9.9M monthly visits in January 2026",
    }
    try:
        C.extract_claim(spec=spec, capture=_platform_capture())
    except C.ClaimSpecError:
        return {"name": "fabricated_claim_rejected", "status": "verified", "admitted": 0}
    return {"name": "fabricated_claim_rejected", "status": "verified", "admitted": 1}


def check_fabricated_selector_rejected() -> dict:
    """A fabricated selector must be rejected, not assumed true (issue #24)."""

    spec = _spec()
    spec["capture_anchors"] = [{"kind": "jsonld_field", "selector": "div#never-exists"}]
    try:
        C.extract_claim(spec=spec, capture=_platform_capture())
    except C.ClaimSpecError:
        return {"name": "fabricated_selector_rejected", "status": "verified", "admitted": 0}
    return {"name": "fabricated_selector_rejected", "status": "verified", "admitted": 1}


def check_unknown_round_trips_as_unknown() -> dict:
    """An unknown value must persist and return as unknown, never the string 'None'."""

    import json as _json

    spec = _spec()
    spec["metrics"][0]["value"] = None
    record = C.extract_claim(spec=spec, capture=_platform_capture())
    engine = C.create_ledger_engine("sqlite+pysqlite:///:memory:")
    C.init_ledger(engine)
    C.persist_claim(engine, record)
    row = C.load_expanded_claims(engine)[0]
    metric = row["metrics"][0]
    rendered_known = metric["value_text"] == "None" or metric["value_number"] == "None"
    leaked = "None" in _json.dumps(row["metrics"])
    return {
        "name": "unknown_round_trips_as_unknown",
        "status": "verified",
        "value_text": metric["value_text"],
        "rendered_as_known": int(rendered_known or leaked),
    }


def check_correction_retained() -> dict:
    """A corrected figure must not be silently dropped (negative control 2)."""

    store = EventStore()
    store.append(
        ChangeEvent(
            event_type=EventType.citation_source_shift,
            title="original",
            description=".",
            surfaces=["chatgpt"],
            observed_at=dt.datetime(2026, 9, 1, tzinfo=UTC),
            published_at=dt.datetime(2026, 9, 1, tzinfo=UTC),
            dedupe_key="k",
        )
    )
    store.append(
        ChangeEvent(
            event_type=EventType.correction_retraction,
            title="correction",
            description=".",
            surfaces=["chatgpt"],
            observed_at=dt.datetime(2026, 9, 5, tzinfo=UTC),
            published_at=dt.datetime(2026, 9, 5, tzinfo=UTC),
            dedupe_key="k",
            supersedes=None,
        )
    )
    ids = {e.title for e in store.timeline()}
    return {
        "name": "correction_retained",
        "status": "verified",
        "correction_dropped": 0 if "correction" in ids else 1,
        "timeline": [e.title for e in store.timeline()],
    }


def check_contradictions_preserved() -> dict:
    """A contradiction must be preserved, and a genuine conflict not resolved away."""

    from ai_discovery.reconciliation import StudyClaim, compare_claims

    first = StudyClaim(
        id="a",
        evidence_ids=("e1",),
        surface="chatgpt",
        subject="reddit.com",
        statement="share fell",
        metric="citation_share",
        denominator="all",
        geography="global",
        value=0.5,
        unit="percent",
    )
    second = StudyClaim(
        id="b",
        evidence_ids=("e2",),
        surface="chatgpt",
        subject="reddit.com",
        statement="share rose",
        metric="citation_share",
        denominator="visit share",
        geography="US",
        value=16.8,
        unit="percent",
    )
    r = compare_claims(first, second)
    preserved = set(r.claim_ids) == {"a", "b"}
    falsely_resolved = r.state not in ("methodologically_incomparable", "contested")
    return {
        "name": "contradictions_preserved",
        "status": "verified",
        "both_claims_preserved": int(preserved),
        "falsely_resolved": int(falsely_resolved),
        "state": r.state,
    }


def check_old_study_is_not_a_new_change() -> dict:
    """An old study ingested now must not classify as this week's change."""

    ref = dt.datetime(2026, 9, 17, tzinfo=UTC)
    old = BriefItem(
        change="old",
        why_it_matters=".",
        agency_action="m",
        confidence=ConfidenceLabel.MEDIUM,
        significance=5.0,
        published_at=dt.datetime(2024, 1, 1, tzinfo=UTC),
    )
    new = BriefItem(
        change="new",
        why_it_matters=".",
        agency_action="m",
        confidence=ConfidenceLabel.MEDIUM,
        significance=4.0,
        published_at=dt.datetime(2026, 9, 15, tzinfo=UTC),
    )
    out = build_weekly_brief([old, new], reference=ref)
    changes = [i.change for i in out]
    return {
        "name": "old_study_not_a_new_change",
        "status": "verified",
        "old_study_misclassified": int("old" in changes),
        "included": changes,
    }


def check_brief_inclusion_against_frozen_set() -> dict:
    """Brief inclusion/exclusion must match a frozen expected set."""

    expected_path = FIXTURES / "brief_expected.json"
    expected = json.loads(expected_path.read_text())
    ref = dt.datetime.fromisoformat(expected["reference"])
    items = [
        BriefItem(
            change=c["change"],
            why_it_matters=".",
            agency_action="m",
            confidence=ConfidenceLabel(c.get("confidence", "medium")),
            significance=c["significance"],
            published_at=dt.datetime.fromisoformat(c["published_at"]) if c.get("published_at") else None,
            effective_from=dt.datetime.fromisoformat(c["effective_from"]) if c.get("effective_from") else None,
            is_watch_item=c.get("is_watch_item", False),
        )
        for c in expected["candidates"]
    ]
    bg = BriefGenerator(target_items=expected.get("target_items", 3), max_items=expected.get("max_items", 5))
    included = {i.change for i in build_weekly_brief(items, generator=bg, reference=ref)}
    wanted = set(expected["expected_included"])
    return {
        "name": "brief_inclusion_matches_expected",
        "status": "verified",
        "mismatch": len(included ^ wanted),
        "included": sorted(included),
        "expected": sorted(wanted),
    }


def check_confidence_is_not_model_asserted() -> dict:
    """A model saying 'high' must not make weak evidence high-confidence."""

    spec = _spec()
    spec["source"]["source_class"] = "other"
    spec["confidence"] = "high"
    spec["methodology"] = {"measurement_mode": "unknown"}
    record = C.extract_claim(spec=spec, capture=_platform_capture())
    assessment = CONF.assess_confidence(record, model_asserted="high")
    return {
        "name": "confidence_not_model_asserted",
        "status": "verified",
        "model_says": "high",
        "derived": assessment.label,
        "elevated_by_model": int(assessment.label == "high"),
    }


#: Human-readable note per check — the *criterion* a failure would violate.
CRITERIA = {
    "fabricated_claim_rejected": "admitted must be 0",
    "fabricated_selector_rejected": "admitted must be 0",
    "unknown_round_trips_as_unknown": "rendered_as_known must be 0",
    "correction_retained": "correction_dropped must be 0",
    "contradictions_preserved": "both_claims_preserved must be 1 and falsely_resolved 0",
    "old_study_not_a_new_change": "old_study_misclassified must be 0",
    "brief_inclusion_matches_expected": "mismatch must be 0",
    "confidence_not_model_asserted": "elevated_by_model must be 0",
}


def _failed(result: dict) -> bool:
    """A check fails when its failure counters are non-zero."""

    for key, value in result.items():
        if key in ("name", "status") or not isinstance(value, int):
            continue
        if key in (
            "admitted",
            "rendered_as_known",
            "correction_dropped",
            "falsely_resolved",
            "old_study_misclassified",
            "mismatch",
            "elevated_by_model",
        ) and value != 0:
            return True
        if key == "both_claims_preserved" and value != 1:
            return True
    return False


def main() -> int:
    checks = [
        check_fabricated_claims_rejected(),
        check_fabricated_selector_rejected(),
        check_unknown_round_trips_as_unknown(),
        check_correction_retained(),
        check_contradictions_preserved(),
        check_old_study_is_not_a_new_change(),
        check_brief_inclusion_against_frozen_set(),
        check_confidence_is_not_model_asserted(),
    ]
    for check in checks:
        check["criterion"] = CRITERIA.get(check["name"], "")
        check["result"] = "fail" if _failed(check) else "pass"
    failures = [c for c in checks if c["result"] == "fail"]
    verified = [c for c in checks if c["status"] == "verified"]
    warnings = [c for c in checks if c["status"] != "verified"]

    # Deterministic: no wall-clock timestamp, so regenerating an unchanged
    # scorecard produces zero diff (and any real content change is visible).
    body = {
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failures),
        "checks_failed": len(failures),
        "verified_count": len(verified),
        "warning_count": len(warnings),
        "negative_controls": [
            "plausible-but-unsupported figure (9.9M)",
            "correction sharing a syndication key",
        ],
        "checks": checks,
    }
    # A content hash instead of a timestamp: stable for identical results, and it
    # changes exactly when a check result does.
    body["content_hash"] = hashlib.sha256(
        json.dumps(body, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()[:16]
    scorecard = body
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(scorecard, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    try:
        shown = OUT.relative_to(REPO)
    except ValueError:  # artifact written outside the repo (isolated test copy)
        shown = OUT
    print(
        f"integrity scorecard: {scorecard['checks_passed']}/{len(checks)} passed "
        f"({len(failures)} failed) -> {shown}"
    )
    for c in checks:
        print(f"  [{'PASS' if c['result'] == 'pass' else 'FAIL'}] {c['name']}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
