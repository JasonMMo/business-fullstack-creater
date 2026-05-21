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
