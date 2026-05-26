"""Tests for the web_index tail hook in contribute_back.

Two complementary strategies:
  - test_run_calls_web_index_build: drives the full run() path (with interactive parts
    stubbed) to confirm the hook fires end-to-end.
  - Tests 2-4: call _run_web_hook() directly to verify the non-blocking contract and
    stdout/stderr messages without needing to navigate the full interactive checklist.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_build_result(ok: list[str] | None = None, failed: list[str] | None = None):
    """Return a real BuildResult instance."""
    from scripts.workflow.web_index import BuildResult
    return BuildResult(
        domains_ok=ok or [],
        domains_failed=failed or [],
    )


def _run_full(monkeypatch, mock_build):
    """Run contribute_back.run() with interactive parts stubbed.

    We feed a catalog file so questions_for() returns a non-empty list,
    which means run() walks the checklist and reaches _run_web_hook() at the end.
    The input() call is patched to return "y" so no missing categories are recorded
    and learn_log calls are not triggered.
    """
    import scripts.workflow.contribute_back as cb
    import scripts.workflow.web_index as wi

    monkeypatch.setattr(cb, "_growth_start_date", lambda: "2026-01-01")
    # catalog file triggers the "catalog" category → questions_for returns it
    monkeypatch.setattr(cb, "collect_changes", lambda since: {
        "andrej-karpathy-rdb-skill": ["presets/customer.seed.md"]
    })
    monkeypatch.setattr("builtins.input", lambda _prompt: "y")
    monkeypatch.setattr(wi, "build", mock_build)

    return cb.run()


# ---------------------------------------------------------------------------
# Test 1 — full run() path calls web_index.build
# ---------------------------------------------------------------------------

def test_run_calls_web_index_build(monkeypatch):
    mock_build = MagicMock(return_value=_make_build_result(ok=["customer"]))
    ret = _run_full(monkeypatch, mock_build)
    mock_build.assert_called_once()
    assert ret == 0


# ---------------------------------------------------------------------------
# Test 2 — exceptions from build() are swallowed
# ---------------------------------------------------------------------------

def test_run_swallows_web_index_exception(monkeypatch):
    import scripts.workflow.web_index as wi
    import scripts.workflow.contribute_back as cb

    monkeypatch.setattr(wi, "build", lambda **_kw: (_ for _ in ()).throw(RuntimeError("boom")))

    # _run_web_hook must not propagate
    cb._run_web_hook()  # would raise if not caught


# ---------------------------------------------------------------------------
# Test 3 — partial failure is logged to stderr
# ---------------------------------------------------------------------------

def test_run_logs_partial_failure_to_stderr(monkeypatch, capsys):
    import scripts.workflow.web_index as wi
    import scripts.workflow.contribute_back as cb

    monkeypatch.setattr(wi, "build", MagicMock(
        return_value=_make_build_result(ok=[], failed=["x"])
    ))

    cb._run_web_hook()
    captured = capsys.readouterr()
    assert "partial failure" in captured.err


# ---------------------------------------------------------------------------
# Test 4 — successful build is logged to stdout
# ---------------------------------------------------------------------------

def test_run_logs_success_to_stdout(monkeypatch, capsys):
    import scripts.workflow.web_index as wi
    import scripts.workflow.contribute_back as cb

    monkeypatch.setattr(wi, "build", MagicMock(
        return_value=_make_build_result(ok=["x"])
    ))

    cb._run_web_hook()
    captured = capsys.readouterr()
    assert "rebuilt OK" in captured.out
