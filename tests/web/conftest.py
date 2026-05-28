import sys
import os
from pathlib import Path

# Ensure repo root is on sys.path so `web` is importable regardless of how pytest is invoked.
# Must happen before any `from web.*` imports; pytest assertion rewriter may exec this
# file in isolation before root conftest path mutations apply.
_HERE = Path(__file__).resolve()
# tests/web/conftest.py → parent=tests/web → parent=tests → parent=repo_root
_REPO_ROOT = _HERE.parent.parent.parent
_REPO_ROOT_STR = str(_REPO_ROOT)

# Debug: verify web/app.py is reachable
_WEB_APP = _REPO_ROOT / "web" / "app.py"

if _REPO_ROOT_STR not in sys.path:
    sys.path.insert(0, _REPO_ROOT_STR)

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    from web.app import create_app  # deferred import — path guaranteed above
    return TestClient(create_app())
