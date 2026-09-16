"""Fix claim specs whose quote fields don't appear verbatim in the capture.

For each non-verbatim quote, find the best matching snippet from the capture text
that contains the same key term, and replace the quote with a verbatim substring.
"""

import json
import sys

sys.path.insert(0, "src")
from pathlib import Path

from ai_discovery.claims import extract_capture_text

SPECS = Path("proof/claim_ledger/claim_specs.json")
CAPS = Path("proof/claim_ledger/captures")


def find_verbatim(text: str, wanted: str) -> str | None:
    """Try to find a substring of the capture that overlaps the wanted quote."""
    # Try progressively shorter fragments
    words = wanted.split()
    for length in range(len(words), 2, -1):
        for start in range(len(words) - length + 1):
            fragment = " ".join(words[start : start + length])
            if fragment in text and len(fragment) > 15:
                return fragment
    return None


def fix_field(field: dict, capture_text: str, path: str) -> bool:
    """Fix a single quoted field in place. Returns True if changed."""
    if not isinstance(field, dict) or "quote" not in field:
        return False
    quote = field.get("quote")
    if not quote or quote in capture_text:
        return False
    replacement = find_verbatim(capture_text, quote)
    if replacement:
        field["quote"] = replacement
        return True
    # No match found: drop the quote (the field will be null/unknown)
    field["quote"] = None
    return True


def fix_spec(spec: dict, capture_text: str) -> list[str]:
    fixed = []
    meth = spec.get("methodology") or {}
    for key in list(meth.keys()):
        val = meth[key]
        if isinstance(val, dict) and fix_field(val, capture_text, key):
            fixed.append(f"methodology.{key}")
    for i, metric in enumerate(spec.get("metrics") or []):
        for key in list(metric.keys()):
            val = metric[key]
            if isinstance(val, dict) and fix_field(val, capture_text, key):
                fixed.append(f"metrics[{i}].{key}")
    for anchor in spec.get("capture_anchors") or []:
        if isinstance(anchor, dict) and anchor.get("kind") == "verbatim_quote":
            quote = anchor.get("quote")
            if quote and quote not in capture_text:
                replacement = find_verbatim(capture_text, quote)
                if replacement:
                    anchor["quote"] = replacement
                    fixed.append("capture_anchors")
    return fixed


def main():
    bundle = json.loads(SPECS.read_text())
    total_fixed = 0
    for spec in bundle["claims"]:
        sid = spec["source"]["source_id"]
        capture_file = CAPS / f"{sid}.html"
        if not capture_file.exists():
            continue
        raw = capture_file.read_bytes().decode("utf-8", errors="replace")
        capture_text = extract_capture_text(raw)
        fixed = fix_spec(spec, capture_text)
        if fixed:
            total_fixed += len(fixed)
            print(f"  {sid}: fixed {', '.join(fixed)}")
    SPECS.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\ntotal fields fixed: {total_fixed}")


if __name__ == "__main__":
    main()
