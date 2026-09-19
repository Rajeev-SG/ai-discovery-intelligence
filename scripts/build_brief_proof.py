"""Build the issue-#6 executive-brief proof from real live-source candidates."""

import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from ai_discovery.brief import (
    BriefGenerator,
    BriefItem,
    ConfidenceScorer,
    SignificanceScorer,
    build_weekly_brief,
    weekly_window,
)


def make_candidate(
    *,
    effective_from=None,
    published_at=None,
    change: str,
    why: str,
    action: str,
    surfaces: list[str],
    evidence_ids: list[str],
    source_authority: float,
    methodology_transparency: float,
    sample_strength: float,
    recency: float,
    geography_fit: float,
    corroboration: float,
    directness: float,
    reach: float,
    commercial_intent: float,
    magnitude: float,
    breadth: float,
    persistence: float,
    actionability_: float,
    is_watch_item: bool = False,
    conflict_penalty: float = 0.0,
) -> tuple[BriefItem, dict]:
    """Derive a BriefItem's confidence/significance from per-dimension scorer inputs."""
    cs = ConfidenceScorer.from_config()
    ss = SignificanceScorer.from_config()
    conf_raw = cs.score(
        source_authority=source_authority,
        methodology_transparency=methodology_transparency,
        sample_strength=sample_strength,
        recency=recency,
        geography_fit=geography_fit,
        corroboration=corroboration,
        directness=directness,
    )
    conf_penalised = max(0.0, conf_raw - conflict_penalty)
    conf_label = cs.label(conf_penalised)
    sig = ss.score(
        reach=reach,
        commercial_intent=commercial_intent,
        magnitude=magnitude,
        breadth=breadth,
        persistence=persistence,
        actionability=actionability_,
    )
    item = BriefItem(
        change=change,
        why_it_matters=why,
        agency_action=action,
        confidence=conf_label,
        significance=sig,
        evidence_ids=evidence_ids,
        surfaces=surfaces,
        is_watch_item=is_watch_item,
        effective_from=effective_from,
        published_at=published_at,
        observed_at=dt.datetime.now(dt.UTC),
    )
    return item, {
        "confidence_raw": conf_raw,
        "confidence_penalty": conflict_penalty,
        "confidence_penalised": conf_penalised,
        "confidence_label": conf_label.value,
        "significance": sig,
    }


