"""Issue #29: the offline integrity scorecard pins the real guards."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "build_integrity_scorecard.py"
SCORECARD = REPO / "proof" / "integrity" / "scorecard.json"


def _run(env: dict | None = None) -> subprocess.CompletedProcess:
    merged = {**os.environ, **(env or {})}
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
        env=merged,
    )


def _isolated_src(tmp_path: Path) -> Path:
    """A throwaway copy of src/ (+ config/) so a mutation test never touches the real tree.

    ``config/`` is copied because the scorer loads ``significance.yaml`` relative
    to the package location, and the copied package resolves it under tmp.
    """

    shutil.copytree(REPO / "config", tmp_path / "config")
    copy = tmp_path / "src"
    shutil.copytree(REPO / "src", copy)
    return copy


def test_scorecard_writes_its_artifact_and_matches_the_committed_one(tmp_path):
    # Write to tmp so a test run never churns the checked-in artifact.
    out = tmp_path / "scorecard.json"
    result = _run(env={"INTEGRITY_SCORECARD_OUT": str(out)})
    assert result.returncode == 0, result.stdout + result.stderr
    assert out.exists(), "scorecard artifact must be written"
    body = json.loads(out.read_text())
    assert body["checks_total"] >= 6
    assert body["checks_failed"] == 0, body["checks"]
    assert len(body["negative_controls"]) >= 2
    committed = json.loads(SCORECARD.read_text())
    # The artifact is deterministic: regenerating it must reproduce the committed
    # content exactly (same checks AND same content hash), so CI leaves no diff.
    assert committed == body, "committed scorecard is stale; regenerate it"
    assert committed["checks_failed"] == 0


def test_scorecard_distinguishes_verified_from_warnings():
    body = json.loads(SCORECARD.read_text())
    for check in body["checks"]:
        assert check["status"] in ("verified", "warning")
        assert check["result"] in ("pass", "fail")
        assert check["criterion"], check["name"]


def test_removing_the_fabrication_guard_makes_the_scorecard_fail(tmp_path):
    """Acceptance: the scorecard is a real guard, not decoration.

    The mutation runs against an **isolated copy** of the package (via
    INTEGRITY_SRC_ROOT) with the artifact in tmp, so a crashed run can never leave
    the real source mutated or dirty the checked-in scorecard.
    """

    src = _isolated_src(tmp_path)
    target = src / "ai_discovery" / "claim_models.py"
    original = target.read_text()
    anchor = (
        "        if self.quote:\n"
        "            return normalize_text(self.quote) in normalize_text(capture_text)"
    )
    assert anchor in original, "anchor drifted; update the mutation or the test verifies nothing"
    mutated = original.replace(anchor, "        return True  # guard removed\n" + anchor, 1)
    assert mutated != original, "mutation did not apply"
    target.write_text(mutated)

    result = _run(
        env={
            "INTEGRITY_SRC_ROOT": str(src),
            "INTEGRITY_SCORECARD_OUT": str(tmp_path / "scorecard.json"),
        }
    )
    assert result.returncode != 0, "scorecard must fail when the guard is removed"
    assert "fabricated_claim_rejected" in result.stdout
    # The real tree is untouched and the checked-in artifact is never rewritten.
    assert (REPO / "src" / "ai_discovery" / "claim_models.py").read_text() == original


def test_removing_correction_protection_makes_the_scorecard_fail(tmp_path):
    """Acceptance: the correction-retention guard is likewise real."""

    src = _isolated_src(tmp_path)
    target = src / "ai_discovery" / "change_events.py"
    original = target.read_text()
    anchor = "            if self._is_protected(event):\n                result.append(event)\n                continue\n"
    assert anchor in original, "anchor drifted"
    replaced = original.replace(anchor, "", 1)
    assert replaced != original, "mutation did not apply"
    target.write_text(replaced)

    result = _run(
        env={
            "INTEGRITY_SRC_ROOT": str(src),
            "INTEGRITY_SCORECARD_OUT": str(tmp_path / "scorecard.json"),
        }
    )
    assert result.returncode != 0, "scorecard must fail when correction protection is removed"
    assert "correction_retained" in result.stdout
    assert (REPO / "src" / "ai_discovery" / "change_events.py").read_text() == original
