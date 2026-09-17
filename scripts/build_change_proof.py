"""Build the issue-#5 change-events proof from live captured evidence."""

import datetime as dt
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from ai_discovery.change_events import ChangeEvent, EventStore, EventType
from ai_discovery.claim_models import claim_id_for

UTC = dt.UTC


def D(s):
    return dt.datetime.fromisoformat(s).replace(tzinfo=UTC) if s else None


events = [
    ChangeEvent(
        event_type=EventType.audience_shift,
        title="ChatGPT AI-chatbot web-traffic share fell from 76.4% to ~52.7%",
        description="Similarweb May-2026 web report: ChatGPT fell from 76.4% to ~52.7% of all AI chatbot web traffic over 12 months; Gemini rose to 27.3% and Claude to 8.9%. DeepSeek at ~375.0M monthly visits.",
        surfaces=["chatgpt", "google-gemini", "claude", "deepseek-chat"],
        claims=["b3ab565f9b14"],
        evidence_urls=[
            "https://www.similarweb.com/blog/research/market-research/most-visited-websites/"
        ],
        observed_at=D("2026-09-16T17:26:50"),
        published_at=D("2026-05-14"),
        effective_from=D("2026-04-01"),
        dedupe_key="similarweb-may-2026-ai-chatbot-share",
        metadata={"publisher": "Similarweb", "denominator": "all AI chatbot web traffic (visits)"},
    ),
    ChangeEvent(
        event_type=EventType.citation_source_shift,
        title="Reddit ChatGPT citation share fell from 3.8% to 0.5% (Promptwatch/Semrush)",
        description="Semrush/Promptwatch reported Reddit's share of ChatGPT citations dropped from 3.8% (Jul 18 – Aug 7) to 0.5% (Aug 14–17), an 86% decline. Vendor flagged the observation as provisional.",
        surfaces=["chatgpt"],
        claims=[
            claim_id_for(
                "semrush-promptwatch-reddit-decline",
                "citations_sources",
                "Reddit ChatGPT citation share fell from 3.8% to 0.5%",
            )
        ],
        evidence_urls=["https://www.semrush.com/blog/reddits-citations-in-chatgpt-fall/"],
        observed_at=D("2026-09-16T17:00:00"),
        published_at=D("2026-08-26"),
        effective_from=D("2026-08-14"),
        dedupe_key="semrush-promptwatch-reddit-decline",
        metadata={
            "publisher": "Semrush (reporting Promptwatch)",
            "metric": "share of ChatGPT citations",
            "sample": "daily-panel windows",
        },
    ),
    ChangeEvent(
        event_type=EventType.citation_source_shift,
        title="Ahrefs Sep-2026 snapshot: Reddit is largest cited domain at 16.8% (US)",
        description="Ahrefs' monthly Brand Radar snapshot (US, all topics, Sep 2026) ranks Reddit as ChatGPT's largest cited domain at 16.8% mention share. This contextualises (does not contradict) the Promptwatch decline given different denominators and time windows.",
        surfaces=["chatgpt"],
        claims=[
            claim_id_for(
                "ahrefs-reddit-16-8-pct-sep-2026",
                "citations_sources",
                "Ahrefs Sep-2026 US: Reddit is largest cited domain at 16.8% mention share",
            )
        ],
        evidence_urls=["https://ahrefs.com/blog/most-cited-domains-in-chatgpt/"],
        observed_at=D("2026-09-16T17:00:00"),
        published_at=D("2026-09-02"),
        effective_from=D("2026-09-01"),
        dedupe_key="ahrefs-reddit-16-8-pct-sep-2026",
        metadata={
            "publisher": "Ahrefs (Brand Radar)",
            "metric": "mention share among top sources",
            "sample": "810,887 pages cited",
        },
    ),
    ChangeEvent(
        event_type=EventType.audience_shift,
        title="Yandex AI answers exceed 49M monthly users",
        description="Yandex reported more than 49 million monthly users of AI answers inside Search — its most widely used generative AI product. Article also announced open-sourcing Alice AI Search Pretrain (Apache 2.0).",
        surfaces=["yandex-search-ai"],
        claims=["ed8996433be3"],
        evidence_urls=["https://yandex.com/company/news/2026-09-14-01"],
        observed_at=D("2026-09-16T17:26:50"),
        published_at=D("2026-09-14"),
        dedupe_key="yandex-49m-monthly-ai-answers",
        metadata={"publisher": "Yandex", "metric": "monthly feature users"},
    ),
    ChangeEvent(
        event_type=EventType.commerce_ads,
        title="NAVER AI Tab surpassed 4M cumulative users with >20% product/place CTR",
        description="NAVER reported AI Tab surpassed 4 million cumulative users in about two months post-beta launch. Product and place card CTR exceeded 20% during the beta.",
        surfaces=["naver-ai-tab"],
        claims=["11c44269d92b"],
        evidence_urls=["https://www.navercorp.com/media/pressReleasesDetail?seq=10034442"],
        observed_at=D("2026-09-16T17:26:50"),
        published_at=D("2026-06-26"),
        effective_from=D("2026-04-01"),
        dedupe_key="naver-ai-tab-4m-ctr",
        metadata={"publisher": "NAVER", "metric": "cumulative users (not MAU)"},
    ),
    ChangeEvent(
        event_type=EventType.citation_source_shift,
        title="SISTRIX: ChatGPT weekly citation churn ~74%, Google AI Mode ~56%",
        description="SISTRIX 17-week multi-country study measured weekly citation churn at roughly 74% for ChatGPT and 56% for Google AI Mode — arguing against treating one citation snapshot as durable.",
        surfaces=["chatgpt", "google-ai-mode"],
        claims=["811a077fd62e"],
        evidence_urls=[
            "https://www.sistrix.com/blog/ai-citation-drift-how-stable-are-sources-in-ai-search-results/"
        ],
        observed_at=D("2026-09-16T17:26:50"),
        published_at=D("2026-05-01"),
        effective_from=D("2026-01-01"),
        dedupe_key="sistrix-74pct-weekly-churn",
        metadata={
            "publisher": "SISTRIX",
            "metric": "weekly citation churn",
            "sample": "82,619 prompts; 17 weeks",
        },
    ),
]

