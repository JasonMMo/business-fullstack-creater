# tests/test_ui_overlay_registry.py
"""Tests for the UI overlay adapter registry (v0.5 H4)."""
import pytest

import ui_overlay_registry
import stage5_overlay  # noqa: F401 — import side-effect registers "nexacro" (+ "react")


def test_nexacro_and_react_are_registered():
    """stage5_overlay import registers nexacro; react_overlay registers react."""
    names = ui_overlay_registry.registered()
    assert "nexacro" in names
    assert "react" in names


def test_dispatch_unknown_ui_raises():
    with pytest.raises(KeyError) as exc:
        ui_overlay_registry.dispatch("svelte")
    msg = str(exc.value)
    assert "svelte" in msg
    assert "nexacro" in msg  # registered set shown for diagnosis


def test_register_allows_third_party_adapter():
    """Third-party UIs can register without modifying the registry."""
    calls = {}

    def fake_adapter(**kwargs):
        calls.update(kwargs)
        return {"react_api_written": [], "java_copied": []}

    ui_overlay_registry.register("fake-ui", fake_adapter)
    try:
        result = ui_overlay_registry.dispatch("fake-ui", out_dir="x", target_dir="y")
        assert result == {"react_api_written": [], "java_copied": []}
        assert calls == {"out_dir": "x", "target_dir": "y"}
    finally:
        # Keep the registry clean between tests
        ui_overlay_registry.REGISTRY.pop("fake-ui", None)


def test_run_overlay_default_dispatches_to_nexacro(monkeypatch):
    """stage5_overlay.run_overlay() must default ui='nexacro' for v0.4 callers."""
    seen = {}

    def fake_nexacro(**kwargs):
        seen["called"] = True
        return {"java_copied": [], "menu_warning": None}

    monkeypatch.setitem(ui_overlay_registry.REGISTRY, "nexacro", fake_nexacro)
    result = stage5_overlay.run_overlay(
        out_dir="o", target_dir="t", domain_slug="x", domain_label="X",
        service_pascal="X", blueprint_entities=[],
    )
    assert seen.get("called") is True
    assert "java_copied" in result
