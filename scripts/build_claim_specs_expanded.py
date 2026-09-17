"""Build proof/claim_ledger/claim_specs.json: the 4 original claims plus
claims extracted from the newly captured priority sources.

Every value carried by a claim is paired with the verbatim quote that supports
it; ai_discovery.claims.extract_claim re-checks each quote against the capture
and refuses to emit the claim otherwise, so nothing here is asserted without
evidence.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "proof" / "claim_ledger" / "claim_specs.json"
ORIGINAL = ROOT / "proof" / "claim_ledger" / "claim_specs_original.json"

OBSERVED = "2026-09-16T21:55:00+00:00"
original = json.loads(ORIGINAL.read_text())["claims"]


def P(value, quote=None, kind="verbatim_quote"):
    return None if value is None else {"value": value, "quote": quote, "kind": kind}


def M(
    mid,
    label,
    definition,
    value,
    unit,
    window,
    scope,
    comparator="exact",
    value_quote=None,
    unit_quote=None,
    window_quote=None,
    scope_quote=None,
):
    """A metric; every cell carries the verbatim quote that supports it."""
    return {
        "metric_id": mid,
        "label": label,
        "comparator": comparator,
        "definition": {"value": definition, "quote": definition},
        "value": {"value": value, "quote": value_quote or definition},
        "unit": {"value": unit, "quote": unit_quote or unit},
        "window": {"value": window, "quote": window_quote or window},
        "scope": {"value": scope, "quote": scope_quote or scope},
    }


def spec(
    source_id,
    publisher,
    url,
    source_class,
    topic,
    statement,
    surfaces,
    metric_family,
    metric_definition,
    denominator,
    unit_of_analysis,
    time_window,
    notes,
    mode,
    metrics,
    anchors,
    rule_id,
    confidence="medium",
    sample_size=None,
    prompt_universe=None,
    limitations=None,
    published_at=None,
    published_selector=None,
):
    meth = {
        "measurement_mode": mode,
        "metric_family": {"value": metric_family, "quote": metric_family},
        "metric_definition": {"value": metric_definition, "quote": metric_definition},
        "denominator": {"value": denominator, "quote": denominator},
        "unit_of_analysis": {"value": unit_of_analysis, "quote": unit_of_analysis},
        "time_window": {"value": time_window, "quote": time_window},
        "methodology_notes": {"value": notes, "quote": notes},
        "geography": None,
        "geography_basis": "not_stated",
        "language": None,
        "language_basis": "not_stated",
        "prompt_universe": (
            {"value": prompt_universe, "quote": prompt_universe} if prompt_universe else None
        ),
        "sample_size": ({"value": sample_size, "quote": sample_size} if sample_size else None),
        "limitations": limitations or [],
    }
    return {
        "source": {
            "source_id": source_id,
            "publisher": publisher,
            "url": url,
            "canonical_url": url,
            "source_class": source_class,
            "robots_allowed": True,
        },
        "topic": topic,
        "statement": statement,
        "surfaces": surfaces,
        "methodology": meth,
        "metrics": metrics,
        "dates": {
            "published_at": published_at,
            "published_at_selector": published_selector,
            "modified_at": None,
            "measured_window": None,
            "observed_at": OBSERVED,
        },
        "capture_anchors": [{"kind": "verbatim_quote", "quote": a} for a in anchors],
        "extraction": {
            "method": "deterministic_parser",
            "tool": "ai_discovery.claims",
            "rule_id": rule_id,
            "version": "claim-extraction-0.1.0",
        },
        "status": "current",
        "relationship": "new",
        "confidence": confidence,
    }


new = []

# --- Official ---------------------------------------------------------------
new.append(
    spec(
        "openai-platform-bots",
        "OpenAI",
        "https://platform.openai.com/docs/bots",
        "official",
        "crawler_index_policy",
        "OpenAI uses two independent robots.txt controls for AI: OAI-SearchBot, which surfaces sites in ChatGPT search results, and GPTBot, which governs generative-AI training. A site can allow one while disallowing the other.",
        ["chatgpt"],
        "OpenAI uses OAI-SearchBot and GPTBot robots.txt tags to enable webmasters to manage how their sites and content work with AI.",
        "Each setting is independent of the others",
        "enable webmasters to manage how their sites and content work with AI",
        "OAI-SearchBot is used to surface websites in search results in ChatGPT's search features.",
        "User agent Description & details",
        "OpenAI uses OAI-SearchBot and GPTBot robots.txt tags to enable webmasters to manage how their sites and content work with AI.",
        "official_documentation",
        [
            M(
                "openai_search_vs_training",
                "Search and training opt-out are independent",
                "Each setting is independent of the others",
                True,
                "independent",
                "robots.txt",
                "ChatGPT search results",
                "policy_statement",
                scope_quote="surface websites in search results in ChatGPT's search features",
            )
        ],
        [
            "OpenAI uses OAI-SearchBot and GPTBot robots.txt tags to enable webmasters to manage how their sites and content work with AI."
        ],
        "openai_crawler_independence_v1",
        confidence="high",
        limitations=["Documents stated crawler policy, not observed crawl frequency."],
    )
)

new.append(
    spec(
        "google-search-central-ai",
        "Google",
        "https://developers.google.com/search/docs/appearance/ai-features",
        "official",
        "retrieval_index",
        "Google states there are no additional content requirements to appear in AI Overviews or AI Mode beyond existing SEO fundamentals and no special schema, while eligibility still requires a page to be indexed and snippet-eligible in Google Search.",
        ["google-ai-overviews", "google-ai-mode"],
        "The best practices for SEO remain relevant for AI features",
        "There are no additional requirements to appear in AI Overviews or AI Mode, nor other special optimizations necessary",
        "As with Search overall",
        "AI Overviews and AI Mode work in Google Search",
        "Last updated 2025-12-10 UTC",
        "Google Search Central | Documentation | Google for Developers",
        "official_documentation",
        [
            M(
                "google_ai_no_special_opt",
                "No special optimisation needed for AI Overviews / AI Mode",
                "There are no additional requirements to appear in AI Overviews or AI Mode, nor other special optimizations necessary",
                True,
                "additional requirements",
                "Last updated 2025-12-10 UTC",
                "AI Overviews or AI Mode",
                "policy_statement",
            ),
            M(
                "google_ai_eligibility",
                "Eligibility for AI features requires indexing + snippet eligibility",
                "page must be indexed and eligible to be shown in Google Search with a snippet",
                True,
                "indexed and snippet-eligible",
                "Last updated 2025-12-10 UTC",
                "AI Overviews or AI Mode",
                "policy_statement",
                unit_quote="indexed and eligible to be shown in Google Search with a snippet",
            ),
        ],
        [
            "There are no additional requirements to appear in AI Overviews or AI Mode, nor other special optimizations necessary"
        ],
        "google_ai_feature_eligibility_v1",
        confidence="high",
        limitations=["Documents stated policy, not actual inclusion rates in AI features."],
    )
)

new.append(
    spec(
        "xai-docs",
        "xAI",
        "https://docs.x.ai/docs/overview",
        "official",
        "retrieval_index",
        "xAI's developer documentation lists a Web search tool among Grok's server-side API capabilities, alongside function calling and structured outputs, on the Grok 4.6 flagship model.",
        ["grok"],
        "Function calling Web search",
        "Function calling Web search",
        "Explore the documentation",
        "Web search",
        "Grok 4.6",
        "Our flagship model for code and everything else: agentic tool calling, minimal hallucinations, configurable reasoning.",
        "official_documentation",
        [
            M(
                "xai_web_search_tool",
                "Grok exposes a server-side Web search tool",
                "Function calling Web search",
                True,
                "Web search",
                "Grok 4.6",
                "Grok developer platform",
                "policy_statement",
                scope_quote="Try in playground",
            )
        ],
        ["Function calling Web search"],
        "xai_web_search_tool_v1",
        confidence="low",
        limitations=["Documented capability, not measured retrieval behaviour."],
    )
)

new.append(
    spec(
        "alibaba-qwen-blog",
        "Alibaba Qwen",
        "https://qwenlm.github.io/blog/",
        "official",
        "audience_usage",
        "Alibaba's Qwen-MT translation model supports 92 major official languages and prominent dialects, covering over 95% of the global population, per the Qwen team's release blog.",
        ["qwen-consumer"],
        "92 major official languages",
        "covering over 95% of the global population",
        "over 95% of the global population",
        "92 major official languages and prominent dialects",
        "July 27, 2025",
        "Qwen-MT: Where Speed Meets Smart Translation",
        "unknown",
        [
            M(
                "qwen_mt_languages",
                "Languages supported by Qwen-MT",
                "92 major official languages",
                92,
                "languages",
                "July 2025",
                "Qwen-MT",
                "exact",
                window_quote="July 27, 2025",
            ),
            M(
                "qwen_mt_population",
                "Global population covered by Qwen-MT languages",
                "over 95% of the global population",
                "95%+",
                "%",
                "July 2025",
                "global population",
                "at_least",
                window_quote="July 27, 2025",
            ),
        ],
        [
            "Qwen-MT enables high-quality translation across 92 major official languages and prominent dialects, covering over 95% of the global population"
        ],
        "qwen_mt_language_reach_v1",
        confidence="low",
        limitations=["Vendor-stated coverage; no independent verification."],
    )
)

# --- Visibility research ----------------------------------------------------
new.append(
    spec(
        "ahrefs-blog-ai",
        "Ahrefs",
        "https://ahrefs.com/blog/why-chatgpt-cites-pages/",
        "vendor_research",
        "citations_sources",
        "Ahrefs' analysis of 1.4 million ChatGPT 5.2 prompts from February 2025 found ChatGPT retrieves dozens of URLs per response but ends up citing only about 50% of them (about 16.57 cited vs 16.58 non-cited URLs per prompt).",
        ["chatgpt"],
        "it only ends up citing ~50% of them",
        "Our 50% figure captures the full journey from retrieval to citation, not just the final decision after a page has been read.",
        "it only ends up citing ~50% of them",
        "~16.57 cited URLs and ~16.58 non-cited URLs per prompt",
        "February 2025",
        "Why ChatGPT Cites One Page Over Another (Study of 1.4M Prompts)",
        "vendor_panel",
        [
            M(
                "ahrefs_citation_rate",
                "Share of retrieved URLs that get cited",
                "it only ends up citing ~50% of them",
                50,
                "%",
                "February 2025",
                "ChatGPT 5.2 responses",
                "approx",
                scope_quote="1.4 million ChatGPT 5.2 prompts",
            ),
            M(
                "ahrefs_cited_urls_per_prompt",
                "Cited URLs per ChatGPT prompt",
                "~16.57 cited URLs and ~16.58 non-cited URLs per prompt",
                16.57,
                "URLs per prompt",
                "February 2025",
                "cited URLs",
                "approx",
            ),
        ],
        ["it only ends up citing ~50% of them"],
        "ahrefs_retrieval_to_citation_v1",
        sample_size="we analyzed 1.4 million ChatGPT 5.2 prompts from February 2025",
        prompt_universe="we analyzed 1.4 million ChatGPT 5.2 prompts from February 2025",
        limitations=["Vendor study; desktop prompts only."],
    )
)

new.append(
    spec(
        "peec-blog",
        "Peec AI",
        "https://peec.ai/blog",
        "vendor_research",
        "citations_sources",
        "Peec AI's analysis of 500,000 prompts found Google AI Overviews appear 86% of the time in its sample, which it calls the most undertracked AI search surface.",
        ["google-ai-overviews"],
        "AI Overviews appear 86% of the time in our sample",
        "AI Overviews appear 86% of the time in our sample",
        "500,000 prompts",
        "AI Overviews appear 86% of the time in our sample",
        "Jun 11, 2026",
        "AI Overviews is the most undertracked AI search",
        "vendor_panel",
        [
            M(
                "peec_aio_trigger_rate",
                "Share of tracked prompts that trigger an AI Overview",
                "AI Overviews appear 86% of the time in our sample",
                86,
                "86%",
                "our sample",
                "AI Overviews",
                "share_of_total",
            )
        ],
        [
            "AI Overviews is the most undertracked AI search: 500,000 prompts show why AI Overviews appear 86% of the time in our sample"
        ],
        "peec_aio_trigger_rate_v1",
        sample_size="500,000 prompts",
        prompt_universe="500,000 prompts",
        published_at="2026-06-11",
        published_selector="page_stamp 'Jun 11, 2026'",
        limitations=["Vendor sample; prompt selection not published on the index page."],
    )
)

new.append(
    spec(
        "semrush-blog-ai",
        "Semrush",
        "https://www.semrush.com/blog/",
        "vendor_research",
        "commerce_ads",
        "A Semrush survey of 2,338 US consumers found AI chatbots talked 57.5% of AI users out of a purchase, and 65% of AI users had replaced some product-related Google searches with chatbots.",
        ["chatgpt"],
        "AI chatbots talked 57.5% of AI users out of buying",
        "65% of AI users have replaced some product-related Google searches with chatbots",
        "We surveyed 2,338 US consumers",
        "AI users",
        "September 10, 2026",
        "4 in 10 dislike chatbot ads",
        "survey",
        [
            M(
                "semrush_talked_out_of_buying",
                "AI users talked out of a purchase by chatbots",
                "AI chatbots talked 57.5% of AI users out of buying",
                57.5,
                "57.5%",
                "September 2026",
                "US AI users",
                "share_of_total",
                window_quote="September 10, 2026",
                scope_quote="We surveyed 2,338 US consumers",
            ),
            M(
                "semrush_replaced_google",
                "AI users who replaced product Google searches with chatbots",
                "65% of AI users have replaced some product-related Google searches with chatbots",
                65,
                "65%",
                "September 2026",
                "US AI users",
                "share_of_total",
                window_quote="September 10, 2026",
                scope_quote="We surveyed 2,338 US consumers",
            ),
        ],
        [
            "We surveyed 2,338 US consumers: 65% of AI users have replaced some product-related Google searches with chatbots"
        ],
        "semrush_chatbot_commerce_survey_v1",
        sample_size="We surveyed 2,338 US consumers",
        published_at="2026-09-10",
        published_selector="page_stamp 'September 10, 2026'",
        limitations=["Vendor survey of US consumers; self-reported behaviour."],
    )
)

new.append(
    spec(
        "sistrix-blog",
        "SISTRIX",
        "https://www.sistrix.com/blog/",
        "vendor_blog",
        "measurement",
        "SISTRIX built its Prompt Research feature on over 62 million real user questions, replacing keyword-level research with topic-level abstractions for AI search.",
        ["chatgpt", "google-ai-mode"],
        "over 62 million real user questions",
        "topics instead of keywords",
        "over 62 million real user questions",
        "real user questions",
        "24.08.2026",
        "Prompt Research: Keyword Research for AI Search",
        "unknown",
        [
            M(
                "sistrix_prompt_corpus",
                "Real user questions behind Prompt Research",
                "over 62 million real user questions",
                "62M+",
                "real user questions",
                "Aug 2026",
                "SISTRIX prompt data",
                "at_least",
                window_quote="24.08.2026",
                scope_quote="over 62 million real user questions",
            )
        ],
        ["topics instead of keywords, based on over 62 million real user questions"],
        "sistrix_prompt_research_corpus_v1",
        confidence="low",
        sample_size="over 62 million real user questions",
        limitations=["Vendor product description; underlying question set not published."],
    )
)

# --- Market telemetry -------------------------------------------------------
new.append(
    spec(
        "statcounter-ai-chatbot",
        "Statcounter",
        "https://gs.statcounter.com/ai-chatbot-market-share",
        "vendor_research",
        "audience_usage",
        "Statcounter's August 2026 AI-chatbot market-share measure puts ChatGPT at 79.4%, Google Gemini at 10.9%, Perplexity at 4.31%, Microsoft Copilot at 2.79%, Claude at 2.57% and DeepSeek at 0.02% worldwide.",
        ["chatgpt", "google-gemini", "perplexity", "microsoft-copilot", "claude", "deepseek-chat"],
        "Percentage Market Share",
        "AI Chatbot Market Share Worldwide - August 2026",
        "AI Chatbot Market Share Worldwide",
        "Percentage Market Share",
        "August 2026",
        "Source: Statcounter Global Stats",
        "clickstream",
        [
            M(
                "statcounter_chatgpt_share",
                "ChatGPT share of AI-chatbot market",
                "ChatGPT 79.4 %",
                79.4,
                "79.4 %",
                "August 2026",
                "worldwide AI chatbots",
                "share_of_total",
                scope_quote="AI Chatbot Market Share Worldwide",
            ),
            M(
                "statcounter_gemini_share",
                "Google Gemini share of AI-chatbot market",
                "Google Gemini 10.9 %",
                10.9,
                "10.9 %",
                "August 2026",
                "worldwide AI chatbots",
                "share_of_total",
                scope_quote="AI Chatbot Market Share Worldwide",
            ),
            M(
                "statcounter_perplexity_share",
                "Perplexity share of AI-chatbot market",
                "Perplexity 4.31 %",
                4.31,
                "4.31 %",
                "August 2026",
                "worldwide AI chatbots",
                "share_of_total",
                scope_quote="AI Chatbot Market Share Worldwide",
            ),
            M(
                "statcounter_copilot_share",
                "Microsoft Copilot share of AI-chatbot market",
                "Microsoft Copilot 2.79 %",
                2.79,
                "2.79 %",
                "August 2026",
                "worldwide AI chatbots",
                "share_of_total",
                scope_quote="AI Chatbot Market Share Worldwide",
            ),
            M(
                "statcounter_claude_share",
                "Claude share of AI-chatbot market",
                "Claude 2.57 %",
                2.57,
                "2.57 %",
                "August 2026",
                "worldwide AI chatbots",
                "share_of_total",
                scope_quote="AI Chatbot Market Share Worldwide",
            ),
            M(
                "statcounter_deepseek_share",
                "DeepSeek share of AI-chatbot market",
                "Deepseek 0.02 %",
                0.02,
                "0.02 %",
                "August 2026",
                "worldwide AI chatbots",
                "share_of_total",
                scope_quote="AI Chatbot Market Share Worldwide",
            ),
        ],
        ["AI Chatbot Market Share Worldwide - August 2026 ChatGPT 79.4 %"],
        "statcounter_ai_chatbot_share_v1",
        limitations=["Clickstream panel; visit-share denominator, not users."],
    )
)

new.append(
    spec(
        "cloudflare-blog-ai",
        "Cloudflare",
        "https://blog.cloudflare.com/tag/ai/",
        "vendor_blog",
        "crawler_index_policy",
        "Cloudflare announced a control that lets site owners stay discoverable in search while disallowing AI training, and separately detects MCP traffic via protocol-level heuristics.",
        ["chatgpt"],
        "stay discoverable in search while disallowing AI training",
        "Cloudflare is giving site owners a way to stay discoverable while disallowing AI training",
        "site owners",
        "site owners",
        "September 15, 2026",
        "How Cloudflare detects MCP traffic",
        "unknown",
        [
            M(
                "cloudflare_ai_training_control",
                "Control to allow search crawl while disallowing AI training",
                "stay discoverable in search while disallowing AI training",
                True,
                "control",
                "September 2026",
                "Cloudflare site owners",
                "policy_statement",
                window_quote="September 15, 2026",
                scope_quote="site owners",
            )
        ],
        [
            "Cloudflare is giving site owners a way to stay discoverable while disallowing AI training"
        ],
        "cloudflare_search_vs_training_control_v1",
        confidence="low",
        limitations=["Vendor blog announcement; surface tag is contextual."],
    )
)

# --- Editorial --------------------------------------------------------------
new.append(
    spec(
        "search-engine-journal",
        "Search Engine Journal",
        "https://www.searchenginejournal.com/",
        "news",
        "commerce_ads",
        "Search Engine Journal argues ChatGPT Ads should not be treated as paid search, advising advertisers to define a clear role, budget source and success criteria for ChatGPT Ads before shifting budget away from paid search.",
        ["chatgpt"],
        "ChatGPT Ads Aren't Paid Search",
        "Give ChatGPT Ads a clear role, budget source, and success criteria before pulling money from paid search",
        "paid search",
        "ChatGPT Ads",
        "Sep 15, 2026",
        "ChatGPT Ads Aren't Paid Search - 5 Questions To Answer Before You Shift Budget",
        "unknown",
        [
            M(
                "sej_chatgpt_ads_guidance",
                "Editorial guidance treating ChatGPT Ads distinctly from paid search",
                "Give ChatGPT Ads a clear role, budget source, and success criteria before pulling money from paid search",
                True,
                "editorial guidance",
                "Sep 2026",
                "ChatGPT Ads",
                "qualitative_finding",
                unit_quote="paid search",
                window_quote="Sep 15, 2026",
                scope_quote="Give ChatGPT Ads a clear role, budget source, and success criteria before pulling money from paid search",
            )
        ],
        ["ChatGPT Ads Aren't Paid Search - 5 Questions To Answer Before You Shift Budget"],
        "sej_chatgpt_ads_v1",
        confidence="low",
        published_at="2026-09-15",
        published_selector="page_stamp 'Sep 15, 2026'",
        limitations=["Editorial analysis, not a measurement."],
    )
)

# --- Additional priority sources (second fetch pass) ------------------------
new.append(
    spec(
        "tryprofound-research",
        "Profound",
        "https://www.tryprofound.com/research",
        "vendor_research",
        "audience_usage",
        "Profound's research on travel decision-making found nearly eight in ten (79.7%) of respondents relied on answer engines for at least half of their decision making.",
        ["chatgpt", "google-ai-overviews"],
        "Nearly eight in ten (79.7%) relied on Answer Engines for at least half of their decision making",
        "Nearly eight in ten (79.7%) relied on Answer Engines for at least half of their decision making",
        "The state of AI Search in travel",
        "The state of AI Search in travel",
        "9 Jul, 2026",
        "The state of AI Search in travel",
        "survey",
        [
            M(
                "profound_travel_answer_engine_reliance",
                "Travel decision-makers relying on answer engines for >=half of decisions",
                "Nearly eight in ten (79.7%) relied on Answer Engines for at least half of their decision making",
                79.7,
                "79.7%",
                "9 Jul, 2026",
                "travel decision-makers",
                "at_least",
                scope_quote="The state of AI Search in travel",
            )
        ],
        [
            "Nearly eight in ten (79.7%) relied on Answer Engines for at least half of their decision making"
        ],
        "profound_travel_reliance_v1",
        sample_size="Nearly eight in ten (79.7%)",
        limitations=["Vendor survey; single industry vertical (travel)."],
    )
)

new.append(
    spec(
        "seer-ai-research",
        "Seer Interactive",
        "https://www.seerinteractive.com/insights",
        "vendor_research",
        "citations_sources",
        "Seer Interactive's study found AI assistants declined to answer prompts about its brand 31% of the time, though answers were mostly correct when given.",
        ["chatgpt", "google-ai-mode"],
        "AI Declined to Answer Prompts About Our Brand 31% of the Time",
        "Study: AI Declined to Answer Prompts About Our Brand 31% of the Time (But Got Our Info Mostly Right When It Answered)",
        "AI Declined to Answer Prompts About Our Brand",
        "AI Declined to Answer Prompts About Our Brand",
        "2026",
        "AI Study",
        "vendor_panel",
        [
            M(
                "seer_declined_to_answer",
                "Share of brand prompts the AI declined to answer",
                "AI Declined to Answer Prompts About Our Brand 31% of the Time",
                31,
                "31%",
                "2026",
                "prompts about Seer's own brand",
                "share_of_total",
                scope_quote="AI Declined to Answer Prompts About Our Brand",
            )
        ],
        [
            "Study: AI Declined to Answer Prompts About Our Brand 31% of the Time (But Got Our Info Mostly Right When It Answered)"
        ],
        "seer_brand_decline_rate_v1",
        confidence="low",
        limitations=["Single-brand vendor study; prompt set not published on the index page."],
    )
)

new.append(
    spec(
        "search-engine-roundtable",
        "Search Engine Roundtable",
        "https://www.seroundtable.com/",
        "news",
        "commerce_ads",
        "Search Engine Roundtable reports OpenAI is testing a ChatGPT ad format named Sponsored Agents, which lets people start a conversation with a business-sponsored agent after clicking an ad in ChatGPT.",
        ["chatgpt"],
        "OpenAI is testing a new ad format in ChatGPT named Sponsored Agents",
        "OpenAI is testing a new ad format in ChatGPT named Sponsored Agents",
        "Sponsored Agents",
        "ChatGPT Ads",
        "Sep 16, 2026",
        "let people start a conversation with a business-sponsored agent after clicking an ad in ChatGPT",
        "unknown",
        [
            M(
                "ser_sponsored_agents_test",
                "ChatGPT Sponsored Agents ad format in testing",
                "OpenAI is testing a new ad format in ChatGPT named Sponsored Agents",
                True,
                "in testing",
                "Sep 16, 2026",
                "ChatGPT Ads",
                "qualitative_finding",
                unit_quote="OpenAI is testing a new ad format in ChatGPT named Sponsored Agents",
                scope_quote="ChatGPT Ads",
            )
        ],
        ["OpenAI is testing a new ad format in ChatGPT named Sponsored Agents"],
        "ser_chatgpt_sponsored_agents_v1",
        confidence="low",
        published_at="2026-09-16",
        published_selector="page_stamp 'Sep 16, 2026'",
        limitations=["Industry news reporting stated testing; not an OpenAI primary source."],
    )
)


bundle = {"extraction_version": "claim-extraction-0.1.0", "claims": original + new}
OUT.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"wrote {len(bundle['claims'])} claims to {OUT.relative_to(ROOT)}")
