# scripts/scaffold_orchestrator.py
import pathlib, subprocess, sys, shutil, time, re
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


def _init_wiki_from_preset(preset_name: str, stage1_root: pathlib.Path,
                            wiki_out: pathlib.Path) -> None:
    """Expand a .seed.md preset into entity/concept profile.md files.

    The rdb_index CLI has only {lint,compile} subcommands; it has no 'init'
    command.  The skill's init workflow is LLM-driven.  For headless scaffold
    we reproduce the minimal file layout that rdb_index compile expects:

        <wiki_out>/entities/<name>/profile.md   ← YAML frontmatter + heading
        <wiki_out>/concepts/<name>/profile.md   ← YAML frontmatter + heading
        <wiki_out>/_schema.md                   ← boilerplate (may be empty)
    """
    import yaml as _yaml

    presets_dir = stage1_root / ".claude" / "skills" / "karpathy-rdb" / "presets"
    seed_file = presets_dir / f"{preset_name}.seed.md"
    if not seed_file.exists():
        raise StageFailure(
            f"Preset not found: {seed_file}\n"
            f"Available presets: {[p.stem.replace('.seed','') for p in presets_dir.glob('*.seed.md')]}"
        )

    seed_text = seed_file.read_text(encoding="utf-8")

    # Extract YAML code blocks: ```yaml ... ```
    blocks = re.findall(r"```yaml\n(.*?)```", seed_text, re.DOTALL)

    for block in blocks:
        try:
            fm = _yaml.safe_load(block)
        except Exception:
            continue
        if not isinstance(fm, dict):
            continue

        kind = fm.get("type", "")
        name = fm.get("name", "")
        if not name:
            continue

        if kind == "entity":
            dest = wiki_out / "entities" / name / "profile.md"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(
                f"---\n{_yaml.dump(fm, allow_unicode=True, sort_keys=False)}---\n\n# {name}\n",
                encoding="utf-8",
            )
        elif kind == "concept":
            dest = wiki_out / "concepts" / name / "profile.md"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(
                f"---\n{_yaml.dump(fm, allow_unicode=True, sort_keys=False)}---\n\n# {name}\n",
                encoding="utf-8",
            )

    # Write a minimal _schema.md with required frontmatter
    schema_md = wiki_out / "_schema.md"
    if not schema_md.exists():
        schema_md.write_text(
            f"---\ntype: schema\nversion: 1\nlocale: ko\nproject: {preset_name}\n---\n\n# {preset_name}\n",
            encoding="utf-8",
        )


def _run_stage1(args, stage_paths, report):
    wiki_out = args.out_dir / "1-wiki"
    wiki_out.mkdir(parents=True, exist_ok=True)
    s1 = stage_paths.stage1
    if args.wiki_mode == "preset":
        t0 = time.monotonic()
        _init_wiki_from_preset(args.preset, s1, wiki_out)
        dur1 = int((time.monotonic() - t0) * 1000)
    elif args.wiki_mode == "wiki":
        if not args.wiki_path or not args.wiki_path.exists():
            raise StageFailure(f"wiki_path not found: {args.wiki_path}")
        if wiki_out.exists():
            shutil.rmtree(wiki_out)
        shutil.copytree(args.wiki_path, wiki_out)
        dur1 = 0
    else:
        assert args.wiki_mode in ("preset", "wiki"), "unreachable: validated in run_scaffold()"
    dur2, _ = _run(
        [sys.executable, str(s1 / "scripts" / "rdb_index.py"),
         "compile", str(wiki_out)],
        cwd=s1, label="stage1.compile",
    )
    report.stages_run.append("stage1")
    report.stage_durations_ms["stage1"] = dur1 + dur2


def _run_stage2(args, stage_paths, report):
    ddl_out = args.out_dir / "2-ddl"
    ddl_out.mkdir(parents=True, exist_ok=True)
    s2 = stage_paths.stage2
    bp = args.out_dir / "1-wiki" / "_blueprint.yaml"
    dur, _ = _run(
        [sys.executable, str(s2 / "scripts" / "ddl_compile.py"),
         str(bp), "--out", str(ddl_out)],
        cwd=s2, label="stage2.ddl_compile",
    )
    report.stages_run.append("stage2")
    report.stage_durations_ms["stage2"] = dur


