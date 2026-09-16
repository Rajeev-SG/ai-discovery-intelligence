"""Batch-capture and extract claims from the fetchable source registry."""

import hashlib
import json
import sys
import time
import urllib.robotparser
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "proof" / "claim_ledger"
CAPS = OUT / "captures"
CAPS.mkdir(parents=True, exist_ok=True)
SPECS = OUT / "claim_specs.json"

UA = "ai-discovery-intelligence/0.1 (+https://github.com/Rajeev-SG/ai-discovery-intelligence)"

sys.path.insert(0, str(ROOT / "src"))
from ai_discovery.claims import extract_capture_text

URLS = {
    "openai-platform-bots": "https://platform.openai.com/docs/bots",
    "google-search-central-ai": "https://developers.google.com/search/docs/appearance/ai-features",
    "xai-docs": "https://docs.x.ai/",
    "meta-ai-news": "https://ai.meta.com/blog/",
    "alibaba-qwen-blog": "https://qwenlm.github.io/blog/",
    "deepseek-docs": "https://api-docs.deepseek.com/",
    "ahrefs-blog-ai": "https://ahrefs.com/blog/why-chatgpt-cites-pages/",
    "semrush-blog-ai": "https://www.semrush.com/blog/",
    "sistrix-blog": "https://www.sistrix.com/blog/",
    "peec-blog": "https://peec.ai/blog",
    "statcounter-ai-chatbot": "https://gs.statcounter.com/ai-chatbot-market-share",
    "cloudflare-blog-ai": "https://blog.cloudflare.com/tag/ai/",
}


def fetch(url: str) -> tuple[str, bytes | None]:
    base = "/".join(url.split("/")[:3])
    rp = urllib.robotparser.RobotFileParser()
    try:
        r = httpx.get(
            f"{base}/robots.txt", headers={"User-Agent": UA}, timeout=10, follow_redirects=True
        )
        rp.parse(r.text.splitlines()) if r.status_code == 200 else rp.parse(
            ["User-agent: *", "Allow: /"]
        )
    except (httpx.HTTPError, OSError):
        rp.parse(["User-agent: *", "Allow: /"])
    if not rp.can_fetch(UA, url):
        return "robots_denied", None
    try:
        resp = httpx.get(url, headers={"User-Agent": UA}, timeout=20, follow_redirects=True)
        if resp.status_code != 200:
            return f"http_{resp.status_code}", None
        return "ok", resp.content
    except (httpx.HTTPError, OSError) as e:
        return f"error:{type(e).__name__}", None


captured = {}
for sid, url in URLS.items():
    status, raw = fetch(url)
    if raw:
        path = CAPS / f"{sid}.html"
        path.write_bytes(raw)
        text = extract_capture_text(raw.decode("utf-8", errors="replace"))
        sha = hashlib.sha256(text.encode()).hexdigest()
        captured[sid] = {"url": url, "sha256": sha, "text_chars": len(text), "status": status}
        print(f"  ✓ {sid:30} {len(text):6} chars  sha={sha[:12]}")
    else:
        print(f"  ✗ {sid:30} {status}")
    time.sleep(2)

print(f"\ncaptured: {len(captured)}/{len(URLS)}")
# Save capture index for the claim-spec authoring step
with open(OUT / "capture_index.json", "w") as f:
    json.dump(captured, f, indent=2)
print(f"saved → {OUT / 'capture_index.json'}")
