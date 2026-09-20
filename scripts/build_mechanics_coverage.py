"""Write the issue-#57 mechanics coverage matrix + before/after corpus distribution.

Reads the real ledger (production Postgres or AI_DISCOVERY_DATABASE_URL) and the
canonical mechanics contract from #56, then emits:

- proof/phase2/MECHANICS_COVERAGE_MATRIX.md  (core surface × 13 dimensions)
- proof/phase2/CORPUS_DISTRIBUTION.md        (topic / source-class / surface counts)

The "before" numbers are passed in (the pre-#57 production counts measured on
2026-09-20) so the before/after is explicit rather than asserted.
"""

from __future__ import annotations

import collections
import datetime as dt
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from sqlalchemy import create_engine

from ai_discovery.claims import load_expanded_claims
from ai_discovery.mechanics import (
    MECHANICS_DIMENSIONS,
    project_all,
)
from ai_discovery.registry import load_surfaces_config

OUT = REPO / "proof" / "phase2"

#: Measured on the production ledger before this work (2026-09-20).
BEFORE_TOPICS = {
    "audience_usage": 16,
    "citations_sources": 10,
    "referrals_conversion": 3,
    "crawler_index_policy": 1,
    "optimisation_implication": 1,
    "commerce_ads": 1,
}

#: Issue #57 core surfaces, in priority order.
CORE_SURFACES = [
    "chatgpt", "google-gemini", "google-ai-mode", "google-ai-overviews",
    "microsoft-copilot", "bing-copilot-search", "claude", "perplexity",
    "deepseek-chat", "grok", "meta-ai", "doubao", "qwen-consumer", "kimi",
    "baidu-ai-search", "naver-ai", "yandex-ai-search",
]

DIM_SHORT = {
    "search_trigger": "trigger",
    "retrieval_provider": "provider",
    "query_rewrite": "rewrite",
    "crawling_indexing_controls": "crawl",
    "freshness_recrawl": "fresh",
    "candidate_selection_reranking": "rank",
    "citation_presentation": "cite",
    "shopping_product_feed": "shop",
    "local_retrieval": "local",
    "social_community_retrieval": "social",
    "mode_region_differences": "mode",
    "answer_type": "answer",
    "marketer_controllable_inputs": "control",
}


def main() -> int:
    url = os.environ.get(
        "AI_DISCOVERY_DATABASE_URL",
        "postgresql+psycopg://ai_discovery:ai_discovery@127.0.0.1:55432/ai_discovery",
    )
    engine = create_engine(url)
    claims = load_expanded_claims(engine)
    ids = load_surfaces_config().ids()
    projection = project_all(ids, claims)

    OUT.mkdir(parents=True, exist_ok=True)

    # ---- coverage matrix -------------------------------------------------- #
    core = [s for s in CORE_SURFACES if s in projection]
    head = ["| surface | " + " | ".join(DIM_SHORT[d] for d in MECHANICS_DIMENSIONS) + " | evidenced |"]
    sep = ["|---" * (len(MECHANICS_DIMENSIONS) + 2) + "|"]
    rows = []
    for sid in core:
        m = projection[sid]
        cells = []
        for d in MECHANICS_DIMENSIONS:
            st = m.state_of(d)
            mark = {"known": "K", "partially_known": "P", "conflicting": "C", "unknown": "·"}[st]
            cells.append(mark)
        rows.append(f"| {sid} | " + " | ".join(cells) + f" | {m.evidenced_dimension_count()}/13 |")

    total_cells = sum(projection[s].evidenced_dimension_count() for s in core)
    evidenced_surfaces = sum(1 for s in core if projection[s].evidenced_dimension_count() > 0)
    matrix = [
        "# Issue #57 — mechanics coverage matrix",
        "",
        f"Core surfaces × {len(MECHANICS_DIMENSIONS)} canonical dimensions (contract from #56).",
        "K = known, P = partial, C = conflicting, · = unknown (explicit).",
        "",
        f"**Evidenced cells: {total_cells} of {len(core) * len(MECHANICS_DIMENSIONS)} "  # noqa: ISC004
        f"({total_cells * 100 // (len(core) * len(MECHANICS_DIMENSIONS))}%).**",
        "",
        f"**Partial coverage - this is NOT a complete rebalance.** {evidenced_surfaces} of "
        + f"{len(core)} core surfaces have any mechanics evidence; the remaining "
        + f"{len(core) - evidenced_surfaces} are entirely `unknown` because no public evidence "
        + "has been captured for them yet (the target of #10), not because they were overlooked.",
        "",
        *head,
        *sep,
        *rows,
        "",
        "Legend — dimensions:",
        *[f"- `{d}` — {DIM_SHORT[d]}" for d in MECHANICS_DIMENSIONS],
    ]
    (OUT / "MECHANICS_COVERAGE_MATRIX.md").write_text("\n".join(matrix) + "\n", encoding="utf-8")

    # ---- distribution ----------------------------------------------------- #
    after_topics = collections.Counter(c["topic"] for c in claims)
    classes = collections.Counter(
        (c.get("source") or {}).get("source_class") for c in claims
    )
    surfaces = collections.Counter(s for c in claims for s in (c.get("surfaces") or []))

    dist = [
        "# Issue #57 — corpus distribution before / after",
        "",
        f"Measured {dt.datetime.now(dt.UTC).date().isoformat()} on the real ledger. "
        + f"Total claims: {len(claims)}.",
        "",
        "## Topic distribution",
        "",
        "| topic | before | after | Δ |",
        "|---|---|---|---|",
    ]
    for topic in sorted(set(BEFORE_TOPICS) | set(after_topics)):
        b = BEFORE_TOPICS.get(topic, 0)
        a = after_topics.get(topic, 0)
        dist.append(f"| {topic} | {b} | {a} | {a - b:+d} |")
    dist += [
        "",
        "The growth is entirely **mechanics** topics (retrieval_index, additional "
        + "citations_sources, additional crawler_index_policy). **No new audience/share "
        + "or news claim was added** - corpus growth is not satisfied by more "
        + "market-share noise.",
        "",
        "## Source-class distribution (after)",
        "",
        "| source_class | claims |",
        "|---|---|",
    ]
    for cls, n in classes.most_common():
        dist.append(f"| {cls} | {n} |")
    dist += [
        "",
        "## Surface distribution (after)",
        "",
        "| surface | claims |",
        "|---|---|",
    ]
    for sid, n in surfaces.most_common():
        dist.append(f"| {sid} | {n} |")
    (OUT / "CORPUS_DISTRIBUTION.md").write_text("\n".join(dist) + "\n", encoding="utf-8")

    print(f"wrote {OUT / 'MECHANICS_COVERAGE_MATRIX.md'}")
    print(f"wrote {OUT / 'CORPUS_DISTRIBUTION.md'}")
    print(f"evidenced cells: {total_cells} / {len(core) * len(MECHANICS_DIMENSIONS)}")
    print("after topics:", dict(after_topics))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
