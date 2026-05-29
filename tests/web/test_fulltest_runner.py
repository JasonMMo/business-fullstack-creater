"""
tests/web/test_fulltest_runner.py — Growth-83 fulltest_runner adapter unit tests.

Tests subprocess JSON parsing, timeout handling, and FULLTEST_NO_LEARNLOG env injection.
"""
from __future__ import annotations

import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from web.adapters.fulltest_runner import FullTestJobResult, run


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_proc_result(stdout: str, returncode: int = 0) -> MagicMock:
    proc = MagicMock()
    proc.stdout = stdout
    proc.stderr = ""
    proc.returncode = returncode
    return proc


# ---------------------------------------------------------------------------
# test_runner_parses_json_success
# ---------------------------------------------------------------------------

def test_runner_parses_json_success(monkeypatch) -> None:
    """subprocess stdout with full JSON → FullTestJobResult.green=True."""
    payload = {
        "label": "풀테스트 그린",
        "lane": "jakarta",
        "layers": {"L1": True, "L2": True, "L3": True, "L4_full": True, "L4_partial": False},
        "next_hint": None,
        "scaffold": "/tmp/out/customer",
    }
    proc = _make_proc_result(json.dumps(payload), returncode=0)

    with patch("subprocess.run", return_value=proc):
        result = run("jakarta", "/tmp/out/customer")

    assert isinstance(result, FullTestJobResult)
    assert result.label == "풀테스트 그린"
    assert result.lane == "jakarta"
    assert result.green is True
    assert result.error is None
    assert result.returncode == 0
    assert result.layers["L4_full"] is True


# ---------------------------------------------------------------------------
# test_runner_handles_timeout
# ---------------------------------------------------------------------------

def test_runner_handles_timeout(monkeypatch) -> None:
    """subprocess.TimeoutExpired → error field set, returncode=-2."""
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=[], timeout=600)):
        result = run("jakarta", "/tmp/out/customer")

    assert result.error is not None
    assert "timeout" in result.error.lower()
    assert result.returncode == -2
    assert result.green is False


# ---------------------------------------------------------------------------
# test_runner_sets_no_learnlog_env
# ---------------------------------------------------------------------------

def test_runner_sets_no_learnlog_env(monkeypatch) -> None:
    """subprocess.run is called with FULLTEST_NO_LEARNLOG=1 in env."""
    payload = {
        "label": "풀테스트 그린",
        "lane": "jakarta",
        "layers": {"L4_full": True},
        "next_hint": None,
        "scaffold": None,
    }
    proc = _make_proc_result(json.dumps(payload), returncode=0)

    captured_env = {}

    def _fake_run(*args, **kwargs):
        captured_env.update(kwargs.get("env", {}))
        return proc

    with patch("subprocess.run", side_effect=_fake_run):
        run("jakarta", "/tmp/out/customer")

    assert captured_env.get("FULLTEST_NO_LEARNLOG") == "1"
