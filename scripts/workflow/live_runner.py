"""Live runner — start jakarta runner via java -jar, poll was.log for ready signal.

The runner is a Spring Boot fat-jar produced by `mvn -q package` in
`<runner>/target/`. We launch it with the system `java`, redirect stdout to a
log file, and poll that file for the "Started Application in N.NNN seconds"
signal (or known failure markers) before the live probe runs.

`stop_runner` is idempotent and uses terminate → wait → kill.
"""
from __future__ import annotations
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

# Regex avoids accidentally matching "Starting Application" or recovery messages.
_READY_RE = re.compile(r"Started\s+\w+\s+in\s+[\d.]+\s+seconds")
_FAIL_MARKERS = (
    "APPLICATION FAILED TO START",
    "Error starting ApplicationContext",
)


@dataclass
class LiveRunnerHandle:
    process: Optional[subprocess.Popen]
    log_path: Path
    port: int


def _read_log(log_path: Path) -> str:
    try:
        return log_path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def wait_until_ready(
    handle: LiveRunnerHandle,
    timeout_sec: float = 120.0,
    poll_interval: float = 0.5,
) -> bool:
    """Poll the log for the ready signal. Returns False on timeout or known failure."""
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        text = _read_log(handle.log_path)
        if any(marker in text for marker in _FAIL_MARKERS):
            return False
        if _READY_RE.search(text):
            return True
        if handle.process is not None and handle.process.poll() is not None:
            # Process exited before signalling ready — give the log one more read.
            text = _read_log(handle.log_path)
            return bool(_READY_RE.search(text))
        time.sleep(poll_interval)
    return False


def start_runner_command(
    cmd: Sequence[str],
    log_path: Path,
    port: int,
) -> LiveRunnerHandle:
    """Launch `cmd`, redirect stdout/stderr to log_path, return handle."""
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_fh = open(log_path, "wb")
    proc = subprocess.Popen(
        list(cmd),
        stdout=log_fh,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
    )
    return LiveRunnerHandle(process=proc, log_path=log_path, port=port)


def _find_runner_jar(runner_dir: Path) -> Path:
    target = runner_dir / "target"
    if not target.exists():
        raise FileNotFoundError(f"No target/ directory in {runner_dir}")
    jars = [p for p in target.glob("*.jar") if not p.name.endswith(".original")]
    if not jars:
        raise FileNotFoundError(f"No runner jar found under {target}")
    # Prefer SNAPSHOT-style fat jar; fall back to first.
    snapshot = [p for p in jars if "SNAPSHOT" in p.name]
    return snapshot[0] if snapshot else jars[0]


def start_runner(
    runner_dir: Path,
    java_exe: str = "java",
    port: int = 8080,
    log_path: Optional[Path] = None,
) -> LiveRunnerHandle:
    """Locate the runner jar in <runner_dir>/target/ and launch it."""
    runner_dir = Path(runner_dir)
    jar = _find_runner_jar(runner_dir)
    log = Path(log_path) if log_path is not None else runner_dir / "was.log"
    cmd = [java_exe, f"-Dserver.port={port}", "-jar", str(jar)]
    return start_runner_command(cmd, log_path=log, port=port)


def stop_runner(handle: LiveRunnerHandle, timeout_sec: float = 10.0) -> None:
    """Terminate the process gracefully, then kill if necessary. Idempotent."""
    proc = handle.process
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=timeout_sec)
    except subprocess.TimeoutExpired:
        proc.kill()
        try:
            proc.wait(timeout=timeout_sec)
        except subprocess.TimeoutExpired:
            pass


def kill_port_listener(port: int) -> tuple[bool, str]:
    """Kill whatever process listens on *port* (JDK-version-agnostic).

    Growth-85: cleanup 의 jdk-path 필터가 jdk 버전 불일치 좀비를 놓쳐
    L4 repackage 가 jar 잠금으로 영구 실패하던 문제 해결. 포트 점유 프로세스를
    직접 종료한다. 리스너가 없으면 no-op (성공).

    Windows PowerShell Get-NetTCPConnection 기반. powershell 없는 환경에서는
    (True, 'none') 반환으로 안전하게 no-op.
    """
    ps = (
        f"$c = Get-NetTCPConnection -LocalPort {port} -State Listen "
        f"-ErrorAction SilentlyContinue; "
        f"if ($c) {{ $c.OwningProcess | Sort-Object -Unique | ForEach-Object "
        f"{{ Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }}; 'killed' }}"
        f" else {{ 'none' }}"
    )
    try:
        p = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=30,
        )
        return True, (p.stdout or "").strip() or "ok"
    except Exception as e:
        return False, str(e)
