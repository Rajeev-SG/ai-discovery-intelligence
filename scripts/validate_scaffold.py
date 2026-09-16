from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
required = [
    "README.md",
    "AGENTS.md",
    "docs/AGENT_BOOTSTRAP.md",
    "docs/OSS_STACK.md",
    "docs/ACCEPTANCE_STANDARD.md",
    "config/surfaces.yaml",
    "config/sources.yaml",
    "config/executive_policy.yaml",
    "config/significance.yaml",
]
missing = [p for p in required if not (ROOT / p).exists()]
if missing:
    raise SystemExit(f"missing required files: {missing}")

for name in ["surfaces.yaml", "sources.yaml", "executive_policy.yaml", "significance.yaml"]:
    with (ROOT / "config" / name).open(encoding="utf-8") as fh:
        yaml.safe_load(fh)

surfaces = yaml.safe_load((ROOT / "config/surfaces.yaml").read_text())["surfaces"]
ids = [s["id"] for s in surfaces]
if len(ids) != len(set(ids)):
    raise SystemExit("duplicate surface ids")
for must in ["chatgpt", "deepseek-chat", "doubao", "qwen-consumer", "naver-ai", "yandex-ai-search"]:
    if must not in ids:
        raise SystemExit(f"required global/regional surface missing: {must}")
print(f"OK: {len(surfaces)} surfaces; scaffold invariants valid")
