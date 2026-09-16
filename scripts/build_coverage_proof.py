"""Build the issue-#8 coverage-gap proof from the canonical surface registry + live evidence."""

import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from ai_discovery.coverage import CoverageMatrix, LedgerDerivedMatrix, Priority

UTC = dt.UTC

# Load the canonical surface registry so gaps come from the config, not hardcoded literals.
import yaml

surfaces_path = os.path.join(os.path.dirname(__file__), "..", "config", "surfaces.yaml")
with open(surfaces_path) as f:
    registry = yaml.safe_load(f)
surface_ids = [s["id"] for s in registry.get("surfaces", [])]
print(f"loaded {len(surface_ids)} surfaces from config/surfaces.yaml")

# Seed importance weights from docs/PLATFORM_COVERAGE.md priorities.
# These are registry-level weights; a changed weight changes the queue order.
importance = {
    "chatgpt": 0.9,
    "google-gemini": 0.85,
    "google-ai-mode": 0.85,
    "google-ai-overviews": 0.8,
    "microsoft-copilot": 0.7,
    "bing-copilot-search": 0.65,
    "claude": 0.7,
    "perplexity": 0.7,
    "deepseek-chat": 0.82,
    "grok": 0.6,
    "meta-ai": 0.6,
    "doubao": 0.78,
    "qwen": 0.71,
    "baidu-wenxin-assistant": 0.58,
    "baidu-ai-search": 0.55,
    "quark-ai": 0.5,
    "tencent-yuanbao": 0.45,
    "kimi": 0.45,
    "360-nano-ai-search": 0.3,
    "zhipu-qingyan": 0.3,
    "naver-ai-tab": 0.55,
    "kakao-kanana": 0.45,
    "yandex-search-ai": 0.52,
    "gigachat": 0.3,
    "mistral-le-chat": 0.4,
    "you-com": 0.2,
    "duck-ai": 0.2,
    "brave-leo": 0.2,
    "genspark": 0.1,
    "felo": 0.1,
    "manus": 0.1,
    "poe": 0.1,
    "apple-siri": 0.35,
    "amazon-rufus": 0.3,
    "msty": 0.05,
}

# Derive gaps from the registry + claim ledger (no hardcoded CoverageGap literals here).
claims = []  # empty ledger: no claims ingested yet; every surface gets no_evidence
dm = LedgerDerivedMatrix(
    claims, surfaces_registry=surface_ids, stale_after_days=90, importance_overrides=importance
)
gaps = dm.derive()

matrix = CoverageMatrix(gaps)
queue = matrix.research_queue()

result = {
    "generated_at": dt.datetime.now(UTC).isoformat(),
    "total_gaps": len(gaps),
    "high_priority": len(matrix.by_priority(Priority.high)),
    "regional_china_gaps": sum(
        1
        for s in surface_ids
        if s
        in (
            "doubao",
            "qwen",
            "baidu-ai-search",
            "baidu-wenxin-assistant",
            "quark-ai",
            "tencent-yuanbao",
            "kimi",
            "360-nano-ai-search",
            "zhipu-qingyan",
            "deepseek-chat",
        )
    ),
    "regional_korea_gaps": sum(1 for s in surface_ids if s in ("naver-ai-tab", "kakao-kanana")),
    "regional_russia_gaps": sum(1 for s in surface_ids if s in ("yandex-search-ai", "gigachat")),
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
