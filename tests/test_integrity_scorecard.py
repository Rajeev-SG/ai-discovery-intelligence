"""Issue #29: the offline integrity scorecard pins the real guards."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "build_integrity_scorecard.py"
SCORECARD = REPO / "proof" / "integrity" / "scorecard.json"


def _run() -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )


def test_scorecard_runs_and_writes_a_durable_artifact():
    result = _run()
    assert result.returncode == 0, result.stdout + result.stderr
    assert SCORECARD.exists(), "scorecard artifact must be written to proof/"
    body = json.loads(SCORECARD.read_text())
    assert body["checks_total"] >= 6
    assert body["checks_failed"] == 0, body["checks"]
    assert len(body["negative_controls"]) >= 2


def test_scorecard_distinguishes_verified_from_warnings():
    body = json.loads(SCORECARD.read_text())
    for check in body["checks"]:
        assert check["status"] in ("verified", "warning")
        assert check["result"] in ("pass", "fail")
        assert check["criterion"], check["name"]


def test_removing_the_fabrication_guard_makes_the_scorecard_fail(tmp_path):
    """Acceptance: the scorecard is a real guard, not decoration."""

    target = REPO / "src" / "ai_discovery" / "claim_models.py"
    original = target.read_text()
    try:
        target.write_text(
            original.replace(
                "        if self.quote:\n"
                "            return normalize_text(self.quote) in normalize_text(capture_text)",
                "        return True  # guard removed\n"
                "        if self.quote:\n"
                "            return normalize_text(self.quote) in normalize_text(capture_text)",
                1,
            )
        )
        result = _run()
        assert result.returncode != 0, "scorecard must fail when the guard is removed"
        assert "fabricated_claim_rejected" in result.stdout
    finally:
        target.write_text(original)
        _run()  # restore the clean artifact