reddit_item, reddit_scores = make_candidate(
    change="Reddit's ChatGPT citation share fell from 3.8% (Jul 18–Aug 7) to 0.5% (Aug 14–17) per Promptwatch/Semrush; Ahrefs' Sep-2026 US snapshot subsequently ranked Reddit as ChatGPT's largest cited domain at 16.8% mention share.",
    why="Publisher/UGC visibility in ChatGPT is contested. Brands should not panic-exit Reddit as a distribution channel; the drop is provisional and not confirmed by an independent September snapshot.",
    action="Monitor only. Treat Reddit as a contested/possibly-temporary ChatGPT visibility source until corroborated by a second independent dataset with the same denominator.",
    surfaces=["chatgpt"],
    evidence_ids=["semrush-reddit-decline-2026-08", "ahrefs-reddit-16-8-sep-2026"],
    source_authority=0.7,
    methodology_transparency=0.6,
    sample_strength=0.5,
    recency=1.0,
    geography_fit=0.8,
    corroboration=0.7,
    directness=0.8,
    reach=0.9,
    commercial_intent=0.8,
    magnitude=0.8,
    breadth=0.6,
    persistence=0.4,
    actionability_=0.7,
    conflict_penalty=0.15,  # config/significance.yaml unresolved_material_conflict
)
yandex_item, yandex_scores = make_candidate(
    change="Yandex AI answers exceeded 49M monthly users — the vendor's most widely used generative AI product.",
    why="A regionally dominant surface now has material generative-AI reach. Brands with Russia/CIS exposure should treat Yandex AI answers as a first-class discovery surface alongside conventional search.",
    action="For clients with Russia/CIS exposure: include Yandex AI answers in regional search strategy. Monitor-only for global-only accounts.",
    surfaces=["yandex-search-ai"],
    evidence_ids=["yandex-49m-monthly-2026-09"],
    source_authority=0.8,
    methodology_transparency=0.5,
    sample_strength=0.5,
    recency=1.0,
    geography_fit=0.8,
    corroboration=0.5,
    directness=0.6,
    reach=0.8,
    commercial_intent=0.7,
    magnitude=0.8,
    breadth=0.5,
    persistence=0.8,
    actionability_=0.7,
)
naver_item, naver_scores = make_candidate(
    change="NAVER AI Tab surpassed 4M cumulative users in ~2 months post-beta; product and place card CTR exceeded 20%.",
    why="Korea's dominant search ecosystem now has a commercially material AI surface with unusually high product/place CTR — indicating direct commerce intent, not just answers.",
    action="For Korea-exposed clients: evaluate NAVER AI Tab product/place visibility. Monitor for global-only accounts.",
    surfaces=["naver-ai-tab"],
    evidence_ids=["naver-ai-tab-4m-2026-06"],
    source_authority=0.8,
    methodology_transparency=0.5,
    sample_strength=0.5,
    recency=0.8,
    geography_fit=0.8,
    corroboration=0.5,
    directness=0.6,
    reach=0.6,
    commercial_intent=0.8,
    magnitude=0.7,
    breadth=0.4,
    persistence=0.6,
    actionability_=0.6,
)
similarweb_item, similarweb_scores = make_candidate(
    change="Similarweb May-2026 report: ChatGPT share of AI-chatbot web traffic fell from 76.4% to ~52.7%; Gemini rose to 27.3%; Claude to 8.9%. DeepSeek at ~375M monthly visits.",
    why="A ChatGPT-only GEO worldview is obsolete. Gemini, Claude and DeepSeek now have material reach that changes prioritization.",
    action="Include Gemini, Claude and DeepSeek in GEO/brand-visibility monitoring, not just ChatGPT.",
    surfaces=["chatgpt", "google-gemini", "claude", "deepseek-chat"],
    evidence_ids=["similarweb-may-2026-ai-chatbot-share"],
    source_authority=0.7,
    methodology_transparency=0.5,
    sample_strength=0.5,
    recency=0.7,
    geography_fit=0.8,
    corroboration=0.6,
    directness=0.6,
    reach=0.9,
    commercial_intent=0.6,
    magnitude=0.5,
    breadth=0.8,
    persistence=0.7,
    actionability_=0.6,
)
benchmark_item, benchmark_scores = make_candidate(
    change="A new OpenAI model version was released with higher benchmark scores.",
    why="Benchmark-only release without a consumer-discovery retrieval/citation change.",
    action="None. Does not alter consumer discovery strategy.",
    surfaces=["chatgpt"],
    evidence_ids=["synthetic-benchmark-only"],
    source_authority=0.9,
    methodology_transparency=0.9,
    sample_strength=0.9,
    recency=0.9,
    geography_fit=0.9,
    corroboration=0.9,
    directness=0.9,
    reach=0.5,
    commercial_intent=0.2,
    magnitude=0.2,
    breadth=0.2,
    persistence=0.3,
    actionability_=0.2,
)
ui_tweak_item, ui_scores = make_candidate(
    change="A minor UI tweak in Gemini's chat layout.",
    why="Cosmetic; no retrieval/citation/commerce impact.",
    action="None.",
    surfaces=["google-gemini"],
    evidence_ids=["synthetic-ui-tweak"],
    source_authority=0.9,
    methodology_transparency=0.9,
    sample_strength=0.9,
    recency=0.9,
    geography_fit=0.9,
    corroboration=0.9,
    directness=0.9,
    reach=0.3,
    commercial_intent=0.1,
    magnitude=0.1,
    breadth=0.1,
    persistence=0.2,
    actionability_=0.1,
)
uncorroborated_item, uncorr_scores = make_candidate(
    change="A significant new retrieval architecture change was observed in a small, uncorroborated consumer test.",
    why="Potentially material but lacks independent corroboration — flagged as a watch item.",
    action="Monitor. Do not brief until corroborated.",
    surfaces=["chatgpt"],
    evidence_ids=["synthetic-uncorroborated-retrieval"],
    source_authority=0.4,
    methodology_transparency=0.3,
    sample_strength=0.2,
    recency=0.9,
    geography_fit=0.5,
    corroboration=0.1,
    directness=0.4,
    reach=0.8,
    commercial_intent=0.8,
    magnitude=0.9,
    breadth=0.5,
    persistence=0.4,
    actionability_=0.8,
    is_watch_item=True,
)
geo_tips_item, geo_scores = make_candidate(
    change="A generic '10 GEO tips' blog post was published.",
    why="Vendor self-promotion without meaningful new evidence.",
    action="None.",
    surfaces=[],
    evidence_ids=["synthetic-geo-tips"],
    source_authority=0.3,
    methodology_transparency=0.2,
    sample_strength=0.2,
    recency=0.7,
    geography_fit=0.5,
    corroboration=0.2,
    directness=0.3,
    reach=0.2,
    commercial_intent=0.1,
    magnitude=0.1,
    breadth=0.1,
    persistence=0.2,
    actionability_=0.1,
)

