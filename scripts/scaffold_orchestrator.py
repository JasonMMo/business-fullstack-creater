# scripts/scaffold_orchestrator.py
import pathlib, subprocess, sys, shutil, time
from dataclasses import dataclass, field
from typing import Optional, List
from stage_paths import resolve_stage_paths


@dataclass
class ScaffoldArgs:
    domain: str
    domain_slug: str
    wiki_mode: Optional[str]            # "preset" | "wiki"
    preset: Optional[str]
    wiki_path: Optional[pathlib.Path]
    lane: str                            # "nexacro" | "vanilla"
    default_pattern: str                 # "D2" | "F1" | "C1"
    package: str
    out_dir: pathlib.Path
    creator_root: pathlib.Path
    stop_after_stage: int = 4            # for tests


@dataclass
class ScaffoldReport:
    stages_run: List[str] = field(default_factory=list)
    stage_durations_ms: dict = field(default_factory=dict)
    out_dir: Optional[pathlib.Path] = None


class StageFailure(Exception):
    pass


def _run(cmd, cwd, label):
    t0 = time.monotonic()
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    dur = int((time.monotonic() - t0) * 1000)
    if proc.returncode != 0:
        raise StageFailure(
            f"{label} failed (exit {proc.returncode})\n"
            f"cmd: {cmd}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return dur, proc.stdout


def _run_stage1(args, stage_paths, report):
    wiki_out = args.out_dir / "1-wiki"
    wiki_out.mkdir(parents=True, exist_ok=True)
    s1 = stage_paths.stage1
    if args.wiki_mode == "preset":
        dur1, _ = _run(
            [sys.executable, str(s1 / "scripts" / "rdb_index.py"),
             "init", str(wiki_out), "--preset", args.preset],
            cwd=s1, label="stage1.init",
        )
    elif args.wiki_mode == "wiki":
        if not args.wiki_path or not args.wiki_path.exists():
            raise StageFailure(f"wiki_path not found: {args.wiki_path}")
        if wiki_out.exists():
            shutil.rmtree(wiki_out)
        shutil.copytree(args.wiki_path, wiki_out)
        dur1 = 0
    else:
        raise ValueError("wiki_mode must be 'preset' or 'wiki'")
    dur2, _ = _run(
        [sys.executable, str(s1 / "scripts" / "rdb_index.py"),
         "compile", str(wiki_out)],
        cwd=s1, label="stage1.compile",
    )
    report.stages_run.append("stage1")
    report.stage_durations_ms["stage1"] = dur1 + dur2


def run_scaffold(args):
    if args.wiki_mode not in ("preset", "wiki"):
        raise ValueError("wiki_mode must be 'preset' or 'wiki'")
    args.out_dir = pathlib.Path(args.out_dir).resolve()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    stage_paths = resolve_stage_paths(args.creator_root)
    report = ScaffoldReport(out_dir=args.out_dir)

    _run_stage1(args, stage_paths, report)
    if args.stop_after_stage <= 1:
        return report
    # Stage 2/3/4 wired in later tasks
    return report
