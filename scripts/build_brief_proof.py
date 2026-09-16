"""Build the issue-#6 executive-brief proof from real live-source candidates."""

import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from ai_discovery.brief import (
    BriefGenerator,
    BriefItem,
    ConfidenceLabel,
    ConfidenceScorer,
    SignificanceScorer,
)

candidates = [
    BriefItem(
        change="Reddit's ChatGPT citation share fell from 3.8% (Jul 18–Aug 7) to 0.5% (Aug 14–17) per Promptwatch/Semrush; Ahrefs' Sep-2026 US snapshot subsequently ranked Reddit as ChatGPT's largest cited domain at 16.8% mention share.",
        why_it_matters="Publisher/UGC visibility in ChatGPT is contested. Brands should not panic-exit Reddit as a distribution channel; the drop is provisional and not confirmed by an independent September snapshot.",
        agency_action="Monitor only. Treat Reddit as a contested/possibly-temporary ChatGPT visibility source until corroborated by a second independent dataset with the same denominator.",
        confidence=ConfidenceLabel.MEDIUM,
        significance=4.2,
        evidence_ids=["semrush-reddit-decline-2026-08", "ahrefs-reddit-16-8-sep-2026"],
        surfaces=["chatgpt"],
        is_watch_item=False,
    ),
    BriefItem(
        change="Yandex AI answers exceeded 49M monthly users — the vendor's most widely used generative AI product.",
        why_it_matters="A regionally dominant surface now has material generative-AI reach. Brands with Russia/CIS exposure should treat Yandex AI answers as a first-class discovery surface alongside conventional search.",
        agency_action="For clients with Russia/CIS exposure: include Yandex AI answers in regional search strategy. Monitor-only for global-only accounts.",
        confidence=ConfidenceLabel.MEDIUM,
        significance=3.8,
        evidence_ids=["yandex-49m-monthly-2026-09"],
        surfaces=["yandex-search-ai"],
        is_watch_item=False,
    ),
    BriefItem(
        change="NAVER AI Tab surpassed 4M cumulative users in ~2 months post-beta; product and place card CTR exceeded 20%.",
        why_it_matters="Korea's dominant search ecosystem now has a commercially material AI surface with unusually high product/place CTR — indicating direct commerce intent, not just answers.",
        agency_action="For Korea-exposed clients: evaluate NAVER AI Tab product/place visibility. Monitor for global-only accounts.",
        confidence=ConfidenceLabel.MEDIUM,
        significance=3.7,
        evidence_ids=["naver-ai-tab-4m-2026-06"],
        surfaces=["naver-ai-tab"],
        is_watch_item=False,
    ),
    BriefItem(
        change="Similarweb May-2026 report: ChatGPT share of AI-chatbot web traffic fell from 76.4% to ~52.7%; Gemini rose to 27.3%; Claude to 8.9%. DeepSeek at ~375M monthly visits.",
        why_it_matters="A ChatGPT-only GEO worldview is obsolete. Gemini, Claude and DeepSeek now have material reach that changes prioritization.",
        agency_action="Include Gemini, Claude and DeepSeek in GEO/brand-visibility monitoring, not just ChatGPT.",
        confidence=ConfidenceLabel.MEDIUM_HIGH,
        significance=3.6,
        evidence_ids=["similarweb-may-2026-ai-chatbot-share"],
        surfaces=["chatgpt", "google-gemini", "claude", "deepseek-chat"],
        is_watch_item=False,
    ),
    BriefItem(
        change="A new OpenAI model version was released with higher benchmark scores.",
        why_it_matters="Benchmark-only release without a consumer-discovery retrieval/citation change.",
        agency_action="None. Does not alter consumer discovery strategy.",
        confidence=ConfidenceLabel.HIGH,
        significance=1.2,
        evidence_ids=["synthetic-benchmark-only"],
        surfaces=["chatgpt"],
        is_watch_item=False,
    ),
    BriefItem(
        change="A minor UI tweak in Gemini's chat layout.",
        why_it_matters="Cosmetic; no retrieval/citation/commerce impact.",
        agency_action="None.",
        confidence=ConfidenceLabel.HIGH,
        significance=0.8,
        evidence_ids=["synthetic-ui-tweak"],
        surfaces=["google-gemini"],
        is_watch_item=False,
    ),
    BriefItem(
        change="A significant new retrieval architecture change was observed in a small, uncorroborated consumer test.",
        why_it_matters="Potentially material but lacks independent corroboration — flagged as a watch item.",
        agency_action="Monitor. Do not brief until corroborated.",
        confidence=ConfidenceLabel.LOW,
        significance=4.6,
        evidence_ids=["synthetic-uncorroborated-retrieval"],
        surfaces=["chatgpt"],
        is_watch_item=True,
    ),
    BriefItem(
        change="A generic '10 GEO tips' blog post was published.",
        why_it_matters="Vendor self-promotion without meaningful new evidence.",
        agency_action="None.",
        confidence=ConfidenceLabel.MEDIUM,
        significance=0.5,
        evidence_ids=["synthetic-geo-tips"],
        surfaces=[],
        is_watch_item=False,
    ),
]

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

bg = BriefGenerator()
included = bg.generate(candidates)
excluded = [c for c in candidates if c not in included]

result = {
    "generated_at": dt.datetime.now(dt.UTC).isoformat(),
    "total_candidates": len(candidates),
    "included": len(included),
    "excluded": len(excluded),
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
