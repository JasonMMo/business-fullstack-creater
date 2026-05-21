"""Tests for live_runner — process lifecycle + ready-signal poll on was.log."""
from __future__ import annotations
import sys
import textwrap
from pathlib import Path

import pytest

from scripts.workflow import live_runner


# ---------- wait_until_ready (pure log-based, no process needed) ----------

def test_wait_until_ready_returns_true_when_signal_present(tmp_path):
    log = tmp_path / "was.log"
    log.write_text(
        "Spring boot stuff...\n"
        "Started Application in 3.456 seconds (process running for 5)\n",
        encoding="utf-8",
    )
    handle = live_runner.LiveRunnerHandle(process=None, log_path=log, port=8080)
    assert live_runner.wait_until_ready(handle, timeout_sec=1.0, poll_interval=0.05) is True


def test_wait_until_ready_returns_false_on_timeout(tmp_path):
    log = tmp_path / "was.log"
    log.write_text("starting...\n", encoding="utf-8")
    handle = live_runner.LiveRunnerHandle(process=None, log_path=log, port=8080)
    assert live_runner.wait_until_ready(handle, timeout_sec=0.3, poll_interval=0.05) is False


def test_wait_until_ready_returns_false_on_failure_signal(tmp_path):
    log = tmp_path / "was.log"
    log.write_text(
        "...\nAPPLICATION FAILED TO START\nCaused by: BeanCreationException\n",
        encoding="utf-8",
    )
    handle = live_runner.LiveRunnerHandle(process=None, log_path=log, port=8080)
    assert live_runner.wait_until_ready(handle, timeout_sec=0.3, poll_interval=0.05) is False


def test_wait_until_ready_handles_missing_log_initially(tmp_path):
    """Log not present yet when polling starts — should wait, not crash."""
    log = tmp_path / "was.log"
    handle = live_runner.LiveRunnerHandle(process=None, log_path=log, port=8080)
    assert live_runner.wait_until_ready(handle, timeout_sec=0.2, poll_interval=0.05) is False


# ---------- start_runner_command + stop_runner (real subprocess) ----------

def _fake_app_script(tmp_path: Path, ready_line: str, delay_sec: float) -> Path:
    """Python script that mimics Spring Boot startup — prints ready line after delay."""
    script = tmp_path / "fake_app.py"
    script.write_text(
        textwrap.dedent(f"""
            import sys, time
            time.sleep({delay_sec})
            print({ready_line!r}, flush=True)
            # stay alive until killed
            try:
                while True:
                    time.sleep(0.5)
            except KeyboardInterrupt:
                sys.exit(0)
        """).strip(),
        encoding="utf-8",
    )
    return script


def test_start_runner_command_then_ready_then_stop(tmp_path):
    script = _fake_app_script(
        tmp_path,
        "Started Application in 0.123 seconds (process running for 0.5)",
        delay_sec=0.1,
    )
    log = tmp_path / "was.log"
    handle = live_runner.start_runner_command(
        [sys.executable, str(script)],
        log_path=log,
        port=8080,
    )
    try:
        assert handle.process is not None
        assert handle.process.poll() is None  # still running
        assert live_runner.wait_until_ready(handle, timeout_sec=5.0, poll_interval=0.1) is True
    finally:
        live_runner.stop_runner(handle, timeout_sec=5)
    assert handle.process.poll() is not None  # has exited


def test_stop_runner_is_idempotent(tmp_path):
    script = _fake_app_script(tmp_path, "Started Application in 0.0 seconds", delay_sec=0.0)
    log = tmp_path / "was.log"
    handle = live_runner.start_runner_command(
        [sys.executable, str(script)],
        log_path=log,
        port=8080,
    )
    live_runner.stop_runner(handle, timeout_sec=5)
    # second call must not raise
    live_runner.stop_runner(handle, timeout_sec=5)


# ---------- start_runner (high-level: locates jar in runner_dir/target/) ----------

def test_start_runner_raises_when_jar_missing(tmp_path):
    runner_dir = tmp_path / "runner"
    (runner_dir / "target").mkdir(parents=True)
    with pytest.raises(FileNotFoundError, match="jar"):
        live_runner.start_runner(runner_dir)


def test_start_runner_finds_jar(tmp_path, monkeypatch):
    runner_dir = tmp_path / "runner"
    (runner_dir / "target").mkdir(parents=True)
    fake_jar = runner_dir / "target" / "runner-boot-jdk17-jakarta-0.1.0-SNAPSHOT.jar"
    fake_jar.write_bytes(b"PK\x03\x04fake-jar")

    captured = {}

    def fake_popen_cmd(cmd, log_path, port):
        captured["cmd"] = cmd
        captured["log_path"] = log_path
        captured["port"] = port
        return live_runner.LiveRunnerHandle(process=None, log_path=log_path, port=port)

    monkeypatch.setattr(live_runner, "start_runner_command", fake_popen_cmd)
    handle = live_runner.start_runner(runner_dir, java_exe="java", port=8080)
    assert handle.port == 8080
    assert captured["cmd"][0] == "java"
    assert "-jar" in captured["cmd"]
    assert str(fake_jar) in captured["cmd"]