def _run_stage3(args, stage_paths, report):
    mybatis_out = args.out_dir / "3-mybatis"
    mybatis_out.mkdir(parents=True, exist_ok=True)
    s3 = stage_paths.stage3
    bp = args.out_dir / "1-wiki" / "_blueprint.yaml"
    # Stage 2 (ddl_gen) writes SQL files into a migrations/ subdirectory.
    # Stage 3 (karpathy-rdb-mybatis) expects the DDL files in --ddl-dir directly.
    ddl_dir = args.out_dir / "2-ddl" / "migrations"
    dur, _ = _run(
        [sys.executable, str(s3 / "scripts" / "compile.py"),
         "compile",
         "--blueprint", str(bp),
         "--ddl-dir", str(ddl_dir),
         "--out", str(mybatis_out),
         "--lane", args.lane,
         "--package", args.package],
        cwd=s3, label="stage3.compile",
    )
    report.stages_run.append("stage3")
    report.stage_durations_ms["stage3"] = dur


def _run_stage4(args, stage_paths, report):
    nexacro_out = args.out_dir / "4-nexacro"
    nexacro_out.mkdir(parents=True, exist_ok=True)
    s4 = stage_paths.stage4
    bp = args.out_dir / "1-wiki" / "_blueprint.yaml"
    eps = args.out_dir / "3-mybatis" / "endpoints.json"
    cmd = [
        sys.executable, str(s4 / "scripts" / "form_gen.py"),
        "compile",
        "--blueprint", str(bp),
        "--out", str(nexacro_out),
    ]
    if eps.exists():
        cmd += ["--endpoints", str(eps)]
    else:
        cmd += ["--infer-endpoints"]
    if args.default_pattern:
        cmd += ["--default-pattern", args.default_pattern]
    dur, _ = _run(cmd, cwd=s4, label="stage4.compile")
    report.stages_run.append("stage4")
    report.stage_durations_ms["stage4"] = dur


def _write_report(args, report, failure=None):
    lines = [
        f"# Scaffold Report — {args.domain}",
        "",
        f"- domain: `{args.domain}` (slug: `{args.domain_slug}`)",
        f"- wiki_mode: `{args.wiki_mode}` "
        + (f"(preset=`{args.preset}`)" if args.wiki_mode == "preset"
           else f"(wiki=`{args.wiki_path}`)"),
        f"- lane: `{args.lane}`",
        f"- default_pattern: `{args.default_pattern}`",
        f"- package: `{args.package}`",
        f"- out_dir: `{args.out_dir}`",
        "",
        "## Stages",
    ]
    for name in ("stage1", "stage2", "stage3", "stage4"):
        if name in report.stages_run:
            lines.append(f"- {name}: OK ({report.stage_durations_ms.get(name, 0)} ms)")
    if failure:
        lines += ["", f"## FAILED: {failure[0]}", "", "```", failure[1], "```"]
    else:
        lines += [
            "", "## 다음 단계",
            f"- DDL: `{args.out_dir / '2-ddl'}`",
            f"- Spring (lane={args.lane}): `{args.out_dir / '3-mybatis'}`",
            f"- Nexacro forms (default={args.default_pattern}): "
            f"`{args.out_dir / '4-nexacro'}`",
        ]
    (args.out_dir / "scaffold-report.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def run_scaffold(args):
    if args.wiki_mode not in ("preset", "wiki"):
        raise ValueError("wiki_mode must be 'preset' or 'wiki'")
    args.out_dir = pathlib.Path(args.out_dir).resolve()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    stage_paths = resolve_stage_paths(args.creator_root)
    report = ScaffoldReport(out_dir=args.out_dir)
    runners = [
        (_run_stage1, "stage1"),
        (_run_stage2, "stage2"),
        (_run_stage3, "stage3"),
        (_run_stage4, "stage4"),
    ]
    try:
        for i, (fn, name) in enumerate(runners, start=1):
            fn(args, stage_paths, report)
            if args.stop_after_stage <= i:
                break
    except StageFailure as e:
        next_stage = f"stage{len(report.stages_run) + 1}"
        _write_report(args, report, failure=(next_stage, str(e)))
        raise
    _write_report(args, report)
    return report
