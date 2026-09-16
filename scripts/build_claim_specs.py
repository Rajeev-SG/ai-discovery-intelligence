#!/usr/bin/env python3
"""Write the claim-extraction rule bundle to proof/claim_ledger/claim_specs.json.

Every value in the bundle names the exact source quote (or structured selector)
that supports it. Nothing here is inferred; fields the sources do not publish are
left null so they land in the ledger as unknown.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "proof" / "claim_ledger" / "claim_specs.json"

SIM = {
    "source": {
        "source_id": "similarweb-most-visited-websites",
        "publisher": "Similarweb",
        "url": "https://www.similarweb.com/blog/research/market-research/most-visited-websites/",
        "canonical_url": "https://www.similarweb.com/blog/research/market-research/most-visited-websites/",
        "source_class": "vendor_research",
        "robots_allowed": True,
    },
    "topic": "audience_usage",
    "statement": (
        "Similarweb estimates ChatGPT at ~52.7% of all AI-chatbot web traffic in the month "
        "before the May 2026 update, down from 76.4% twelve months earlier, with Gemini at "
        "27.3% and Claude at 8.9%."
    ),
    "surfaces": ["chatgpt", "gemini", "claude", "deepseek-chat"],
    "methodology": {
        "measurement_mode": "vendor_estimate",
        "metric_family": {
            "value": "share of measured AI-chatbot web traffic",
            "quote": "falling from 76.4% of all AI chatbot web traffic",
        },
        "metric_definition": {
            "value": "share of estimated monthly visits attributable to each AI chatbot",
            "quote": "ChatGPT's web traffic share fell from 76.4% one year ago to around 52.7% one month ago.",
        },
        "denominator": {
            "value": "all AI chatbot web traffic (visits), worldwide",
            "quote": "falling from 76.4% of all AI chatbot web traffic 12 months ago to around 52.7% one month ago",
        },
        "prompt_universe": None,
        "sample_size": None,
        "unit_of_analysis": {
            "value": "domain-level monthly visits (estimated)",
            "quote": "# Domain Monthly Visits MoM traffic change Yearly Change",
        },
        "time_window": {
            "value": "~Apr 2026 (the month before the 14 May 2026 update)",
            "quote": "around 52.7% one month ago",
        },
        "geography": None,
        "geography_basis": "not_stated",
        "language": None,
        "language_basis": "not_stated",
        "devices": {
            "value": "desktop and mobile web",
            "quote": "Our methodology covers both desktop and mobile web.",
        },
        "limitations": [
            "Estimates, rounded, and modelled - not a measured census.",
            "Visit-share denominator, not users/MAU; not comparable to panel market-share trackers.",
        ],
        "methodology_notes": {
            "value": (
                "Similarweb combines opt-in device/panel measurement, ISP data, public data "
                "sources, and machine-learning models."
            ),
            "quote": (
                "Similarweb estimates monthly visits using a combination of direct measurement "
                "from opt-in devices and panels, ISP data, public data sources, and machine "
                "learning models."
            ),
        },
    },
    "metrics": [
        {
            "metric_id": "chatgpt_share",
            "label": "ChatGPT share of AI-chatbot web traffic",
            "definition": {
                "value": "ChatGPT's share of all AI-chatbot web traffic",
                "quote": "falling from 76.4% of all AI chatbot web traffic",
            },
            "value": {"value": 52.7, "quote": "around 52.7% one month ago"},
            "unit": {"value": "%", "quote": "52.7%"},
            "comparator": "share_of_total",
            "window": {"value": "~Apr 2026", "quote": "one month ago"},
            "scope": {"value": "worldwide, all AI chatbots", "quote": "all AI chatbot web traffic"},
        },
        {
            "metric_id": "chatgpt_prior_share",
            "label": "ChatGPT share twelve months earlier",
            "definition": {
                "value": "ChatGPT's share of all AI-chatbot web traffic one year before",
                "quote": "falling from 76.4% of all AI chatbot web traffic 12 months ago",
            },
            "value": {"value": 76.4, "quote": "76.4% of all AI chatbot web traffic 12 months ago"},
            "unit": {"value": "%", "quote": "76.4%"},
            "comparator": "share_of_total",
            "window": {
                "value": "~Apr 2025 (12 months before measurement)",
                "quote": "12 months ago",
            },
            "scope": {"value": "worldwide, all AI chatbots", "quote": "all AI chatbot web traffic"},
        },
        {
            "metric_id": "gemini_share",
            "label": "Gemini share of AI-chatbot web traffic",
            "definition": {
                "value": "Gemini's share of AI-chatbot web traffic",
                "quote": "Gemini has taken the largest share of that ground, rising from roughly 9% to 27.3%",
            },
            "value": {
                "value": 27.3,
                "quote": "rising from roughly 9% to 27.3% over the same period",
            },
            "unit": {"value": "%", "quote": "27.3%"},
            "comparator": "share_of_total",
            "window": {"value": "~Apr 2026", "quote": "over the same period"},
            "scope": {"value": "worldwide, AI chatbots", "quote": "the same period"},
        },
        {
            "metric_id": "deepseek_visits",
            "label": "DeepSeek chat visits",
            "definition": {
                "value": "Estimated monthly visits to chat.deepseek.com",
                "quote": "chat.deepseek.com 375.1M",
            },
            "value": {"value": "375.1M", "quote": "chat.deepseek.com 375.1M"},
            "unit": {"value": "visits", "quote": "Monthly Visits"},
            "comparator": "approx",
            "window": {"value": "May 2026", "quote": "monthly visits in May 2026"},
            "scope": {"value": "worldwide (rank #82)", "quote": "chat.deepseek.com 375.1M"},
        },
    ],
    "dates": {
        "published_at": "2026-05-14",
        "published_at_selector": "datePublished",
        "modified_at": "2026-06-11",
        "modified_at_selector": "dateModified",
        "measured_window": {"value": "~Apr 2026", "quote": "one month ago"},
        "observed_at": "2026-09-16T12:00:00+00:00",
    },
    "capture_anchors": [
        {
            "kind": "jsonld_field",
            "selector": "datePublished=2026-05-14T01:54:23+00:00 / dateModified=2026-06-11T12:07:19+00:00",
        },
        {
            "kind": "verbatim_quote",
            "quote": "falling from 76.4% of all AI chatbot web traffic 12 months ago to around 52.7% one month ago",
        },
    ],
    "extraction": {
        "method": "deterministic_parser",
        "tool": "ai_discovery.claims",
        "rule_id": "similarweb_visit_share_v1",
    },
    "status": "current",
    "relationship": "new",
    "confidence": "medium",
}

SIS = {
    "source": {
        "source_id": "sistrix-ai-citation-drift",
        "publisher": "SISTRIX",
        "url": "https://www.sistrix.com/blog/ai-citation-drift-how-stable-are-sources-in-ai-search-results/",
        "canonical_url": "https://www.sistrix.com/blog/ai-citation-drift-how-stable-are-sources-in-ai-search-results/",
        "source_class": "vendor_research",
        "robots_allowed": True,
    },
    "topic": "citations_sources",
    "statement": (
        "SISTRIX's 17-week, six-country study of 82,619 prompts found ChatGPT replaces ~74% of "
        "its cited sources week to week and Google AI Mode ~56%, with Google AI Mode churn a "
        "consistent 54-59% across all six countries."
    ),
    "surfaces": ["chatgpt", "google-ai-mode"],
    "methodology": {
        "measurement_mode": "vendor_panel",
        "metric_family": {
            "value": "weekly source/citation churn",
            "quote": "Citation drift is global and persistent",
        },
        "metric_definition": {
            "value": "share of cited sources replaced from one week to the next",
            "quote": "Google replaces 56% of sources in AI-generated responses every week",
        },
        "denominator": {
            "value": "cited sources in AI-generated responses, week over week",
            "quote": "replaces 56% of sources in AI-generated responses every week",
        },
        "prompt_universe": {
            "value": "82,619 prompts across six countries",
            "quote": "Our analysis of 82,619 prompts over 17 weeks",
        },
        "sample_size": {
            "value": "82,619 prompts; 17 weeks",
            "quote": "Our analysis of 82,619 prompts over 17 weeks",
        },
        "unit_of_analysis": {
            "value": "cited source/domain per weekly prompt set",
            "quote": "sources in AI-generated responses",
        },
        "time_window": {
            "value": "17 weeks (study period, published May 2026)",
            "quote": "over 17 weeks",
        },
        "geography": {
            "value": "six countries incl. US, Germany, UK, France",
            "quote": "covering three platforms , six countries and 17 weeks",
        },
        "geography_basis": "source_stated",
        "language": {
            "value": "English-language report",
            "kind": "jsonld_field",
            "selector": "inLanguage=en-US (article JSON-LD)",
        },
        "language_basis": "inferred",
        "devices": None,
        "limitations": [
            "Vendor panel (SISTRIX data); prompt selection method not published in the article.",
            "Country-level ChatGPT churn varies (Germany 74%, UK 60%, France 42%); do not generalise one country.",
        ],
        "methodology_notes": {
            "value": "Weekly comparison of the source set per prompt; 'drift' = sources swapped out week to week.",
            "quote": "We took a closer look at the issue using SISTRIX data , covering three platforms , six countries and 17 weeks",
        },
    },
    "metrics": [
        {
            "metric_id": "chatgpt_weekly_churn",
            "label": "ChatGPT weekly source churn",
            "definition": {
                "value": "% of ChatGPT sources replaced each week",
                "quote": "ChatGPT replaces as much as 74%",
            },
            "value": {"value": "74%", "quote": "ChatGPT replaces as much as 74%"},
            "unit": {"value": "%", "quote": "74%"},
            "comparator": "exact",
            "window": {"value": "per week over 17 weeks", "quote": "every week"},
            "scope": {
                "value": "ChatGPT, six countries",
                "quote": "ChatGPT replaces as much as 74%",
            },
        },
        {
            "metric_id": "google_ai_mode_weekly_churn",
            "label": "Google AI Mode weekly source churn",
            "definition": {
                "value": "% of Google AI Mode sources replaced each week",
                "quote": "Google replaces 56% of sources",
            },
            "value": {
                "value": "56%",
                "quote": "Google replaces 56% of sources in AI-generated responses every week",
            },
            "unit": {"value": "%", "quote": "56%"},
            "comparator": "exact",
            "window": {"value": "per week over 17 weeks", "quote": "every week"},
            "scope": {
                "value": "Google AI Mode, six countries",
                "quote": "Google replaces 56% of sources",
            },
        },
        {
            "metric_id": "google_ai_mode_country_range",
            "label": "Google AI Mode weekly churn range across countries",
            "definition": {
                "value": "country-level weekly churn range",
                "quote": "drift rates in Google AI Mode are remarkably consistent across all six countries studied",
            },
            "value": {
                "value": "54-59%",
                "quote": "Drift rates remain consistently at 54-59% across six countries",
            },
            "unit": {"value": "%", "quote": "54-59%"},
            "comparator": "exact",
            "window": {"value": "weekly, 17 weeks", "quote": "over the 17-week period"},
            "scope": {
                "value": "Google AI Mode, six countries incl. US and Germany",
                "quote": "not a phenomenon specific to the US or Germany",
            },
        },
    ],
    "dates": {
        "published_at": "2026-05-01",
        "published_at_selector": "datePublished",
        "modified_at": "2026-05-12",
        "modified_at_selector": "dateModified",
        "measured_window": {"value": "17 weeks up to ~Apr 2026", "quote": "over 17 weeks"},
        "observed_at": "2026-09-16T12:05:00+00:00",
    },
    "capture_anchors": [
        {
            "kind": "jsonld_field",
            "selector": "datePublished=2026-05-01T11:34:47+00:00 / dateModified=2026-05-12T12:41:18+00:00",
        },
        {
            "kind": "verbatim_quote",
            "quote": "Google replaces 56% of sources in AI-generated responses every week, whilst ChatGPT replaces as much as 74%",
        },
    ],
    "extraction": {
        "method": "deterministic_parser",
        "tool": "ai_discovery.claims",
        "rule_id": "sistrix_citation_drift_v1",
    },
    "status": "current",
    "relationship": "new",
    "confidence": "medium",
}

YAN = {
    "source": {
        "source_id": "yandex-ai-search-pretrain-2026-09",
        "publisher": "Yandex",
        "url": "https://yandex.com/company/news/2026-09-14-01",
        "canonical_url": "https://yandex.com/company/news/2026-09-14-01",
        "source_class": "press_release",
        "robots_allowed": True,
    },
    "topic": "audience_usage",
    "statement": (
        "Yandex reports that more than 49 million people use its AI answers in Search each month, "
        "making it Yandex's most widely used generative AI product (press release, 14 Sep 2026)."
    ),
    "surfaces": ["yandex-ai-search"],
    "methodology": {
        "measurement_mode": "press_release",
        "metric_family": {"value": "monthly feature usage", "quote": "use the feature each month"},
        "metric_definition": {
            "value": "people who use AI answers in Yandex Search in a month",
            "quote": "use the feature each month",
        },
        "denominator": {
            "value": "monthly users of the AI answers feature within Yandex Search",
            "quote": "More than 49 million people use the feature each month",
        },
        "prompt_universe": None,
        "sample_size": None,
        "unit_of_analysis": {
            "value": "people (feature users), not app MAU and not all search users",
            "quote": "Yandex's most widely used generative AI product",
        },
        "time_window": {
            "value": "each month (no named measurement month; published Sep 2026)",
            "quote": "each month",
        },
        "geography": {
            "value": "Russia / Russian-language Yandex ecosystem",
            "quote": "blind tests of Russian-language answer quality",
        },
        "geography_basis": "source_stated",
        "language": {"value": "Russian", "quote": "Russian-language answer quality"},
        "language_basis": "source_stated",
        "devices": None,
        "limitations": [
            "Vendor press release; no sample, panel or measurement method published.",
            "Measured month is not named - only 'each month' at publication.",
        ],
        "methodology_notes": {
            "value": "Company-stated usage figure in a press release about open-sourcing the model behind the feature.",
            "quote": "Yandex has open-sourced Alice AI Search Pretrain",
        },
    },
    "metrics": [
        {
            "metric_id": "monthly_ai_answer_users",
            "label": "Monthly users of Yandex AI answers in Search",
            "definition": {
                "value": "people using AI answers in Yandex Search per month",
                "quote": "use the feature each month",
            },
            "value": {
                "value": 49000000,
                "quote": "More than 49 million people use the feature each month",
            },
            "unit": {"value": "people (monthly)", "quote": "49 million people"},
            "comparator": "at_least",
            "window": {"value": "each month (unnamed)", "quote": "each month"},
            "scope": {
                "value": "Yandex Search AI answers feature",
                "quote": "the feature each month",
            },
        },
    ],
    "dates": {
        "published_at": "2026-09-14",
        "published_at_selector": "page stamp 'September 14, 2026'",
        "modified_at": None,
        "modified_at_selector": None,
        "measured_window": {
            "value": "each month (no named measurement month)",
            "quote": "each month",
        },
        "observed_at": "2026-09-16T12:10:00+00:00",
    },
    "capture_anchors": [
        {"kind": "page_stamp", "selector": "September 14, 2026"},
        {
            "kind": "verbatim_quote",
            "quote": "More than 49 million people use the feature each month, making it Yandex's most widely used generative AI product",
        },
    ],
    "extraction": {
        "method": "deterministic_parser",
        "tool": "ai_discovery.claims",
        "rule_id": "yandex_feature_usage_v1",
    },
    "status": "current",
    "relationship": "new",
    "confidence": "low",
}

NAV = {
    "source": {
        "source_id": "naver-ai-tab-launch-2026-06",
        "publisher": "NAVER",
        "url": "https://www.navercorp.com/media/pressReleasesDetail?seq=10034442",
        "canonical_url": "https://www.navercorp.com/media/pressReleasesDetail?seq=10034442",
        "source_class": "press_release",
        "robots_allowed": True,
    },
    "topic": "referrals_conversion",
    "statement": (
        "NAVER's AI Tab surpassed 4 million cumulative users in ~2 months of beta, product and "
        "place card CTR exceeded 20%, and it is built on a model for NAVER's service environment "
        "which averages 50 million daily visitors (press release, 26 Jun 2026)."
    ),
    "surfaces": ["naver-ai"],
    "methodology": {
        "measurement_mode": "press_release",
        "metric_family": {
            "value": "cumulative users and card click-through rate",
            "quote": "Surpassed 4 million cumulative users",
        },
        "metric_definition": {
            "value": "beta cumulative users; CTR for product and place cards",
            "quote": "click-through rates (CTR) for both product and place cards exceeded 20%",
        },
        "denominator": {
            "value": "cumulative beta users (~2 months) and card CTR during beta - distinct denominators",
            "quote": "surpassed 4 million cumulative users in about two months",
        },
        "prompt_universe": None,
        "sample_size": None,
        "unit_of_analysis": {
            "value": "users and card impressions (three separate quantities kept apart)",
            "quote": "which receives an average of 50 million daily visitors",
        },
        "time_window": {
            "value": "~2 months post-Apr 2026 beta, to 26 Jun 2026 launch",
            "quote": "in about two months",
        },
        "geography": {
            "value": "South Korea (navercorp.com press release, Korean-language page)",
            "quote": "NAVER Officially Launches AI Tab",
        },
        "geography_basis": "publisher_scope",
        "language": {
            "value": "Korean",
            "kind": "jsonld_field",
            "selector": "document element lang=ko",
        },
        "language_basis": "source_stated",
        "devices": {
            "value": "mobile and PC search bars",
            "quote": "one click from the mobile and PC search bars",
        },
        "limitations": [
            "Vendor press release; no sample or measurement method published.",
            "The '50 million daily visitors' is the NAVER main page, not AI Tab users - must not be merged.",
        ],
        "methodology_notes": {
            "value": "Company-stated beta metrics in a launch press release; three quantities with different denominators.",
            "quote": "AI Tab, which launched in beta in April for NAVER Plus Membership users, surpassed 4 million cumulative users in about two months.",
        },
    },
    "metrics": [
        {
            "metric_id": "cumulative_users",
            "label": "AI Tab cumulative beta users",
            "definition": {
                "value": "cumulative users in ~2 months of beta",
                "quote": "Surpassed 4 million cumulative users in two months after beta launch",
            },
            "value": {
                "value": 4000000,
                "quote": "surpassed 4 million cumulative users in about two months",
            },
            "unit": {"value": "people (cumulative)", "quote": "4 million cumulative users"},
            "comparator": "at_least",
            "window": {"value": "~2 months of beta (Apr-Jun 2026)", "quote": "in about two months"},
            "scope": {
                "value": "NAVER Plus Membership beta users",
                "quote": "for NAVER Plus Membership users",
            },
        },
        {
            "metric_id": "card_ctr",
            "label": "Product/place card click-through rate",
            "definition": {
                "value": "CTR for product and place cards during beta",
                "quote": "click-through rates (CTR) for both product and place cards",
            },
            "value": {
                "value": ">20%",
                "quote": "click-through rates (CTR) for both product and place cards exceeded 20%",
            },
            "unit": {"value": "%", "quote": "20%"},
            "comparator": "at_least",
            "window": {"value": "beta period", "quote": "During the beta period"},
            "scope": {"value": "product and place cards", "quote": "both product and place cards"},
        },
        {
            "metric_id": "main_page_daily_visitors",
            "label": "NAVER main page average daily visitors",
            "definition": {
                "value": "average daily visitors to NAVER's main page (not AI Tab users)",
                "quote": "which receives an average of 50 million daily visitors",
            },
            "value": {
                "value": 50000000,
                "quote": "which receives an average of 50 million daily visitors",
            },
            "unit": {"value": "visitors per day", "quote": "daily visitors"},
            "comparator": "approx",
            "window": {"value": "period not stated", "quote": "receives an average of"},
            "scope": {
                "value": "NAVER main page / service environment",
                "quote": "NAVER's service environment, which receives an average of 50 million daily visitors",
            },
        },
    ],
    "dates": {
        "published_at": "2026-06-26",
        "published_at_selector": "page stamp '2026.06.26'",
        "modified_at": None,
        "modified_at_selector": None,
        "measured_window": {
            "value": "Apr-Jun 2026 (~2-month beta)",
            "quote": "in about two months",
        },
        "observed_at": "2026-09-16T12:15:00+00:00",
    },
    "capture_anchors": [
        {"kind": "page_stamp", "selector": "2026.06.26"},
        {
            "kind": "verbatim_quote",
            "quote": "surpassed 4 million cumulative users in about two months",
        },
    ],
    "extraction": {
        "method": "deterministic_parser",
        "tool": "ai_discovery.claims",
        "rule_id": "naver_ai_tab_beta_v1",
    },
    "status": "current",
    "relationship": "new",
    "confidence": "low",
}

BUNDLE = {"extraction_version": "claim-extraction-0.1.0", "claims": [SIM, SIS, YAN, NAV]}


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(BUNDLE, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(BUNDLE['claims'])} claim specs)")
