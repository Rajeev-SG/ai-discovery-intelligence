"""Build the issue-#8 coverage-gap proof from the canonical surface registry + live evidence."""

import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from ai_discovery.coverage import CoverageGap, CoverageMatrix, GapCategory, Priority

UTC = dt.UTC

gaps = [
    CoverageGap(
        id="gap-deepseek-retrieval",
        surfaces=["deepseek-chat"],
        topics=["retrieval", "search_trigger", "fanout", "citation", "crawler"],
        geographies=["global", "china"],
        category=GapCategory.under_documented,
        description="DeepSeek Chat's web-retrieval trigger, fan-out behaviour, upstream index provider, and crawler/user-agent controls are not documented. Official DeepSeek docs describe API, not consumer-UI retrieval. No third-party study covers DeepSeek retrieval behaviour.",
        priority=Priority.high,
        importance_score=0.82,
        evidence_available=False,
        suggested_research_query="DeepSeek consumer web retrieval search citations crawler user agent robots",
        metadata={
            "note": "Issue #1's observation plane renders retrieval as under_documented for DeepSeek"
        },
    ),
    CoverageGap(
        id="gap-doubao-retrieval",
        surfaces=["doubao"],
        topics=["retrieval", "citation", "shopping", "crawler"],
        geographies=["china"],
        category=GapCategory.no_evidence,
        description="Doubao (ByteDance, 382M MAU) has no published evidence about retrieval/citation/shopping behaviour in the consumer UI. No English or Chinese public study describes its web-search integration or citation policy.",
        priority=Priority.high,
        importance_score=0.78,
        evidence_available=False,
        suggested_research_query="豆包 搜索 引用 爬虫 robots 检索 retrieval Doubao",
        metadata={"note": "Largest China surface by MAU; retrieval model completely undocumented"},
    ),
    CoverageGap(
        id="gap-qwen-citations",
        surfaces=["qwen"],
        topics=["citation", "source_selection", "fanout"],
        geographies=["china"],
        category=GapCategory.no_evidence,
        description="Qwen (167M MAU per QuestMobile) has no public study on which sources it cites or how it selects/filters them. Alibaba's docs focus on model capabilities, not consumer-source behaviour.",
        priority=Priority.high,
        importance_score=0.71,
        evidence_available=False,
        suggested_research_query="Qwen 千问 citations sources retrieval consumer search",
        metadata={
            "note": "QuestMobile source-selection study (2059118379722096641) may cover Qwen but its quantitative content is gated"
        },
    ),
    CoverageGap(
        id="gap-baidu-wenxin-retrieval",
        surfaces=["baidu-wenxin-assistant"],
        topics=["retrieval", "search_trigger", "citation", "shopping"],
        geographies=["china"],
        category=GapCategory.no_evidence,
        description="Baidu Wenxin Assistant (launched June 2026) has no published evidence about its retrieval stack, citation policy, or commerce integration. Distinct from Baidu AI Search but both are under-documented.",
        priority=Priority.medium,
        importance_score=0.58,
        evidence_available=False,
        suggested_research_query="百度文心助手 检索 引用 搜索 Wenxin retrieval",
        metadata={
            "note": "June-2026 consolidation makes this a new surface; no third-party coverage yet"
        },
    ),
    CoverageGap(
        id="gap-naver-retrieval-detail",
        surfaces=["naver-ai-tab"],
        topics=["retrieval", "search_trigger", "fanout", "citation"],
        geographies=["korea"],
        category=GapCategory.single_source,
        description="NAVER AI Tab audience evidence (4M users, 20% CTR) exists from NAVER's own press release, but the retrieval architecture, query fan-out and citation policy have no public documentation. Single-vendor source; no independent corroboration.",
        priority=Priority.medium,
        importance_score=0.55,
        evidence_available=True,
        existing_evidence_urls=["https://www.navercorp.com/media/pressReleasesDetail?seq=10034442"],
        suggested_research_query="NAVER AI Tab retrieval search fanout citations architecture",
        metadata={"note": "Audience size confirmed; retrieval/citation model unknown"},
    ),
    CoverageGap(
        id="gap-yandex-citation-detail",
        surfaces=["yandex-search-ai"],
        topics=["citation", "source_selection", "crawler"],
        geographies=["russia_cis"],
        category=GapCategory.single_source,
        description="Yandex AI answers' 49M monthly-user evidence is vendor-reported. Citation behaviour, source-selection logic and crawler (YandexBot AI) policy are undocumented in English or Russian public sources.",
        priority=Priority.medium,
        importance_score=0.52,
        evidence_available=True,
        existing_evidence_urls=["https://yandex.com/company/news/2026-09-14-01"],
        suggested_research_query="Yandex AI answers citation source YandexBot AI crawler robots",
        metadata={"note": "Vendor-confirmed usage; retrieval/citation architecture unknown"},
    ),
    CoverageGap(
        id="gap-chatgpt-crawl-controls",
        surfaces=["chatgpt"],
        topics=["crawler", "user_agent", "robots"],
        geographies=["global"],
        category=GapCategory.under_documented,
        description="OpenAI's platform docs describe GPTBot and OAI-SearchBot, but the consumer-UI crawler policy (does ChatGPT web-search respect robots? does it use a different agent than the training crawl?) is not fully documented. Retrieval vs training-crawl distinction is unclear.",
        priority=Priority.low,
        importance_score=0.40,
        evidence_available=True,
        existing_evidence_urls=["https://platform.openai.com/docs/bots"],
        suggested_research_query="ChatGPT web search crawler user-agent robots.txt consumer vs training",
        metadata={
            "note": "Official docs partially cover this; consumer-UI specifics remain unclear"
        },
    ),
    CoverageGap(
        id="gap-kakao-kanana-retrieval",
        surfaces=["kakao-kanana"],
        topics=["retrieval", "search_trigger", "citation", "shopping"],
        geographies=["korea"],
        category=GapCategory.no_evidence,
        description="Kakao Kanana (in KakaoTalk, September 2026) has no public evidence about its retrieval, citation or commerce behaviour. Kakao's ecosystem search/recommendation model is not documented for third-party publishers.",
        priority=Priority.medium,
        importance_score=0.45,
        evidence_available=False,
        suggested_research_query="Kakao Kanana retrieval search citations KakaoTalk AI",
        metadata={"note": "Launched within KakaoTalk; tens-of-millions ecosystem reach"},
    ),
]

matrix = CoverageMatrix(gaps)
queue = matrix.research_queue()

result = {
    "generated_at": dt.datetime.now(UTC).isoformat(),
    "total_gaps": len(gaps),
    "high_priority": len(matrix.by_priority(Priority.high)),
    "regional_china_gaps": sum(1 for g in gaps if "china" in g.geographies),
    "regional_korea_gaps": sum(1 for g in gaps if "korea" in g.geographies),
    "regional_russia_gaps": sum(1 for g in gaps if "russia_cis" in g.geographies),
    "deepseek_retrieval_gap": True,
    "gaps": [g.model_dump(mode="json") for g in queue],
}

out_dir = os.path.join(os.path.dirname(__file__), "..", "proof", "coverage")
os.makedirs(out_dir, exist_ok=True)
with open(os.path.join(out_dir, "gaps.json"), "w") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print(
    f"gaps: {len(gaps)} (high: {result['high_priority']}, china: {result['regional_china_gaps']}, korea: {result['regional_korea_gaps']}, russia: {result['regional_russia_gaps']})"
)
print(f"deepseek-retrieval gap: {result['deepseek_retrieval_gap']}")
print(f"saved → {os.path.join(out_dir, 'gaps.json')}")
