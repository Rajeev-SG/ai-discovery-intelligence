"""Measure the acquisition → extraction → validated-claim loss funnel (issue #48).

Reads the *real* persisted ledger and the private snapshot store and reports, per
source and in aggregate, where evidence is lost between:

  1. configured sources           (config/sources.yaml)
  2. sources that produced a capture (evidence_item rows in the ledger)
  3. captures with stored extracted text (snapshot store text/<hash>.txt)
  4. captures re-extractable by the semantic lane (schema-valid model output)
  5. *validated* claims persisted  (quote-verified, integrity-gated)

Stage 4 is measured by re-running the production semantic lane read-only against
stored text; it costs one model call per capture and is therefore opt-in
(``--semantic``). Without it the script reports stages 1-3 and 5 from persisted
state, which is free and safe to run anywhere.

This is a measurement tool, not a gate: it never writes to the ledger. Output is
JSON on stdout so a proof artifact can be attached to the issue.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from sqlalchemy import create_engine, text

from ai_discovery.snapshot_store import read_extracted_text


def _engine():
    from ai_discovery.settings import get_settings

    return create_engine(get_settings().database_url)


def measure(*, semantic: bool = False, limit: int | None = None) -> dict:
    """Measure the funnel. ``limit`` caps captures measured per source (semantic
    re-extraction is the only expensive step), bounding cost on a large corpus."""
    from ai_discovery.registry import load_sources_config

    config = load_sources_config()
    configured = [s for s in config.sources]

    engine = _engine()
    per_source: list[dict] = []
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "select source_id, source_class, capture_hash, url, canonical_url, "
                "publisher, observed_at from evidence_item where is_candidate = false "
                "order by source_id"
            )
        ).all()
        claim_counts = dict(
            conn.execute(text("select source_id, count(*) from claim group by 1")).all()
        )
        claim_total = conn.execute(text("select count(*) from claim")).scalar() or 0

    by_source: dict[str, list] = {}
    for r in rows:
        by_source.setdefault(r[0], []).append(r)

    configured_ids = {s.id for s in configured}
    total_text_present = 0
    total_re_extractable = 0
    for source_id in sorted(configured_ids | set(by_source)):
        items = by_source.get(source_id, [])
        text_present = 0
        re_extractable: int | None = None
        measured_items = items[:limit] if limit else items
        for item in measured_items:
            stored = read_extracted_text(item[2])
            if stored:
                text_present += 1
        total_text_present += text_present
        if semantic and items:
            import logging

            # Reduce third-party chatter for the duration of this source without
            # silencing the extraction pipeline's own diagnostics: raise only the
            # noisy HTTP/client loggers and restore them afterwards.
            _noisy = ("httpx", "httpx2", "httpcore", "urllib3", "openai", "instructor")
            _prev_levels = {name: logging.getLogger(name).level for name in _noisy}
            for name in _noisy:
                logging.getLogger(name).setLevel(logging.ERROR)
            from ai_discovery.claim_extract import claims_from_extraction
            from ai_discovery.claims import Capture
            from ai_discovery.semantic import semantic_extract

            ok = 0
            re_extraction_failures: list[dict] = []
            for item in measured_items:
                stored = read_extracted_text(item[2])
                if not stored:
                    continue
                try:
                    result = semantic_extract(
                        source_id=source_id,
                        source_url=item[4] or item[3],
                        cleaned_markdown=stored,
                    )
                    src = {
                        "source_id": source_id,
                        "publisher": item[5] or "",
                        "url": item[3],
                        "canonical_url": item[4] or item[3],
                        "source_class": item[1],
                        "snapshot_path": None,
                        "http_status": None,
                        "robots_allowed": None,
                    }
                    cap = Capture(
                        raw=b"", text=stored, fetched_at=dt.datetime.now(dt.UTC)
                    )
                    claims_from_extraction(
                        result, source=src, capture=cap, verified_against_capture=True
                    )
                    ok += 1
                except Exception as error:  # noqa: BLE001 — a loss is a data point, not fatal
                    re_extraction_failures.append(
                        {"capture_hash": item[2][:12], "error": str(error)[:200]}
                    )
                    continue
            for _name, _lvl in _prev_levels.items():
                logging.getLogger(_name).setLevel(_lvl)
            re_extractable = ok
            total_re_extractable += ok
        per_source.append(
            {
                "source_id": source_id,
                "source_class": items[0][1] if items else next(
                    (s.source_class for s in configured if s.id == source_id), None
                ),
                "evidence_items": len(items),
                "extracted_text_present": text_present,
                "re_extractable_captures": re_extractable,
                "re_extraction_failures": (re_extraction_failures if semantic else None),
                "validated_claims": claim_counts.get(source_id, 0),
            }
        )

    sources_with_evidence = sum(1 for e in per_source if e["evidence_items"])
    sources_with_claims = sum(1 for e in per_source if e["validated_claims"])
    return {
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "funnel": {
            "configured_sources": len(configured),
            "sources_with_capture": sources_with_evidence,
            "captures_with_extracted_text": total_text_present,
            "captures_re_extractable": (total_re_extractable if semantic else None),
            "validated_claims": claim_total,
            "sources_with_validated_claim": sources_with_claims,
        },
        "per_source": per_source,
        "semantic_measured": semantic,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--semantic",
        action="store_true",
        help="re-run the semantic lane against stored text (costs model calls)",
    )
    parser.add_argument("--out", help="write JSON to this path instead of stdout")
    args = parser.parse_args()
    report = measure(semantic=args.semantic)
    payload = json.dumps(report, indent=2)
    if args.out:
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