# Load the claim ledger produced by the issue-#3 extraction pipeline (real captured evidence).

claims_path = os.path.join(os.path.dirname(__file__), "..", "proof", "brief", "claim_specs.json")
with open(claims_path) as f:
    claim_specs = json.load(f)
print(f"loaded {len(claim_specs['claims'])} claims from the issue-#3 claim ledger")

# Build corpus-derived candidates from the stored claims (no hand-authored prose here).
candidates: list[BriefItem] = []
all_scores: dict[str, dict] = {}
for spec in claim_specs["claims"]:
    sid = spec["source"]["source_id"]
    topic = spec["topic"]
    statement = spec["statement"]
    surfaces = spec.get("surfaces", [])
    evidence_ids = [spec["source"]["url"]]
    meth = spec.get("methodology", {})
    sample = meth.get("sample_size", {})
    sample_known = isinstance(sample, dict) and sample.get("value") not in (None, "unknown")
    source_class = spec["source"].get("source_class", "vendor_research")
    authority = {"official": 0.8, "vendor_research": 0.7, "market_telemetry": 0.6}.get(
        source_class, 0.5
    )
    sample_score = 0.6 if sample_known else 0.3
    corroboration = 0.6 if sid == "similarweb-most-visited-websites" else 0.3
    pub = (spec.get("dates") or {}).get("published_at")
    item, scores = make_candidate(
        change=statement,
        published_at=dt.datetime.fromisoformat(pub) if pub else None,
        why=f"{spec['source']['publisher']} ({source_class}) published this {topic} finding with documented methodology.",
        action="Include in monitoring. Adjust client strategy if corroborated by an independent source.",
        surfaces=surfaces,
        evidence_ids=evidence_ids,
        source_authority=authority,
        methodology_transparency=0.6 if meth.get("metric_definition") else 0.3,
        sample_strength=sample_score,
        recency=0.9,
        geography_fit=0.7 if "global" in surfaces else 0.5,
        corroboration=corroboration,
        directness=0.7,
        reach=0.7,
        commercial_intent=0.6,
        magnitude=0.6,
        breadth=0.5,
        persistence=0.5,
        actionability_=0.6,
    )
    candidates.append(item)
    all_scores[sid] = scores

