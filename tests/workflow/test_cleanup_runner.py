import subprocess
from unittest.mock import patch, MagicMock
import pytest
from scripts.workflow import cleanup_runner

def test_plan_steps_for_jakarta_lane():
    steps = cleanup_runner.plan_steps("jakarta")
    labels = [s.label for s in steps]
    assert "Stop java (jdk-17)" in labels
    assert any("boot-jdk17-jakarta" in s.label for s in steps)

def test_plan_steps_unknown_lane_raises():
    with pytest.raises(ValueError):
        cleanup_runner.plan_steps("kotlin")

def test_run_reports_each_step_outcome(monkeypatch):
    monkeypatch.setattr(cleanup_runner, "_execute_step",
                        lambda s: cleanup_runner.StepResult(s.label, ok=True, detail="OK"))
    report = cleanup_runner.run("jakarta")
    assert all(r.ok for r in report)
    assert len(report) >= 3

def test_run_failed_step_does_not_short_circuit(monkeypatch):
    def fake(s):
        return cleanup_runner.StepResult(s.label, ok=("Stop" not in s.label),
                                          detail="fake-fail" if "Stop" in s.label else "ok")
    monkeypatch.setattr(cleanup_runner, "_execute_step", fake)
    report = cleanup_runner.run("jakarta")
    failed = [r for r in report if not r.ok]
    assert len(failed) == 1
    assert "Stop" in failed[0].label
    assert len(report) >= 3


# --- Growth-54: cleanup_runner PowerShell quoting trap fix ---

def _make_mappers_layout(tmp_path, runner, *, files):
    mappers = tmp_path / "samples" / "runners" / runner / "src" / "main" / "resources" / "mybatis" / "mappers"
    mappers.mkdir(parents=True)
    for name in files:
        (mappers / name).write_text("<xml/>", encoding="utf-8")
    return mappers


def test_remove_untracked_mappers_keeps_tracked_deletes_untracked(tmp_path, monkeypatch):
    runner = "boot-jdk17-jakarta"
    mappers = _make_mappers_layout(tmp_path, runner,
                                   files=["customer-mapper.xml", "address-mapper.xml", "board-mapper.xml"])
    tracked_rel = f"samples/runners/{runner}/src/main/resources/mybatis/mappers/customer-mapper.xml"

    fake = MagicMock(return_value=subprocess.CompletedProcess(
        args=[], returncode=0, stdout=tracked_rel + "\n", stderr=""
    ))
    monkeypatch.setattr(cleanup_runner.subprocess, "run", fake)

    ok, detail = cleanup_runner._remove_untracked_mappers(runner, repo=tmp_path)
    assert ok is True
    assert (mappers / "customer-mapper.xml").exists(), "tracked file must be preserved"
    assert not (mappers / "address-mapper.xml").exists(), "untracked file must be removed"
    assert not (mappers / "board-mapper.xml").exists(), "untracked file must be removed"
    assert "removed 2" in detail


def test_remove_untracked_mappers_all_tracked_no_op(tmp_path, monkeypatch):
    runner = "boot-jdk17-jakarta"
    mappers = _make_mappers_layout(tmp_path, runner, files=["customer-mapper.xml"])
    tracked_rel = f"samples/runners/{runner}/src/main/resources/mybatis/mappers/customer-mapper.xml"

    fake = MagicMock(return_value=subprocess.CompletedProcess(
        args=[], returncode=0, stdout=tracked_rel + "\n", stderr=""
    ))
    monkeypatch.setattr(cleanup_runner.subprocess, "run", fake)

    ok, detail = cleanup_runner._remove_untracked_mappers(runner, repo=tmp_path)
    assert ok is True
    assert (mappers / "customer-mapper.xml").exists()
    assert detail == "all tracked"


def test_remove_untracked_mappers_missing_dir_is_pass(tmp_path):
    ok, detail = cleanup_runner._remove_untracked_mappers("boot-jdk17-jakarta", repo=tmp_path)
    assert ok is True
    assert detail == "no mappers dir"


def test_remove_untracked_mappers_git_failure_surfaces(tmp_path, monkeypatch):
    runner = "boot-jdk17-jakarta"
    _make_mappers_layout(tmp_path, runner, files=["address-mapper.xml"])
    fake = MagicMock(return_value=subprocess.CompletedProcess(
        args=[], returncode=128, stdout="", stderr="fatal: not a git repository"
    ))
    monkeypatch.setattr(cleanup_runner.subprocess, "run", fake)

    ok, detail = cleanup_runner._remove_untracked_mappers(runner, repo=tmp_path)
    assert ok is False
    assert "not a git repository" in detail
    # On failure no destructive action
    assert (tmp_path / "samples" / "runners" / runner / "src" / "main" / "resources"
            / "mybatis" / "mappers" / "address-mapper.xml").exists()


def test_plan_steps_wires_python_callable_for_remove_mappers():
    steps = cleanup_runner.plan_steps("jakarta")
    mapper_steps = [s for s in steps if s.label.startswith("Remove untracked mappers")]
    assert len(mapper_steps) == 1
    s = mapper_steps[0]
    assert s.python is not None, "step must use Python callable (not PowerShell pipeline)"
    assert s.command is None, "command must be None when python hook is set"
