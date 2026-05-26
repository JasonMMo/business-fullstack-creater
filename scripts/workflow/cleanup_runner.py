"""Layer-4 cleanup orchestration: Stop java + git restore + remove overlay."""
from __future__ import annotations
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

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
    command: Optional[list[str]] = None
    cwd: Optional[Path] = None
    shell: bool = False
    python: Optional[Callable[[], tuple[bool, str]]] = None

@dataclass
class StepResult:
    label: str
    ok: bool
    detail: str


def _remove_untracked_mappers(runner: str, *, repo: Optional[Path] = None) -> tuple[bool, str]:
    """Delete *-mapper.xml files that git does not track under the runner's mappers dir.

    Why Python-side instead of PowerShell pipeline: prior implementation used a
    ScriptBlock subexpression `(git ls-files ... ; $LASTEXITCODE) -ne 0` inside
    `Where-Object`. PowerShell collects every expression in a ScriptBlock body
    as output stream — git stdout + $LASTEXITCODE became an array, and comparing
    an array to 0 yields an element-wise filter rather than a boolean predicate.
    Single `git ls-files` here + set-membership lookup is unambiguous.
    """
    nexacro_repo = repo if repo is not None else NEXACRO_REPO
    overlay_xml = nexacro_repo / "samples" / "runners" / runner / "src" / "main" / "resources" / "mybatis" / "mappers"
    if not overlay_xml.exists():
        return True, "no mappers dir"
    mappers = sorted(overlay_xml.glob("*-mapper.xml"))
    if not mappers:
        return True, "no mapper files"
    rel_dir = f"samples/runners/{runner}/src/main/resources/mybatis/mappers/"
    try:
        p = subprocess.run(
            ["git", "-C", str(nexacro_repo), "ls-files", rel_dir],
            capture_output=True, text=True, timeout=30,
        )
    except Exception as e:
        return False, f"git exception: {e}"
    if p.returncode != 0:
        return False, (p.stderr or "git ls-files failed").strip()[:120]
    repo_root = nexacro_repo.resolve()
    tracked = {(repo_root / line.strip()).resolve()
               for line in p.stdout.splitlines() if line.strip()}
    removed = 0
    errors: list[str] = []
    for m in mappers:
        if m.resolve() in tracked:
            continue
        try:
            m.unlink()
            removed += 1
        except Exception as e:
            errors.append(f"{m.name}: {e}")
    if errors:
        return False, f"removed={removed}, errors={'; '.join(errors)}"[:120]
    return True, (f"removed {removed} untracked" if removed else "all tracked")


def plan_steps(lane: str) -> list[Step]:
    runner = resolve_runner(lane)
    jdk_match = "jdk-17" if "17" in runner else "jdk-8"
    runner_dir = NEXACRO_REPO / "samples" / "runners" / runner
    # Overlay (live_overlay.py:263) writes Java sources under com.example.<slug>/.
    # The runner's own sources live under com.nexacro.uiadapter.* and must NEVER
    # be touched by cleanup — git restore handles tracked-file revert; this step
    # only removes the untracked overlay tree at com.example/.
    overlay_pkg = runner_dir / "src" / "main" / "java" / "com" / "example"
    return [
        Step(f"Stop java ({jdk_match})",
             ["powershell", "-NoProfile", "-Command",
              f"Get-Process java -EA SilentlyContinue | Where-Object {{ $_.Path -like '*{jdk_match}*' }} | Stop-Process -Force"]),
        Step(f"git restore {runner}",
             ["git", "-C", str(NEXACRO_REPO), "restore", f"samples/runners/{runner}/"]),
        Step(f"Remove overlay dirs ({runner})",
             ["powershell", "-NoProfile", "-Command",
              f"if (Test-Path '{overlay_pkg}') {{ Remove-Item -Path '{overlay_pkg}' -Recurse -Force }}"]),
        Step(f"Remove untracked mappers ({runner})",
             python=(lambda r=runner: _remove_untracked_mappers(r))),
    ]

def _execute_step(step: Step) -> StepResult:
    if step.python is not None:
        try:
            ok, detail = step.python()
            return StepResult(step.label, ok, detail[:120])
        except Exception as e:
            return StepResult(step.label, False, f"exception: {e}")
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
