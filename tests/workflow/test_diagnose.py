"""Tests for diagnose.py — Growth-52 (2026-05-26).

Each check is isolated against a synthetic workspace under tmp_path so the
suite doesn't depend on the real sibling repos. CLI smoke verifies exit codes
and JSON output shape.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.workflow import diagnose
from scripts.workflow.diagnose import Check


def _make_workspace(tmp_path: Path) -> tuple[Path, Path]:
    """Build a fake workspace with all sibling repos present.

    Returns (workspace_root, creater_root).
    """
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    for dirname in diagnose.LAYER_REPOS.values():
        (workspace / dirname).mkdir()
    # rdb-skill INDEX.md with 14 fake domains
    idx_dir = (
        workspace
        / "andrej-karpathy-rdb-skill"
        / ".claude"
        / "skills"
        / "karpathy-rdb"
        / "presets"
    )
    idx_dir.mkdir(parents=True)
    body = "# Preset Catalog\n\n"
    for i in range(14):
        body += f"## 도메인{i}\n- 한 줄: example\n\n"
    body += "## 매칭 알고리즘\n\n1. ...\n"
    (idx_dir / "INDEX.md").write_text(body, encoding="utf-8")
    # creater root + learn-log
    creater_root = workspace / "business-fullstack-creater"
    creater_root.mkdir()
    (creater_root / "learn-log.md").write_text(
        "# learn-log\n\n## 0. Layer Ownership Card\n\n| 축 |\n|---|\n",
        encoding="utf-8",
    )
    # runners
    runners = workspace / "nexacroN-fullstack" / "samples" / "runners"
    runners.mkdir(parents=True)
    for name in diagnose.EXPECTED_RUNNERS:
        (runners / name).mkdir()
    return workspace, creater_root


def test_check_layer_repos_all_pass(tmp_path):
    workspace, _ = _make_workspace(tmp_path)
    results = diagnose.check_layer_repos(workspace)
    assert all(c.status == "PASS" for c in results)
    assert {c.name for c in results} == {
        f"layer/{axis}" for axis in diagnose.LAYER_REPOS
    }


def test_check_layer_repos_fail_when_missing(tmp_path):
    workspace = tmp_path / "empty"
    workspace.mkdir()
    results = diagnose.check_layer_repos(workspace)
    assert all(c.status == "FAIL" for c in results)
    # every failing check carries a recovery hint
    assert all(c.hint for c in results)


def test_check_preset_catalog_pass(tmp_path):
    workspace, _ = _make_workspace(tmp_path)
    c = diagnose.check_preset_catalog(workspace)
    assert c.status == "PASS"
    assert "14 domains" in c.detail


def test_check_preset_catalog_fail_when_index_missing(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    c = diagnose.check_preset_catalog(workspace)
    assert c.status == "FAIL"
    assert c.hint


def test_check_preset_catalog_warn_when_too_few(tmp_path):
    workspace, _ = _make_workspace(tmp_path)
    idx = (
        workspace
        / "andrej-karpathy-rdb-skill"
        / ".claude"
        / "skills"
        / "karpathy-rdb"
        / "presets"
        / "INDEX.md"
    )
    idx.write_text("# Catalog\n\n## one\n\n## 매칭\n", encoding="utf-8")
    c = diagnose.check_preset_catalog(workspace)
    assert c.status == "WARN"


def test_check_learn_log_pass(tmp_path):
    _, creater_root = _make_workspace(tmp_path)
    c = diagnose.check_learn_log(creater_root)
    assert c.status == "PASS"


def test_check_learn_log_warn_when_no_section_zero(tmp_path):
    creater_root = tmp_path / "creater"
    creater_root.mkdir()
    (creater_root / "learn-log.md").write_text("# log\n\n## 1. other\n", encoding="utf-8")
    c = diagnose.check_learn_log(creater_root)
    assert c.status == "WARN"


def test_check_learn_log_fail_when_missing(tmp_path):
    creater_root = tmp_path / "creater"
    creater_root.mkdir()
    c = diagnose.check_learn_log(creater_root)
    assert c.status == "FAIL"


def test_check_runners_pass_when_clean(tmp_path):
    workspace, _ = _make_workspace(tmp_path)
    results = diagnose.check_runners(workspace)
    assert all(c.status == "PASS" for c in results)


def test_check_runners_warn_when_stale_overlay(tmp_path):
    workspace, _ = _make_workspace(tmp_path)
    overlay = (
        workspace
        / "nexacroN-fullstack"
        / "samples"
        / "runners"
        / "boot-jdk17-jakarta"
        / "src"
        / "main"
        / "java"
        / "com"
        / "example"
    )
    overlay.mkdir(parents=True)
    results = diagnose.check_runners(workspace)
    stale = next(c for c in results if c.name == "runner/boot-jdk17-jakarta")
    assert stale.status == "WARN"
    assert "cleanup_runner" in stale.hint


def test_check_runners_fail_when_root_missing(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    results = diagnose.check_runners(workspace)
    assert len(results) == 1
    assert results[0].status == "FAIL"


def test_format_table_summary_lines():
    checks = [
        Check("a", "PASS", "ok"),
        Check("b", "WARN", "soft", hint="run x"),
        Check("c", "FAIL", "hard", hint="run y"),
    ]
    out = diagnose.format_table(checks)
    assert "OK" in out and "!" in out and "X" in out
    assert "run x" in out and "run y" in out
    assert "1 FAIL" in out


def test_format_table_all_pass():
    checks = [Check("a", "PASS"), Check("b", "PASS")]
    out = diagnose.format_table(checks)
    assert "All 2 checks PASS" in out


def test_format_table_empty():
    assert diagnose.format_table([]) == "(no checks ran)"


def test_main_exit_code_zero_when_no_fail(tmp_path, monkeypatch, capsys):
    workspace, creater_root = _make_workspace(tmp_path)
    monkeypatch.setattr(diagnose, "WORKSPACE", workspace)
    monkeypatch.setattr(diagnose, "CREATER_ROOT", creater_root)
    # Stub JDK to PASS to keep test deterministic across CI machines.
    monkeypatch.setattr(
        diagnose, "check_jdk", lambda: Check("jdk", "PASS", "stubbed")
    )
    rc = diagnose.main([])
    assert rc == 0


def test_main_exit_code_one_when_any_fail(tmp_path, monkeypatch, capsys):
    workspace = tmp_path / "empty"
    workspace.mkdir()
    creater_root = tmp_path / "creater"
    creater_root.mkdir()
    monkeypatch.setattr(diagnose, "WORKSPACE", workspace)
    monkeypatch.setattr(diagnose, "CREATER_ROOT", creater_root)
    monkeypatch.setattr(
        diagnose, "check_jdk", lambda: Check("jdk", "PASS", "stubbed")
    )
    rc = diagnose.main([])
    assert rc == 1


def test_main_json_output_shape(tmp_path, monkeypatch, capsys):
    workspace, creater_root = _make_workspace(tmp_path)
    monkeypatch.setattr(diagnose, "WORKSPACE", workspace)
    monkeypatch.setattr(diagnose, "CREATER_ROOT", creater_root)
    monkeypatch.setattr(
        diagnose, "check_jdk", lambda: Check("jdk", "PASS", "stubbed")
    )
    rc = diagnose.main(["--json"])
    captured = capsys.readouterr()
    assert rc == 0
    data = json.loads(captured.out)
    assert isinstance(data, list)
    assert all({"name", "status", "detail", "hint"} <= set(d) for d in data)
    assert any(d["name"] == "preset-catalog" for d in data)
