"""
web/run_registry.py — In-memory registry for scaffold run results.

Keyed by UUID4 hex string. Intentionally simple for M1 single-user self-host.
"""
from __future__ import annotations

import uuid
from typing import Dict, Optional

from web.adapters.scaffold_runner import ScaffoldResult

_registry: Dict[str, ScaffoldResult] = {}


def register(result: ScaffoldResult) -> str:
    """Store *result* and return the assigned run_id (uuid4 hex)."""
    run_id = uuid.uuid4().hex
    _registry[run_id] = result
    return run_id


def get(run_id: str) -> Optional[ScaffoldResult]:
    """Return the ScaffoldResult for *run_id*, or None if not found."""
    return _registry.get(run_id)


def clear() -> None:
    """Remove all entries — used by tests to ensure isolation."""
    _registry.clear()
