"""Layer-4 cleanup orchestration: Stop java + git restore + remove overlay."""
from __future__ import annotations
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# Support both `python -m scripts.workflow.cleanup_runner` (package import)
# and `python scripts/workflow/cleanup_runner.py` (direct script invocation).
try:
    from .lane_runner_map import resolve_runner
except ImportError:
    _root = str(Path(__file__).resolve().parents[2])
    if _root not in sys.path:
        sys.path.insert(0, _root)
    from scripts.workflow.lane_runner_map import resolve_runner

NEXACRO_REPO = Path(r"D:\AI\workspace\nexacroN-fullstack")

@dataclass
class Step:
    label: str
    command: list[str]
    cwd: Path | None = None
    shell: bool = False

@dataclass
class StepResult:
    label: str
    ok: bool
    detail: str

def plan_steps(lane: str) -> list[Step]:
    runner = resolve_runner(lane)
    jdk_match = "jdk-17" if "17" in runner else "jdk-8"
    runner_dir = NEXACRO_REPO / "samples" / "runners" / runner
    overlay_pkg = runner_dir / "src" / "main" / "java" / "com" / "nexacro" / "uiadapter"
    overlay_xml = runner_dir / "src" / "main" / "resources" / "mybatis" / "mappers"
    return [
        Step(f"Stop java ({jdk_match})",
             ["powershell", "-NoProfile", "-Command",
              f"Get-Process java -EA SilentlyContinue | Where-Object {{ $_.Path -like '*{jdk_match}*' }} | Stop-Process -Force"]),
        Step(f"git restore {runner}",
             ["git", "-C", str(NEXACRO_REPO), "restore", f"samples/runners/{runner}/"]),
        Step(f"Remove overlay dirs ({runner})",
             ["powershell", "-NoProfile", "-Command",
              f"Get-ChildItem -Path '{overlay_pkg}' -Directory -EA SilentlyContinue | "
              f"Where-Object {{ $_.Name -notin @('mapper','config','common') }} | "
              f"Remove-Item -Recurse -Force"]),
        Step(f"Remove untracked mappers ({runner})",
             ["powershell", "-NoProfile", "-Command",
              f"Get-ChildItem -Path '{overlay_xml}' -Filter '*-mapper.xml' -EA SilentlyContinue | "
              f"Where-Object {{ (git -C '{NEXACRO_REPO}' ls-files --error-unmatch $_.FullName 2>$null; $LASTEXITCODE) -ne 0 }} | "
              f"Remove-Item -Force"]),
    ]

def _execute_step(step: Step) -> StepResult:
    try:
        p = subprocess.run(step.command, capture_output=True, text=True, timeout=60)
        if p.returncode == 0:
            return StepResult(step.label, True, (p.stdout or "OK").strip()[:120])
        return StepResult(step.label, False, (p.stderr or p.stdout).strip()[:120])
    except Exception as e:
        return StepResult(step.label, False, f"exception: {e}")

def run(lane: str) -> list[StepResult]:
    return [_execute_step(s) for s in plan_steps(lane)]

def format_report(results: list[StepResult]) -> str:
    width = max(len(r.label) for r in results)
    lines = [f"{'Step':<{width}}    Result", f"{'-'*width}    ------"]
    for r in results:
        flag = "OK" if r.ok else "FAIL"
        lines.append(f"{r.label:<{width}}    {flag} ({r.detail})")
    return "\n".join(lines)

if __name__ == "__main__":
    lane = sys.argv[1] if len(sys.argv) > 1 else "jakarta"
    results = run(lane)
    print(format_report(results))
    sys.exit(0 if all(r.ok for r in results) else 1)
