"""
tests/web/test_scaffold_runner.py — Coverage for M1 S1.2 scaffold_runner adapter.

All tests mock subprocess.run — scaffold_cli.py is NEVER actually invoked.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import List
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_REPORT = """\
# Scaffold Report — 고객관리

- domain: `고객관리` (slug: `customer`)
- wiki_mode: `preset`
- lane: `jakarta`
- dialect: `hsqldb`

## Stages
- stage1: OK (217 ms)
- stage2: OK (283 ms)
- stage3: OK (341 ms)
- stage4: OK (304 ms)
- stage5: SKIPPED (no --target-project)

## 다음 단계
- DDL: out/customer/2-ddl
"""


def _make_completed(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
    """Return a mock that looks like subprocess.CompletedProcess."""
    mock = MagicMock()
    mock.returncode = returncode
    mock.stdout = stdout
    mock.stderr = stderr
    return mock


# ---------------------------------------------------------------------------
# 1. Pydantic validation
# ---------------------------------------------------------------------------

def test_scaffold_request_validates_required_fields():
    """domain and slug are required; omitting either raises ValidationError."""
    from pydantic import ValidationError
    from web.adapters.scaffold_runner import ScaffoldRequest

    with pytest.raises(ValidationError):
        ScaffoldRequest(slug="customer")       # missing domain

    with pytest.raises(ValidationError):
        ScaffoldRequest(domain="고객관리")     # missing slug

    # Both present → should succeed
    req = ScaffoldRequest(domain="고객관리", slug="customer")
    assert req.domain == "고객관리"
    assert req.slug == "customer"
    assert req.dialect == "hsqldb"             # default
    assert req.lane == "jakarta"               # default


# ---------------------------------------------------------------------------
# 2. argv construction
# ---------------------------------------------------------------------------

def test_run_invokes_scaffold_cli_with_expected_args(monkeypatch, tmp_path):
    """subprocess.run is called with required CLI flags."""
    from web.adapters import scaffold_runner
    from web.adapters.scaffold_runner import ScaffoldRequest, run

    captured: List[list] = []

    def fake_run(argv, **kwargs):
        captured.append(argv)
        # Write a minimal report so the adapter can proceed
        # run() computes out_dir = creater_root / "out" / slug
        out_dir = tmp_path / "out" / "customer"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "scaffold-report.md").write_text(_FAKE_REPORT, encoding="utf-8")
        return _make_completed(returncode=0, stdout="OK. Report: scaffold-report.md")

    # Point settings to tmp_path so out_dir resolves correctly
    fake_settings = SimpleNamespace(
        creater_root=str(tmp_path),
        scaffold_cli_path="scripts/scaffold_cli.py",
        scaffold_out_dir="out/",
    )
    monkeypatch.setattr(scaffold_runner, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(subprocess, "run", fake_run)

    req = ScaffoldRequest(domain="고객관리", slug="customer", preset="고객관리")
    run(req)

    assert len(captured) == 1
    argv = captured[0]
    assert "--domain" in argv
    assert "고객관리" in argv
    assert "--slug" in argv
    assert "customer" in argv
    assert "--lane" in argv
    assert "--dialect" in argv
    assert "--default-pattern" in argv
    assert "--out" in argv


# ---------------------------------------------------------------------------
# 3. customer_profile flag — present
# ---------------------------------------------------------------------------

def test_run_passes_customer_profile_when_set(monkeypatch, tmp_path):
    """When customer_profile='acme', --customer-profile acme is in argv."""
    from web.adapters import scaffold_runner
    from web.adapters.scaffold_runner import ScaffoldRequest, run

    captured: List[list] = []

    def fake_run(argv, **kwargs):
        captured.append(argv)
        out_dir = tmp_path / "out" / "acme"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "scaffold-report.md").write_text(_FAKE_REPORT.replace("customer", "acme"), encoding="utf-8")
        return _make_completed(returncode=0)

    fake_settings = SimpleNamespace(
        creater_root=str(tmp_path),
        scaffold_cli_path="scripts/scaffold_cli.py",
        scaffold_out_dir="out/",
    )
    monkeypatch.setattr(scaffold_runner, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(subprocess, "run", fake_run)

    req = ScaffoldRequest(domain="고객관리", slug="acme", customer_profile="acme")
    run(req)

    argv = captured[0]
    assert "--customer-profile" in argv
    idx = argv.index("--customer-profile")
    assert argv[idx + 1] == "acme"


# ---------------------------------------------------------------------------
# 4. customer_profile flag — absent
# ---------------------------------------------------------------------------

def test_run_omits_customer_profile_when_none(monkeypatch, tmp_path):
    """When customer_profile is None, --customer-profile must NOT appear in argv."""
    from web.adapters import scaffold_runner
    from web.adapters.scaffold_runner import ScaffoldRequest, run

    captured: List[list] = []

    def fake_run(argv, **kwargs):
        captured.append(argv)
        out_dir = tmp_path / "out" / "order"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "scaffold-report.md").write_text(_FAKE_REPORT.replace("customer", "order"), encoding="utf-8")
        return _make_completed(returncode=0)

    fake_settings = SimpleNamespace(
        creater_root=str(tmp_path),
        scaffold_cli_path="scripts/scaffold_cli.py",
        scaffold_out_dir="out/",
    )
    monkeypatch.setattr(scaffold_runner, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(subprocess, "run", fake_run)

    req = ScaffoldRequest(domain="주문관리", slug="order", customer_profile=None)
    run(req)

    assert "--customer-profile" not in captured[0]


# ---------------------------------------------------------------------------
# 5. Report parsing
# ---------------------------------------------------------------------------

def test_run_parses_report_stages(monkeypatch, tmp_path):
    """A well-formed scaffold-report.md is parsed into 5 StageResult entries."""
    from web.adapters import scaffold_runner
    from web.adapters.scaffold_runner import ScaffoldRequest, run

    def fake_run(argv, **kwargs):
        out_dir = tmp_path / "out" / "customer"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "scaffold-report.md").write_text(_FAKE_REPORT, encoding="utf-8")
        return _make_completed(returncode=0, stdout="OK.")

    fake_settings = SimpleNamespace(
        creater_root=str(tmp_path),
        scaffold_cli_path="scripts/scaffold_cli.py",
        scaffold_out_dir="out/",
    )
    monkeypatch.setattr(scaffold_runner, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(subprocess, "run", fake_run)

    req = ScaffoldRequest(domain="고객관리", slug="customer", preset="고객관리")
    result = run(req)

    assert result.success is True
    assert result.returncode == 0
    assert len(result.stages) == 5

    statuses = {s.name: s.status for s in result.stages}
    assert statuses["stage1"] == "OK"
    assert statuses["stage2"] == "OK"
    assert statuses["stage3"] == "OK"
    assert statuses["stage4"] == "OK"
    assert statuses["stage5"] == "SKIPPED"

    # Duration should be parsed for OK stages
    stage1 = next(s for s in result.stages if s.name == "stage1")
    assert stage1.duration_ms == 217

    # SKIPPED note
    stage5 = next(s for s in result.stages if s.name == "stage5")
    assert stage5.note is not None
    assert "target-project" in stage5.note


# ---------------------------------------------------------------------------
# 6. Missing report + non-zero exit
# ---------------------------------------------------------------------------

def test_run_handles_missing_report_gracefully(monkeypatch, tmp_path):
    """Non-zero returncode with no report → success=False, stages empty."""
    from web.adapters import scaffold_runner
    from web.adapters.scaffold_runner import ScaffoldRequest, run

    def fake_run(argv, **kwargs):
        # Return error without writing report
        return _make_completed(returncode=1, stderr="stage1 exploded")

    fake_settings = SimpleNamespace(
        creater_root=str(tmp_path),
        scaffold_cli_path="scripts/scaffold_cli.py",
        scaffold_out_dir="out/",
    )
    monkeypatch.setattr(scaffold_runner, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(subprocess, "run", fake_run)

    req = ScaffoldRequest(domain="고객관리", slug="customer")
    result = run(req)

    assert result.success is False
    assert result.returncode == 1
    assert result.stages == []
    assert "exploded" in result.stderr
    assert result.raw_report is None


# ---------------------------------------------------------------------------
# 7. Timeout
# ---------------------------------------------------------------------------

def test_run_handles_timeout(monkeypatch, tmp_path):
    """TimeoutExpired → success=False, informative stderr, returncode=-1."""
    from web.adapters import scaffold_runner
    from web.adapters.scaffold_runner import ScaffoldRequest, run

    def fake_run(argv, **kwargs):
        raise subprocess.TimeoutExpired(cmd=argv, timeout=300)

    fake_settings = SimpleNamespace(
        creater_root=str(tmp_path),
        scaffold_cli_path="scripts/scaffold_cli.py",
        scaffold_out_dir="out/",
    )
    monkeypatch.setattr(scaffold_runner, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(subprocess, "run", fake_run)

    req = ScaffoldRequest(domain="고객관리", slug="customer")
    result = run(req)

    assert result.success is False
    assert result.returncode == -1
    assert result.stages == []
    assert "timed out" in result.stderr
    assert "customer" in result.stderr