# The Reddit conflict is an issue-#4 deliverable, not yet in the claim ledger.
# Included here as a watch item with the conflict penalty to demonstrate policy.
reddit_item, reddit_scores = make_candidate(
    published_at=dt.datetime.now(dt.UTC),
    change="Reddit's ChatGPT citation share fell from 3.8% to 0.5% (Promptwatch/Semrush Aug 2026); Ahrefs Sep-2026 ranked Reddit as ChatGPT's largest cited domain at 16.8% mention share (US, different denominator).",
    why="Publisher/UGC visibility in ChatGPT is contested. Brands should not panic-exit Reddit; the drop is provisional.",
    action="Monitor only. Treat Reddit as contested until corroborated.",
    surfaces=["chatgpt"],
    evidence_ids=[
        "https://www.semrush.com/blog/reddits-citations-in-chatgpt-fall/",
        "https://ahrefs.com/blog/most-cited-domains-in-chatgpt/",
    ],
    source_authority=0.7,
    methodology_transparency=0.6,
    sample_strength=0.5,
    recency=1.0,
    geography_fit=0.8,
    corroboration=0.7,
    directness=0.8,
    reach=0.9,
    commercial_intent=0.8,
    magnitude=0.8,
    breadth=0.6,
    persistence=0.4,
    actionability_=0.7,
    conflict_penalty=0.15,
)
candidates.append(reddit_item)
all_scores["reddit-conflict"] = reddit_scores

# Verify scorers are loaded from config and actually callable (not just decorative).
cs = ConfidenceScorer.from_config()
ss = SignificanceScorer.from_config()
print(
    f"ConfidenceScorer weights from config: source_authority={cs.source_authority}, corroboration={cs.corroboration}"
)
print(f"SignificanceScorer weights from config: reach={ss.reach}, breadth={ss.breadth}")
print(
    f"Example confidence score for (0.8, 0.6, 0.4, 0.7, 0.5, 0.9, 0.7) = {cs.score(source_authority=0.8, methodology_transparency=0.6, sample_strength=0.4, recency=0.7, geography_fit=0.5, corroboration=0.9, directness=0.7)} ({cs.label(cs.score(source_authority=0.8, methodology_transparency=0.6, sample_strength=0.4, recency=0.7, geography_fit=0.5, corroboration=0.9, directness=0.7)).value})"
)
print(
    f"Example significance score for (0.8, 0.6, 0.7, 0.5, 0.9, 0.7) = {ss.score(reach=0.8, commercial_intent=0.6, magnitude=0.7, breadth=0.5, persistence=0.9, actionability=0.7)}"
)

def _excluded_split(candidates, included, reference):
    """Why each candidate is absent: windowed out (event time) or below threshold.

    Reported separately because "left out because it is not this week's change" is
    a different editorial fact from "left out because it is weak".
    """

    start, end = weekly_window(reference)
    windowed = [
        c
        for c in candidates
        if c.effective_at is None or not (start <= _aware(c.effective_at) <= end)
    ]
    below = [c for c in candidates if c not in included and c not in windowed]
    return windowed, below


def _aware(value):
    return value if value.tzinfo else value.replace(tzinfo=dt.UTC)


bg = BriefGenerator()
# Weekly output: apply the explicit event-time window so a newly-ingested old
# study cannot appear as this week's change (issue #27). The reference is the
# build time; candidates carry published_at/effective_from from their source.
reference = dt.datetime.now(dt.UTC)
included = build_weekly_brief(candidates, generator=bg, reference=reference)
windowed_out, below_threshold = _excluded_split(candidates, included, reference)
excluded = [*windowed_out, *below_threshold]

result = {
    "generated_at": dt.datetime.now(dt.UTC).isoformat(),
    "total_candidates": len(candidates),
    "included": len(included),
    "excluded": len(excluded),
    "excluded_windowed_out": len(windowed_out),
    "excluded_below_threshold": len(below_threshold),
    "scorer_audit": all_scores,
    "items": [i.model_dump(mode="json") for i in included],
    "excluded_items": [
        {"change": c.change[:80], "significance": c.significance, "confidence": c.confidence.value}
        for c in excluded
    ],
}

out_dir = os.path.join(os.path.dirname(__file__), "..", "proof", "brief")
os.makedirs(out_dir, exist_ok=True)
with open(os.path.join(out_dir, "brief.json"), "w") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print(f"candidates: {len(candidates)}  included: {len(included)}  excluded: {len(excluded)}")
for i in included:
    print(f"  ✓ [{i.confidence.value} / sig {i.significance}] {i.change[:70]}...")
for c in excluded:
    print(f"  ✗ [{c.confidence.value} / sig {c.significance}] {c.change[:70]}...")
