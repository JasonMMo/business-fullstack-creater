# scripts/ui_overlay_registry.py
"""UI overlay adapter registry (v0.5 H4).

Keeps `stage5_overlay.run_overlay()` UI-agnostic — concrete UI overlays
register themselves and dispatch by name. New UI = add module + register().

Contract: each adapter is a callable with the same keyword signature as
`stage5_overlay._nexacro_overlay_run` and returns a report dict with the
keys documented in adapters/ui-contract.md §5.2.
"""
from typing import Callable

REGISTRY: dict[str, Callable[..., dict]] = {}


def register(name: str, fn: Callable[..., dict]) -> None:
    """Register a UI overlay adapter."""
    REGISTRY[name] = fn


def dispatch(ui: str, **kwargs) -> dict:
    """Invoke the registered adapter for `ui`. Raises KeyError if unknown."""
    if ui not in REGISTRY:
        raise KeyError(
            f"Unknown UI overlay adapter: {ui!r}. "
            f"Registered: {sorted(REGISTRY)}"
        )
    return REGISTRY[ui](**kwargs)


def registered() -> list[str]:
    """Return sorted list of registered UI names."""
    return sorted(REGISTRY)
