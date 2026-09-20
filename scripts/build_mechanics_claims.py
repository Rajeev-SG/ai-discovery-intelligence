"""Build the Phase-2 mechanics claim specs (issue #57) from real captures.

This is the *corpus rebalance*: it authors deterministic claim specs that turn
mechanic-rich evidence already sitting in the committed real captures
(`proof/claim_ledger/captures/`) into validated ledger claims tagged with the
canonical mechanics topics. Every value is a VERBATIM quote from the capture; the
existing extraction lane (`ai_discovery.claims.extract_claim`) re-verifies each
quote against the capture bytes and refuses a claim whose quote is absent, so no
fabricated number can enter the ledger.

Run: uv run python scripts/build_mechanics_claims.py            # write specs JSON
     uv run python scripts/build_mechanics_claims.py --persist  # + persist to DB
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

CAPTURES = REPO / "proof" / "claim_ledger" / "captures"
OUT = REPO / "proof" / "claim_ledger" / "mechanics_claim_specs.json"

# Per-capture observed_at (when the capture was taken; see captures.json).
OBSERVED = {
    "google-search-central-ai": "2026-09-16T21:55:00+00:00",
    "openai-platform-bots": "2026-09-16T21:55:00+00:00",
    "ahrefs-blog-ai": "2026-09-16T21:55:00+00:00",
}
PUBLISHED = {
    "google-search-central-ai": None,
    "openai-platform-bots": None,
    "ahrefs-blog-ai": None,  # no publication date locator in the capture: stays unknown
    "perplexity-blog": None,  # "Sep 9, 2026" shown in the list, no machine-readable locator
}

SOURCES = {
    "perplexity-blog": {
        "source_id": "perplexity-blog",
        "publisher": "Perplexity",
        "url": "https://www.perplexity.ai/hub/blog",
        "canonical_url": "https://www.perplexity.ai/hub/blog",
        "source_class": "official",
    },
    "google-search-central-ai": {
        "source_id": "google-search-central-ai",
        "publisher": "Google",
        "url": "https://developers.google.com/search/docs/appearance/ai-features",
        "canonical_url": "https://developers.google.com/search/docs/appearance/ai-features",
        "source_class": "official",
    },
    "openai-platform-bots": {
        "source_id": "openai-platform-bots",
        "publisher": "OpenAI",
        "url": "https://platform.openai.com/docs/bots",
        "canonical_url": "https://platform.openai.com/docs/bots",
        "source_class": "official",
    },
    "ahrefs-blog-ai": {
        "source_id": "ahrefs-blog-ai",
        "publisher": "Ahrefs",
        "url": "https://ahrefs.com/blog/ai-search-traffic/",
        "canonical_url": "https://ahrefs.com/blog/ai-search-traffic/",
        "source_class": "visibility_research",
    },
}


def _qv(value, quote):
    return {"value": value, "quote": quote}


def _metric(mid, label, *, definition, value, unit, window, scope, comparator="qualitative_finding"):
    return {
        "metric_id": mid,
        "label": label,
        "comparator": comparator,
        "definition": definition,
        "value": value,
        "unit": unit,
        "window": window,
        "scope": scope,
    }


def specs() -> list[dict]:
    out: list[dict] = []

    # ------------------------------------------------------------------ Google
    g = SOURCES["google-search-central-ai"]
    fanout_q = (
        'Both AI Overviews and AI Mode may use a "query fan-out" technique — issuing '
        "multiple related searches across subtopics and data sources — to develop a response."
    )
    out.append({
        "source": g,
        "topic": "retrieval_index",
        "statement": (
            "Google's AI Mode and AI Overviews may use a query fan-out technique, issuing "
            "multiple related searches across subtopics and data sources to build one response."
        ),
        "surfaces": ["google-ai-mode", "google-ai-overviews"],
        "methodology": {
            "measurement_mode": "official_documentation",
            "metric_family": _qv("query fan-out behaviour", fanout_q),
            "metric_definition": _qv(
                "issuing multiple related searches across subtopics and data sources",
                'issuing multiple related searches across subtopics and data sources — to develop a response.',
            ),
            "unit_of_analysis": _qv("a single AI response", fanout_q),
            "denominator": None,
            "prompt_universe": None,
            "sample_size": None,
            "time_window": None,
            "geography": None,
            "geography_basis": "not_stated",
            "language": None,
            "language_basis": "not_stated",
            "devices": None,
            "limitations": ["Documents stated technique, not an observed fan-out rate."],
            "methodology_notes": _qv(
                "Google Search Central AI-features documentation.",
                "AI features and your website",
            ),
        },
        "metrics": [
            _metric(
                "fanout_used",
                "AI Mode and AI Overviews may use query fan-out",
                definition=_qv("query fan-out technique", 'query fan-out" technique'),
                value=_qv("query fan-out", 'query fan-out" technique'),
                unit=_qv("technique", fanout_q),
                window=_qv("current documentation", fanout_q),
                scope=_qv("AI Mode and AI Overviews", "Both AI Overviews and AI Mode may use"),
            )
        ],
        "dates": {
            "published_at": PUBLISHED["google-search-central-ai"],
            "modified_at": None,
            "measured_window": None,
            "observed_at": OBSERVED["google-search-central-ai"],
        },
        "capture_anchors": [{"kind": "verbatim_quote", "quote": fanout_q}],
        "extraction": {
            "method": "deterministic_parser",
            "tool": "ai_discovery.claims",
            "rule_id": "google_ai_fanout_v1",
            "version": "claim-extraction-0.1.0",
        },
        "status": "current",
        "relationship": "new",
    })

    trigger_q = (
        "AI Overviews are only shown when our systems determine that it is additive to "
        "classic Search, and as such, often don't trigger."
    )
    out.append({
        "source": g,
        "topic": "retrieval_index",
        "statement": (
            "Google shows AI Overviews only when its systems judge them additive to classic "
            "Search, so they often do not trigger at all."
        ),
        "surfaces": ["google-ai-overviews"],
        "methodology": {
            "measurement_mode": "official_documentation",
            "metric_family": _qv("AI Overview trigger condition", trigger_q),
            "metric_definition": _qv(
                "shown only when systems determine it is additive to classic Search", trigger_q
            ),
            "unit_of_analysis": _qv("a search query", trigger_q),
            "denominator": None,
            "prompt_universe": None,
            "sample_size": None,
            "time_window": None,
            "geography": None,
            "geography_basis": "not_stated",
            "language": None,
            "language_basis": "not_stated",
            "devices": None,
            "limitations": ["Publisher states a policy; no trigger rate is published."],
            "methodology_notes": _qv(
                "Google Search Central AI-features documentation.",
                "AI features and your website",
            ),
        },
        "metrics": [
            _metric(
                "ai_overview_trigger",
                "AI Overviews trigger conditionally",
                definition=_qv("additive to classic Search", "additive to classic Search"),
                value=_qv("conditional, often does not trigger", trigger_q),
                unit=_qv("policy", trigger_q),
                window=_qv("current documentation", trigger_q),
                scope=_qv("AI Overviews", "AI Overviews are only shown"),
            )
        ],
        "dates": {
            "published_at": PUBLISHED["google-search-central-ai"],
            "modified_at": None,
            "measured_window": None,
            "observed_at": OBSERVED["google-search-central-ai"],
        },
        "capture_anchors": [{"kind": "verbatim_quote", "quote": trigger_q}],
        "extraction": {
            "method": "deterministic_parser",
            "tool": "ai_discovery.claims",
            "rule_id": "google_ai_trigger_v1",
            "version": "claim-extraction-0.1.0",
        },
        "status": "current",
        "relationship": "new",
    })

    support_q = (
        "While responses are being generated, our advanced models identify more supporting "
        "web pages, allowing us to display a wider and more diverse set of helpful links "
        "associated with the response than with a classic web search"
    )
    out.append({
        "source": g,
        "topic": "citations_sources",
        "statement": (
            "While generating an AI response, Google's models identify additional supporting "
            "web pages and display a wider, more diverse set of links than classic web search."
        ),
        "surfaces": ["google-ai-mode", "google-ai-overviews"],
        "methodology": {
            "measurement_mode": "official_documentation",
            "metric_family": _qv("supporting-link presentation", support_q),
            "metric_definition": _qv(
                "models identify more supporting web pages during generation", support_q
            ),
            "unit_of_analysis": _qv("a generated response", support_q),
            "denominator": None,
            "prompt_universe": None,
            "sample_size": None,
            "time_window": None,
            "geography": None,
            "geography_basis": "not_stated",
            "language": None,
            "language_basis": "not_stated",
            "devices": None,
            "limitations": ["Qualitative vendor claim; no link-count measurement."],
            "methodology_notes": _qv(
                "Google Search Central AI-features documentation.",
                "AI features and your website",
            ),
        },
        "metrics": [
            _metric(
                "supporting_links",
                "More supporting links than classic search",
                definition=_qv("supporting web pages", "supporting web pages"),
                value=_qv("wider and more diverse set of helpful links", support_q),
                unit=_qv("links displayed", support_q),
                window=_qv("current documentation", support_q),
                scope=_qv("AI Mode and AI Overviews", "our advanced models"),
            )
        ],
        "dates": {
            "published_at": PUBLISHED["google-search-central-ai"],
            "modified_at": None,
            "measured_window": None,
            "observed_at": OBSERVED["google-search-central-ai"],
        },
        "capture_anchors": [{"kind": "verbatim_quote", "quote": support_q}],
        "extraction": {
            "method": "deterministic_parser",
            "tool": "ai_discovery.claims",
            "rule_id": "google_ai_supporting_links_v1",
            "version": "claim-extraction-0.1.0",
        },
        "status": "current",
        "relationship": "new",
    })

    mode_q = (
        "AI Mode and AI Overviews may use different models and techniques, so the set of "
        "responses and links they show will vary."
    )
    out.append({
        "source": g,
        "topic": "retrieval_index",
        "statement": (
            "Google states AI Mode and AI Overviews may use different models and techniques, "
            "so their responses and links vary between the two surfaces."
        ),
        "surfaces": ["google-ai-mode", "google-ai-overviews"],
        "methodology": {
            "measurement_mode": "official_documentation",
            "metric_family": _qv("mode-level technique variation", mode_q),
            "metric_definition": _qv(
                "may use different models and techniques", mode_q
            ),
            "unit_of_analysis": _qv("surface (AI Mode vs AI Overviews)", mode_q),
            "denominator": None,
            "prompt_universe": None,
            "sample_size": None,
            "time_window": None,
            "geography": None,
            "geography_basis": "not_stated",
            "language": None,
            "language_basis": "not_stated",
            "devices": None,
            "limitations": ["States variation exists; does not enumerate the differences."],
            "methodology_notes": _qv(
                "Google Search Central AI-features documentation.",
                "AI features and your website",
            ),
        },
        "metrics": [
            _metric(
                "mode_variation",
                "Responses vary between AI Mode and AI Overviews",
                definition=_qv("different models and techniques", "different models and techniques"),
                value=_qv("responses and links will vary", mode_q),
                unit=_qv("surface", mode_q),
                window=_qv("current documentation", mode_q),
                scope=_qv("AI Mode and AI Overviews", "AI Mode and AI Overviews may use"),
            )
        ],
        "dates": {
            "published_at": PUBLISHED["google-search-central-ai"],
            "modified_at": None,
            "measured_window": None,
            "observed_at": OBSERVED["google-search-central-ai"],
        },
        "capture_anchors": [{"kind": "verbatim_quote", "quote": mode_q}],
        "extraction": {
            "method": "deterministic_parser",
            "tool": "ai_discovery.claims",
            "rule_id": "google_ai_mode_variation_v1",
            "version": "claim-extraction-0.1.0",
        },
        "status": "current",
        "relationship": "new",
    })

    # ------------------------------------------------------------------ OpenAI
    o = SOURCES["openai-platform-bots"]
    user_q = "ChatGPT-User is not used for crawling the web in an automatic fashion."
    out.append({
        "source": o,
        "topic": "crawler_index_policy",
        "statement": (
            "OpenAI's ChatGPT-User agent is not used to crawl the web automatically; it acts "
            "only in response to a user action."
        ),
        "surfaces": ["chatgpt"],
        "methodology": {
            "measurement_mode": "official_documentation",
            "metric_family": _qv("crawler user-agent purpose", user_q),
            "metric_definition": _qv("not used for crawling the web in an automatic fashion", user_q),
            "unit_of_analysis": _qv("user agent ChatGPT-User", user_q),
            "denominator": None,
            "prompt_universe": None,
            "sample_size": None,
            "time_window": None,
            "geography": None,
            "geography_basis": "not_stated",
            "language": None,
            "language_basis": "not_stated",
            "devices": None,
            "limitations": ["Documents agent purpose, not observed crawl rates."],
            "methodology_notes": _qv("OpenAI crawler documentation.", "Overview of OpenAI Crawlers"),
        },
        "metrics": [
            _metric(
                "chatgpt_user_not_automatic",
                "ChatGPT-User is user-triggered only",
                definition=_qv("user-initiated action", user_q),
                value=_qv("not used for crawling the web in an automatic fashion", user_q),
                unit=_qv("user agent", user_q),
                window=_qv("current documentation", user_q),
                scope=_qv("ChatGPT", "ChatGPT-User"),
            )
        ],
        "dates": {
            "published_at": PUBLISHED["openai-platform-bots"],
            "modified_at": None,
            "measured_window": None,
            "observed_at": OBSERVED["openai-platform-bots"],
        },
        "capture_anchors": [{"kind": "verbatim_quote", "quote": user_q}],
        "extraction": {
            "method": "deterministic_parser",
            "tool": "ai_discovery.claims",
            "rule_id": "openai_chatgpt_user_v1",
            "version": "claim-extraction-0.1.0",
        },
        "status": "current",
        "relationship": "new",
    })

    robots_q = (
        "ChatGPT-User is not used to determine whether content may appear in Search."
    )
    out.append({
        "source": o,
        "topic": "crawler_index_policy",
        "statement": (
            "OpenAI states the ChatGPT-User agent does not determine whether content appears "
            "in Search; that is governed separately."
        ),
        "surfaces": ["chatgpt"],
        "methodology": {
            "measurement_mode": "official_documentation",
            "metric_family": _qv("search eligibility control", robots_q),
            "metric_definition": _qv(
                "not used to determine whether content may appear in Search", robots_q
            ),
            "unit_of_analysis": _qv("user agent ChatGPT-User", robots_q),
            "denominator": None,
            "prompt_universe": None,
            "sample_size": None,
            "time_window": None,
            "geography": None,
            "geography_basis": "not_stated",
            "language": None,
            "language_basis": "not_stated",
            "devices": None,
            "limitations": ["Documents a control boundary, not observed behaviour."],
            "methodology_notes": _qv("OpenAI crawler documentation.", "Overview of OpenAI Crawlers"),
        },
        "metrics": [
            _metric(
                "search_eligibility_separate",
                "ChatGPT-User does not control Search eligibility",
                definition=_qv("appear in Search", robots_q),
                value=_qv("not used to determine whether content may appear in Search", robots_q),
                unit=_qv("user agent", robots_q),
                window=_qv("current documentation", robots_q),
                scope=_qv("ChatGPT", "ChatGPT-User"),
            )
        ],
        "dates": {
            "published_at": PUBLISHED["openai-platform-bots"],
            "modified_at": None,
            "measured_window": None,
            "observed_at": OBSERVED["openai-platform-bots"],
        },
        "capture_anchors": [{"kind": "verbatim_quote", "quote": robots_q}],
        "extraction": {
            "method": "deterministic_parser",
            "tool": "ai_discovery.claims",
            "rule_id": "openai_search_eligibility_v1",
            "version": "claim-extraction-0.1.0",
        },
        "status": "current",
        "relationship": "new",
    })

    # ------------------------------------------------------------------ Ahrefs
    a = SOURCES["ahrefs-blog-ai"]
    cite_q = (
        "although ChatGPT retrieves dozens of URLs to answer a single query, according to our "
        "research, it only ends up citing ~50% of them"
    )
    out.append({
        "source": a,
        "topic": "citations_sources",
        "statement": (
            "Ahrefs research found ChatGPT converts roughly half of the URLs it retrieves for a "
            "query into citations, retrieving dozens but citing about 50%."
        ),
        "surfaces": ["chatgpt"],
        "methodology": {
            "measurement_mode": "vendor_estimate",
            "metric_family": _qv("retrieved-to-cited conversion", cite_q),
            "metric_definition": _qv("share of retrieved URLs that become citations", cite_q),
            "unit_of_analysis": _qv("URLs retrieved per query", cite_q),
            "denominator": _qv("URLs retrieved", cite_q),
            "prompt_universe": None,
            "sample_size": None,
            "time_window": None,
            "geography": None,
            "geography_basis": "not_stated",
            "language": None,
            "language_basis": "not_stated",
            "devices": None,
            "limitations": ["Vendor research; exact prompt sample not shown in the capture."],
            "methodology_notes": _qv("Ahrefs research on ChatGPT citations.", cite_q),
        },
        "metrics": [
            _metric(
                "cited_share_of_retrieved",
                "~50% of retrieved URLs are cited",
                definition=_qv("retrieved URLs that become citations", cite_q),
                value=_qv("~50%", "~50% of them"),
                unit=_qv("percent of retrieved URLs", cite_q),
                window=_qv("Ahrefs study window", cite_q),
                scope=_qv("ChatGPT", cite_q),
                comparator="share_of_total",
            )
        ],
        "dates": {
            "published_at": PUBLISHED["ahrefs-blog-ai"],
            "modified_at": None,
            "measured_window": None,
            "observed_at": OBSERVED["ahrefs-blog-ai"],
        },
        "capture_anchors": [{"kind": "verbatim_quote", "quote": cite_q}],
        "extraction": {
            "method": "deterministic_parser",
            "tool": "ai_discovery.claims",
            "rule_id": "ahrefs_retrieved_to_cited_v1",
            "version": "claim-extraction-0.1.0",
        },
        "status": "current",
        "relationship": "new",
    })

    age_q = "The average cited page is 500 days old (and still getting picked)"
    out.append({
        "source": a,
        "topic": "citations_sources",
        "statement": (
            "Ahrefs found the average cited page in ChatGPT is about 500 days old, so recency "
            "is not the dominant citation factor."
        ),
        "surfaces": ["chatgpt"],
        "methodology": {
            "measurement_mode": "vendor_estimate",
            "metric_family": _qv("cited-page age", age_q),
            "metric_definition": _qv("average age of a cited page", age_q),
            "unit_of_analysis": _qv("cited page", age_q),
            "denominator": None,
            "prompt_universe": None,
            "sample_size": None,
            "time_window": None,
            "geography": None,
            "geography_basis": "not_stated",
            "language": None,
            "language_basis": "not_stated",
            "devices": None,
            "limitations": ["Vendor research; sample not shown in the capture."],
            "methodology_notes": _qv("Ahrefs research on ChatGPT citations.", age_q),
        },
        "metrics": [
            _metric(
                "avg_cited_page_age",
                "Average cited page ~500 days old",
                definition=_qv("age of a cited page", age_q),
                value=_qv("500", "500 days old"),
                unit=_qv("days", "days old"),
                window=_qv("Ahrefs study window", age_q),
                scope=_qv("ChatGPT cited pages", age_q),
                comparator="approx",
            )
        ],
        "dates": {
            "published_at": PUBLISHED["ahrefs-blog-ai"],
            "modified_at": None,
            "measured_window": None,
            "observed_at": OBSERVED["ahrefs-blog-ai"],
        },
        "capture_anchors": [{"kind": "verbatim_quote", "quote": age_q}],
        "extraction": {
            "method": "deterministic_parser",
            "tool": "ai_discovery.claims",
            "rule_id": "ahrefs_cited_page_age_v1",
            "version": "claim-extraction-0.1.0",
        },
        "status": "current",
        "relationship": "new",
    })

    fanout_q2 = (
        "when ChatGPT retrieves results, each one comes back with the page title, a brief "
        "snippet or summary, the URL, and an ID number"
    )
    out.append({
        "source": a,
        "topic": "retrieval_index",
        "statement": (
            "Ahrefs reports that ChatGPT's retrieval results carry a title, snippet, URL and ID, "
            "and it uses these to decide which pages to open and cite before reading full content."
        ),
        "surfaces": ["chatgpt"],
        "methodology": {
            "measurement_mode": "vendor_estimate",
            "metric_family": _qv("retrieval candidate fields", fanout_q2),
            "metric_definition": _qv(
                "fields returned per retrieved result", fanout_q2
            ),
            "unit_of_analysis": _qv("retrieved result", fanout_q2),
            "denominator": None,
            "prompt_universe": None,
            "sample_size": None,
            "time_window": None,
            "geography": None,
            "geography_basis": "not_stated",
            "language": None,
            "language_basis": "not_stated",
            "devices": None,
            "limitations": ["Vendor research; describes a pre-open gatekeeping layer."],
            "methodology_notes": _qv("Ahrefs research on ChatGPT citations.", fanout_q2),
        },
        "metrics": [
            _metric(
                "retrieval_candidate_fields",
                "Retrieval results carry title/snippet/URL/ID",
                definition=_qv("per-result fields", fanout_q2),
                value=_qv("title, snippet, URL, ID", fanout_q2),
                unit=_qv("fields", fanout_q2),
                window=_qv("Ahrefs study window", fanout_q2),
                scope=_qv("ChatGPT retrieval", fanout_q2),
            )
        ],
        "dates": {
            "published_at": PUBLISHED["ahrefs-blog-ai"],
            "modified_at": None,
            "measured_window": None,
            "observed_at": OBSERVED["ahrefs-blog-ai"],
        },
        "capture_anchors": [{"kind": "verbatim_quote", "quote": fanout_q2}],
        "extraction": {
            "method": "deterministic_parser",
            "tool": "ai_discovery.claims",
            "rule_id": "ahrefs_retrieval_fields_v1",
            "version": "claim-extraction-0.1.0",
        },
        "status": "current",
        "relationship": "new",
    })

    # --------------------------------------------------------------- Perplexity
    pp = SOURCES["perplexity-blog"]
    q2d_q = (
        "Q2D-Web: Evaluating First-Stage Retrievers at Scale"
    )
    out.append({
        "source": pp,
        "topic": "retrieval_index",
        "statement": (
            "Perplexity Research publishes Q2D-Web, a first-stage retriever benchmark built "
            "on agent queries and web documents, indicating its search stack is evaluated at "
            "the retrieval stage."
        ),
        "surfaces": ["perplexity"],
        "methodology": {
            "measurement_mode": "official_documentation",
            "metric_family": _qv("first-stage retriever benchmark", q2d_q),
            "metric_definition": _qv("Evaluating First-Stage Retrievers at Scale", q2d_q),
            "unit_of_analysis": _qv("web document retrieval", q2d_q),
            "denominator": None,
            "prompt_universe": None,
            "sample_size": None,
            "time_window": None,
            "geography": None,
            "geography_basis": "not_stated",
            "language": None,
            "language_basis": "not_stated",
            "devices": None,
            "limitations": ["Vendor research publication; describes evaluation, not production behaviour."],
            "methodology_notes": _qv("Perplexity Research blog index.", q2d_q),
        },
        "metrics": [
            _metric(
                "first_stage_retriever_benchmark",
                "Perplexity benchmarks first-stage retrieval",
                definition=_qv("first-stage retriever", "First-Stage Retrievers"),
                value=_qv("published benchmark Q2D-Web", q2d_q),
                unit=_qv("benchmark", q2d_q),
                window=_qv("Sep 2026", q2d_q),
                scope=_qv("Perplexity", "Perplexity Research"),
            )
        ],
        "dates": {
            "published_at": None,
            "modified_at": None,
            "measured_window": None,
            "observed_at": OBSERVED.get("perplexity-blog", "2026-09-16T21:55:00+00:00"),
        },
        "capture_anchors": [{"kind": "verbatim_quote", "quote": q2d_q}],
        "extraction": {
            "method": "deterministic_parser",
            "tool": "ai_discovery.claims",
            "rule_id": "perplexity_first_stage_retriever_v1",
            "version": "claim-extraction-0.1.0",
        },
        "status": "current",
        "relationship": "new",
    })

    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--persist", action="store_true", help="persist validated claims to the DB")
    args = ap.parse_args()

    from ai_discovery.claims import Capture, extract_capture_text, extract_claim

    bundle = {"extraction_version": "claim-extraction-0.1.0", "claims": specs()}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(bundle['claims'])} mechanics claim specs -> {OUT.relative_to(REPO)}")

    # Verify each spec extracts (quotes present) against its real capture.
    captures: dict[str, Capture] = {}
    for name in {c["source"]["source_id"] for c in bundle["claims"]}:
        path = CAPTURES / f"{name}.html"
        raw = path.read_bytes()
        captures[name] = Capture(raw=raw, text=extract_capture_text(raw.decode("utf-8", errors="replace")))
    records = []
    for spec in bundle["claims"]:
        record = extract_claim(spec=spec, capture=captures[spec["source"]["source_id"]])
        records.append(record)
        print(f"  OK {record.claim_id} [{record.topic}] {spec['statement'][:60]}")

    if args.persist:
        from sqlalchemy import create_engine

        from ai_discovery.claims import persist_claim
        from ai_discovery.settings import get_settings

        engine = create_engine(os.environ.get("AI_DISCOVERY_DATABASE_URL", get_settings().database_url))
        for record in records:
            cid, created = persist_claim(engine, record)
            print(f"  persisted {cid} created={created}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
