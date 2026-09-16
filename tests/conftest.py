"""Put the src/ layout on sys.path so the ledger tests run without packaging.

The worktree's pyproject deliberately carries no pytest config until the
integration commit with issue #2, which adds ``pythonpath = ["src"]``.
"""

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
