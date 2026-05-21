"""Start a new Growth cycle: append row in learn-log §6."""
from __future__ import annotations
import sys
from pathlib import Path

# Support both `python -m scripts.workflow.growth_start` (package import)
# and `python scripts/workflow/growth_start.py` (direct script invocation).
try:
    from . import learn_log
except ImportError:
    _root = str(Path(__file__).resolve().parents[2])
    if _root not in sys.path:
        sys.path.insert(0, _root)
    from scripts.workflow import learn_log


def start(name: str, today: str | None = None) -> int:
    name = (name or "").strip()
    if not name:
        raise ValueError("name is required")
    return learn_log.append_row(name, today=today)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: growth_start.py <name>", file=sys.stderr)
        sys.exit(2)
    name = " ".join(sys.argv[1:])
    n = start(name)
    print(f"Growth-{n} started. learn-log §6 placeholder 추가됨.")
