"""
tests/conftest.py — Ensure repo root is on sys.path for all test sub-packages.

The root conftest.py adds scripts/ and repo root to sys.path. This file
exists as a safety net for cases where pytest discovers test sub-packages
before the root conftest sys.path mutations propagate.
"""
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
for _p in (str(_REPO_ROOT / "scripts"), str(_REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
