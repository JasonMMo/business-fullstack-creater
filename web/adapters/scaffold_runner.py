"""
web/adapters/scaffold_runner.py — Adapter between the FastAPI web layer and scaffold_cli.py.

Critical constraint: this module MUST NOT re-implement scaffold logic.
It MUST spawn scripts/scaffold_cli.py via subprocess so the 6-axis compounding
stays intact (enforced by G-69 guard in S1.8).
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel

from web.settings import get_settings


# ---------------------------------------------------------------------------
# Request / result models
# ---------------------------------------------------------------------------

class ScaffoldRequest(BaseModel):
    domain: str                                  # 한글 도메인명 e.g. "고객관리"
    slug: str                                    # ASCII slug e.g. "customer"
    dialect: str = "hsqldb"                      # hsqldb | postgres | mysql
    lane: str = "jakarta"                        # jakarta | javax | nexacro | vanilla
    default_pattern: str = "D2"                  # D2 | D3 | ...
    wiki_mode: str = "preset"                    # preset | wiki
    preset: Optional[str] = None                 # preset name when wiki_mode=preset
    customer_profile: Optional[str] = None       # profile slug, optional
    package: str = ""                            # Growth-85: Java 패키지명 (비우면 scaffold_cli 기본값)
    shell_mode: str = "none"                     # Growth-86: none|MDI|SDI — !=none 이면 shell 생성 → ops pack auto-emit


class StageResult(BaseModel):
    name: str                                    # stage1..stage5
    status: str                                  # OK | SKIPPED | FAIL
    duration_ms: Optional[int] = None
    note: Optional[str] = None                   # e.g. "(no --target-project)" for SKIPPED


class ScaffoldResult(BaseModel):
    success: bool
    slug: str
    out_dir: str                                 # absolute path string
    stages: List[StageResult]
    stdout: str
    stderr: str
    raw_report: Optional[str] = None             # markdown content of scaffold-report.md
    returncode: int
    lane: str = "jakarta"                        # Growth-83: fulltest_route 가 lane 을 읽기 위해 추가


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# Matches lines like:
#   - stage1: OK (217 ms)
#   - stage2: OK (283 ms)
#   - stage5: SKIPPED (no --target-project)
#   - stage3: FAIL (1234 ms) some note
_STAGE_RE = re.compile(
    r"^- (stage\d+): (OK|SKIPPED|FAIL)"
    r"(?:\s+\((\d+) ms\))?"   # optional duration group
    r"(?:\s+(.+))?$"          # optional note
)


def _parse_report(markdown: str) -> List[StageResult]:
    """Extract stage results from the ## Stages section of scaffold-report.md."""
    stages: List[StageResult] = []
    in_stages = False
    for line in markdown.splitlines():
        if line.strip() == "## Stages":
            in_stages = True
            continue
        if in_stages:
            if line.startswith("##"):
                break  # next section — stop
            m = _STAGE_RE.match(line.strip())
            if m:
                name, status, duration_raw, note = m.groups()
                stages.append(
                    StageResult(
                        name=name,
                        status=status,
                        duration_ms=int(duration_raw) if duration_raw else None,
                        note=note.strip() if note else None,
                    )
                )
    return stages


def _build_argv(
    request: ScaffoldRequest,
    *,
    cli_path: str,
    out_dir: Path,
) -> List[str]:
    """Build the subprocess argv list for scaffold_cli.py."""
    argv = [
        sys.executable,
        cli_path,
        "--domain", request.domain,
        "--slug", request.slug,
        "--dialect", request.dialect,
        "--lane", request.lane,
        "--default-pattern", request.default_pattern,
        "--wiki-mode", request.wiki_mode,
        "--out", str(out_dir),
    ]
    if request.preset is not None:
        argv += ["--preset", request.preset]
    if request.customer_profile is not None:
        argv += ["--customer-profile", request.customer_profile]
    if request.package:  # Growth-85: --package 전달 (비전문 사용자 자동 기본값은 라우트에서 채워줌)
        argv += ["--package", request.package]
    if request.shell_mode and request.shell_mode != "none":
        # Growth-86: shell 변형 생성 → <out>/shell/pom.xml → orchestrator 가 ops pack
        # 을 auto-emit (Growth-74). --target-project 을 <out>/shell 로 고정해
        # emit_ops_pack(shell_subdir="shell") 가 읽는 경로와 정렬한다. 이로써
        # IT담당자(M-Ops) 가 웹만으로 /domain/{id}/ops.zip 에 도달할 수 있다.
        argv += [
            "--shell-mode", request.shell_mode,
            "--target-project", str(out_dir / "shell"),
        ]
    return argv


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run(request: ScaffoldRequest, *, timeout_sec: int = 300) -> ScaffoldResult:
    """Spawn scaffold_cli.py and parse the resulting report.

    Pure function — no global state mutated. All I/O is via subprocess
    and the filesystem report written by scaffold_cli.py.
    """
    settings = get_settings()
    creater_root = Path(settings.creater_root)
    cli_path = settings.scaffold_cli_path  # relative to creater_root

    # Output directory: <creater_root>/out/<slug>
    out_dir = creater_root / "out" / request.slug

    argv = _build_argv(request, cli_path=cli_path, out_dir=out_dir)

    stdout_text = ""
    stderr_text = ""
    returncode = -1

    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=str(creater_root),
            timeout=timeout_sec,
        )
        stdout_text = result.stdout or ""
        stderr_text = result.stderr or ""
        returncode = result.returncode

    except subprocess.TimeoutExpired as exc:
        stdout_text = exc.output.decode("utf-8", errors="replace") if exc.output else ""
        stderr_text = (
            f"scaffold_cli.py timed out after {timeout_sec}s "
            f"(domain={request.domain!r}, slug={request.slug!r})"
        )
        return ScaffoldResult(
            success=False,
            slug=request.slug,
            out_dir=str(out_dir),
            stages=[],
            stdout=stdout_text,
            stderr=stderr_text,
            raw_report=None,
            returncode=-1,
        )

    except OSError as exc:
        stderr_text = (
            f"Failed to launch scaffold_cli.py: {exc} "
            f"(argv={argv!r})"
        )
        return ScaffoldResult(
            success=False,
            slug=request.slug,
            out_dir=str(out_dir),
            stages=[],
            stdout="",
            stderr=stderr_text,
            raw_report=None,
            returncode=-1,
        )

    # Read the report if it exists
    report_path = out_dir / "scaffold-report.md"
    raw_report: Optional[str] = None
    if report_path.exists():
        raw_report = report_path.read_text(encoding="utf-8")

    # Parse stages from the report
    stages: List[StageResult] = []
    if raw_report:
        stages = _parse_report(raw_report)

    # success = zero returncode AND no FAIL stage AND at least one stage parsed
    success = (
        returncode == 0
        and len(stages) > 0
        and all(s.status in ("OK", "SKIPPED") for s in stages)
    )

    return ScaffoldResult(
        success=success,
        slug=request.slug,
        out_dir=str(out_dir),
        stages=stages,
        stdout=stdout_text,
        stderr=stderr_text,
        raw_report=raw_report,
        returncode=returncode,
        lane=request.lane,
    )