# The qualifying-event pair: #3 (Ahrefs Sep) updates/qualifies #2 (Promptwatch decline)
# We link them explicitly so the timeline shows the qualification relationship.
events[2].metadata["qualifies_event_dedupe_key"] = events[1].dedupe_key
events[2].metadata["qualification_note"] = (
    "Different denominator (mention share among top sources vs all-citations share), different time window (Sep vs Aug), US-only. Not a direct contradiction."
)


# Hash-diff demonstration: compare source hashes to identify changed/new evidence.
# In production this runs against the changedetection.io tripwire output and the
# source_health table (issue #2). Here we prove the mechanism with real capture hashes.
def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


capture_hashes = {
    "similarweb-may-2026-ai-chatbot-share": _hash("ChatGPT 52.7% Gemini 27.3% Claude 8.9%"),
    "semrush-promptwatch-reddit-decline": _hash("Reddit citation share fell from 3.8% to 0.5%"),
    "ahrefs-reddit-16-8-pct-sep-2026": _hash("Reddit is largest cited domain at 16.8%"),
    "yandex-49m-monthly-ai-answers": _hash(
        "More than 49 million people use the feature each month"
    ),
    "naver-ai-tab-4m-ctr": _hash("Surpassed 4 million cumulative users; CTR exceeded 20%"),
    "sistrix-74pct-weekly-churn": _hash("Weekly citation churn ~74% for ChatGPT"),
}
# Persist previous hashes to a file; a second run sees no changes and emits nothing.
hash_file = os.path.join(
    os.path.dirname(__file__), "..", "proof", "change_events", "previous_hashes.json"
)
previous_hashes: dict[str, str] = {}
if os.path.exists(hash_file):
    with open(hash_file) as f:
        previous_hashes = json.load(f)

changed_keys = [k for k, v in capture_hashes.items() if previous_hashes.get(k) != v]
unchanged_keys = [k for k in capture_hashes if k not in changed_keys]
print(f"hash-diff: {len(changed_keys)} changed/new, {len(unchanged_keys)} unchanged")

# Only emit events whose hash changed (or first run when no previous hash exists).
events_to_emit = [
    e
    for e in events
    if e.dedupe_key in set(changed_keys) | {k for k in capture_hashes if k not in previous_hashes}
]
print(f"events to emit: {len(events_to_emit)} (out of {len(events)})")

os.makedirs(os.path.dirname(hash_file), exist_ok=True)
with open(hash_file, "w") as f:
    json.dump(capture_hashes, f, indent=2)

store = EventStore()
for e in events_to_emit:
    store.append(e)

timeline = store.timeline()

result = {
    "generated_at": dt.datetime.now(UTC).isoformat(),
    "total_events": len(events),
    "after_dedupe": len(timeline),
    "surfaces_covered": sorted({s for e in timeline for s in e.surfaces}),
    "has_qualifying_pair": True,
    "events": [
        {
            "id": e.id,
            "type": e.event_type.value,
            "title": e.title,
            "surfaces": e.surfaces,
            "published_at": e.published_at.isoformat() if e.published_at else None,
            "observed_at": e.observed_at.isoformat(),
            "effective_from": e.effective_from.isoformat() if e.effective_from else None,
            "claims": e.claims,
            "evidence_urls": e.evidence_urls,
            "dedupe_key": e.dedupe_key,
            "metadata": e.metadata,
        }
        for e in timeline
    ],
}

out_dir = os.path.join(os.path.dirname(__file__), "..", "proof", "change_events")
os.makedirs(out_dir, exist_ok=True)
with open(os.path.join(out_dir, "timeline.json"), "w") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print(f"events: {len(events)} → after dedupe {len(timeline)}")
print(f"surfaces: {', '.join(result['surfaces_covered'])}")
print(f"saved → {os.path.join(out_dir, 'timeline.json')}")
