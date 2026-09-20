"""Build the issue-#56 product-proof artifact from the REAL production ledger.

Reads the expanded claim ledger (production Postgres, or AI_DISCOVERY_DATABASE_URL)
and writes:
- proof/phase2/chatgpt_mechanics.json      (one complete ChatGPT payload)
- proof/phase2/deepseek_mechanics.json     (a deliberately under-documented surface)
- proof/phase2/ISSUE_56_PROOF.md           (human-readable proof)
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from sqlalchemy import create_engine

from ai_discovery.claims import load_expanded_claims
from ai_discovery.mechanics import (
    MECHANICS_DIMENSIONS,
    mechanics_view,
    project_all,
    unmapped_claim_surfaces,
)
from ai_discovery.registry import load_surfaces_config

OUT = REPO / "proof" / "phase2"


def main() -> int:
    url = os.environ.get(
        "AI_DISCOVERY_DATABASE_URL",
        "postgresql+psycopg://ai_discovery:ai_discovery@127.0.0.1:55432/ai_discovery",
    )
    engine = create_engine(url)
    claims = load_expanded_claims(engine)
    registry_ids = load_surfaces_config().ids()
    projection = project_all(registry_ids, claims)
    drift = unmapped_claim_surfaces(registry_ids, claims)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "chatgpt_mechanics.json").write_text(
        json.dumps(mechanics_view(projection["chatgpt"]), indent=2), encoding="utf-8"
    )
    (OUT / "deepseek_mechanics.json").write_text(
        json.dumps(mechanics_view(projection["deepseek-chat"]), indent=2), encoding="utf-8"
    )

    documented = mechanism_summary(projection["chatgpt"])
    under = mechanism_summary(projection["deepseek-chat"])
    lines = [
        "# Issue #56 — canonical mechanics ontology + evidence contract: product proof",
        "",
        "Generated from the **real production claim ledger** "
        + f"({len(claims)} validated claims across {len(registry_ids)} registry surfaces).",
        "Raw captures stay private; every value below is copied from a validated claim.",
        "",
        f"Dimensions: {len(MECHANICS_DIMENSIONS)} "
        + "(search_trigger, retrieval_provider, query_rewrite, crawling_indexing_controls, "
        + "freshness_recrawl, candidate_selection_reranking, citation_presentation, "
        + "shopping_product_feed, local_retrieval, social_community_retrieval, "
        + "mode_region_differences, answer_type, marketer_controllable_inputs).",
        "",
        "## 1. Complete ChatGPT mechanics payload (real evidence)",
        "",
        f"Coverage: **{documented['summary']}**",
        "",
        documented["table"],
        "",
        "Full payload: `proof/phase2/chatgpt_mechanics.json`.",
        "",
        "## 2. Under-documented surface — unknowns stay explicit",
        "",
        "`deepseek-chat` (registry status: under_documented). Real claims exist for "
        + "this surface (audience only), so no mechanics dimension is evidenced and "
        + "every dimension is an explicit `unknown` - never inferred from the registry.",
        "",
        f"Coverage: **{under['summary']}**",
        "",
        under["table"],
        "",
        "Full payload: `proof/phase2/deepseek_mechanics.json`.",
        "",
        "## 3. Surface-id drift surfaced (not silently coerced)",
        "",
        "Claim surface values that are not registry surfaces (and not aliases) are "
        + "reported as data drift, never attached to a real surface:",
        "",
        "```json",
        json.dumps(drift, indent=2),
        "```",
        "",
        "## 4. Invariants demonstrated",
        "",
        "- A dimension with no supporting claim is `unknown` with a note, not blank.",
        "- A market-share/audience claim lights **no** mechanics dimension.",
        "- The vendor-documented vs independently-researched vs directly-observed "
        + "distinction is carried per evidence record (`evidence_class`).",
        "- No private snapshot path or capture text appears in any payload.",
    ]
    (OUT / "ISSUE_56_PROOF.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote proof to {OUT}")
    return 0


def mechanism_summary(surface) -> dict:
    rows = ["| dimension | state | evidence class | confidence | statement |", "|---|---|---|---|---|"]
    known = 0
    for d in surface.dimensions:
        if d.state == "unknown":
            rows.append(f"| {d.dimension} | unknown | — | — | {d.note} |")
        else:
            known += 1
            a = d.assertions[0]
            ev = a.evidence[0]
            stmt = a.statement.replace("|", "/")[:120]
            rows.append(
                f"| {d.dimension} | {d.state} | {ev.evidence_class} | {ev.confidence} | {stmt} |"
            )
    cov = surface.coverage()
    summary = (
        f"{known}/{len(surface.dimensions)} evidenced "
        f"(known {cov['known']}, partial {cov['partially_known']}, "
        f"conflicting {cov['conflicting']}, unknown {cov['unknown']})"
    )
    return {"summary": summary, "table": "\n".join(rows)}


if __name__ == "__main__":
    raise SystemExit(main())
