# scripts/scaffold_orchestrator.py
import pathlib, subprocess, sys, shutil, time, re
from dataclasses import dataclass, field
from typing import Optional, List
from stage_paths import resolve_stage_paths
import stage5_overlay


@dataclass
class ScaffoldArgs:
    domain: str
    domain_slug: str
    wiki_mode: Optional[str]            # "preset" | "wiki"
    preset: Optional[str]
    wiki_path: Optional[pathlib.Path]
    lane: str                            # "nexacro" | "vanilla" | "jakarta" | "javax"
    default_pattern: str                 # "D2" | "F1" | "C1"
    package: str
    out_dir: pathlib.Path
    creator_root: pathlib.Path
    stop_after_stage: int = 5            # for tests (default 5 to include stage5)
    dialect: str = "postgres"            # E3: "postgres" | "hsqldb" | "mysql"
    service_name: Optional[str] = None   # E5: explicit PascalCase service name; auto-derived if None
    target_project: Optional[pathlib.Path] = None   # F: Stage 5 target overlay root (None → skip)
    overlay_force: bool = False                     # F: allow .bak overwrite during overlay
    target_pkg_prefix: str = "com.nexacro.uiadapter"  # G(v0.4.2): Stage 5 Java/XML target package prefix
    ui: str = "nexacro"                             # H4 (v0.5): Stage 5 UI overlay adapter ("nexacro" | "react")
    # Growth-16 (P3): standalone shell controls
    shell_mode: str = "none"                        # "none" | "MDI" | "SDI"
    nexacrolib_from: Optional[pathlib.Path] = None  # copies into target_dir/nxui/nexacrolib/
    shell_app_id: str = "packageN"                  # branding.app_id passed to shell adapter
    # Growth-21a-2: SHELL Spring Security + Nexacro auth bundle gate.
    #   "none"    → no auth classes (default; Growth-16~20 goldens stay bit-identical)
    #   "session" → 8-class form-login bundle (BCrypt + JDBC UserDetailsService)
    #   "jwt"     → session + JwtTokenProvider; success handler emits Bearer
    #   "oauth2"  → jwt + OAuth2 starter (Growth-21a-3 fills in deps + login UI)
    auth_mode: str = "none"
    # Growth-23: SHELL auth bundle servlet/Spring-Security flavor.
    #   "jakarta" → Spring Security 6 + jakarta.servlet (default; matches Growth-21a)
    #   "javax"   → Spring Security 5 + javax.servlet (no silent fallback)
    auth_lane: str = "jakarta"
    # Growth-47: nexacro-uiadapter Spring flavor for Stage 3 (lane=nexacro only).
    #   "jakarta" → com.nexacro.uiadapter.jakarta.core.* (Spring 6, boot-jdk17-jakarta)
    #   "spring"  → com.nexacro.uiadapter.spring.core.*  (Spring 5, boot-jdk8-javax)
    # Mismatch causes L4 ParamDataSet/NexacroResult symbol-not-found
    # (T-NexacroUiaPkg-javax trap).
    uia_namespace: str = "jakarta"
    # Growth-63: parsed customer profile (6th axis). None when --customer-profile not used.
    # Schema in profiles/_README.md; loader: scaffold_cli.load_customer_profile.
    customer_profile: Optional[dict] = None


@dataclass
class ScaffoldReport:
    stages_run: List[str] = field(default_factory=list)
    stage_durations_ms: dict = field(default_factory=dict)
    out_dir: Optional[pathlib.Path] = None
    overlay_report: Optional[dict] = None


class StageFailure(Exception):
    pass


def _derive_service_pascal(domain_slug: str) -> str:
    """snake_case slug → PascalCase service name. 'sales_order' → 'SalesOrder'."""
    parts = [p for p in re.split(r"[_\-\s]+", domain_slug) if p]
    return "".join(p[:1].upper() + p[1:] for p in parts) or "Default"


# Middle-layer display labels. Internal lane codes stay as-is (templates,
# package paths, CLI choices), but human-facing surfaces show the
# clarified label — "nexacro" lane is MyBatis-driven + jakarta, *not* JPA.
_LANE_DISPLAY = {
    "nexacro": "jakarta-for-nexacro",
    "vanilla": "vanilla",
    "jakarta": "jakarta",
    "javax":   "javax",
}


def display_lane(lane: str) -> str:
    return _LANE_DISPLAY.get(lane, lane)


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
         str(bp), "--out", str(ddl_out), "--dialect", args.dialect],
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
    seed_dir = args.out_dir / "2-ddl" / "seed"
    cmd = [
        sys.executable, str(s3 / "scripts" / "compile.py"),
        "compile",
        "--blueprint", str(bp),
        "--ddl-dir", str(ddl_dir),
        "--out", str(mybatis_out),
        "--lane", args.lane,
        "--package", args.package,
        "--project-root-pkg", args.target_pkg_prefix,
        "--uia-namespace", args.uia_namespace,
    ]
    # E4: pass --seed-dir only when Stage 2 actually emitted seed files
    if seed_dir.exists() and any(seed_dir.iterdir()):
        cmd += ["--seed-dir", str(seed_dir)]
    dur, _ = _run(cmd, cwd=s3, label="stage3.compile")
    report.stages_run.append("stage3")
    report.stage_durations_ms["stage3"] = dur


def _run_stage4(args, stage_paths, report):
    # Growth-58 T-Stage4-VanillaReject: Stage 4 is nexacro XFDL form gen.
    # For --lane vanilla, Stage 3 emits version=2 REST-flavored endpoints.json
    # that Stage 4's endpoints_loader rejects with "N002 unsupported version: 2".
    # Vanilla has no XFDL forms — skip cleanly so users don't need --stop-after-stage 3.
    if args.lane == "vanilla":
        print(
            "[stage4] skipped: vanilla lane is pure REST — no nexacro XFDL forms to generate",
            file=sys.stderr,
        )
        report.stages_run.append("stage4-skipped-vanilla")
        return

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
    # E5: derive service_name from domain_slug when not explicit
    service_name = args.service_name or _derive_service_pascal(args.domain_slug)
    cmd += ["--service-name", service_name]
    dur, _ = _run(cmd, cwd=s4, label="stage4.compile")
    report.stages_run.append("stage4")
    report.stage_durations_ms["stage4"] = dur


def _copy_nexacrolib(src: pathlib.Path, target_dir: pathlib.Path) -> int:
    """Copy <src> into <target_dir>/nxui/nexacrolib/. Returns file count."""
    src = pathlib.Path(src).resolve()
    if not src.exists():
        raise StageFailure(f"--nexacrolib-from path not found: {src}")
    dest = target_dir / "nxui" / "nexacrolib"
    dest.mkdir(parents=True, exist_ok=True)
    count = 0
    for src_file in src.rglob("*"):
        if src_file.is_dir():
            continue
        rel = src_file.relative_to(src)
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, out)
        count += 1
    return count


def _run_stage5(args, stage_paths, report):
    if args.target_project is None and args.shell_mode == "none":
        report.stages_run.append("stage5-skipped")
        return
    target = pathlib.Path(args.target_project).resolve() if args.target_project else None
    if target is None:
        raise StageFailure("--shell-mode requires --target-project")
    # For shell-mode, the target may be a fresh project root; create if missing
    if args.shell_mode != "none":
        target.mkdir(parents=True, exist_ok=True)
    elif not target.exists():
        raise StageFailure(f"--target-project does not exist: {target}")
    # Load blueprint entities
    import yaml as _yaml
    bp_path = args.out_dir / "1-wiki" / "_blueprint.yaml"
    data = _yaml.safe_load(bp_path.read_text(encoding="utf-8"))
    entities = data.get("entities", []) if isinstance(data, dict) else []

    # ----- Growth-16: optional shell pass before per-domain overlay -----
    if args.shell_mode != "none":
        nexacro_skill_root = (
            stage_paths.stage4 / ".claude" / "skills"
            / "karpathy-rdb-nexacro" / "patterns"
        )
        try:
            t0s = time.monotonic()
            shell_report = stage5_overlay.run_overlay(
                ui="nexacro-shell",
                out_dir=args.out_dir,
                target_dir=target,
                domain_slug=args.package.split(".")[-1],
                domain_label=args.domain,
                service_pascal=args.service_name or _derive_service_pascal(
                    args.package.split(".")[-1]
                ),
                blueprint_entities=entities,
                overlay_force=args.overlay_force,
                shell_variant=args.shell_mode,
                shell_branding={"app_id": args.shell_app_id},
                nexacro_skill_root=nexacro_skill_root,
                target_pkg_prefix=args.target_pkg_prefix,
                source_pkg_prefix=".".join(args.package.split(".")[:-1]) or "com.example",
                maven_group_id=getattr(args, "maven_group_id", None) or args.target_pkg_prefix,
                maven_artifact_id=getattr(args, "maven_artifact_id", None),
                maven_version=getattr(args, "maven_version", None) or "0.1.0-SNAPSHOT",
                dialect=args.dialect,
                auth_mode=args.auth_mode,
                auth_lane=args.auth_lane,
            )
            shell_dur = int((time.monotonic() - t0s) * 1000)
        except RuntimeError as exc:
            raise StageFailure(f"stage5 shell conflict: {exc}") from exc
        report.overlay_report = shell_report
        report.stage_durations_ms["stage5-shell"] = shell_dur
        if args.nexacrolib_from is not None:
            copied = _copy_nexacrolib(args.nexacrolib_from, target)
            report.stage_durations_ms["stage5-nexacrolib"] = copied
        # Shell-only run (no Stage 3/4 outputs yet) → record and return
        domain_artifacts = (args.out_dir / "3-mybatis").exists() or (
            args.out_dir / "4-nexacro"
        ).exists()
        if not domain_artifacts:
            report.stages_run.append("stage5")
            return
    # Overlay slug must match Stage 3's actual Java package + Stage 4's xfdl
    # output, which derive from --package (e.g. com.example.order -> "order").
    # args.domain_slug can fall back to "domain" for non-ASCII domain names
    # (e.g. "주문관리"), so it is not safe for path/prefixid use here.
    overlay_slug = args.package.split(".")[-1]
    # G(v0.4.2): source prefix is everything before the slug, e.g.
    #   --package com.example.order   → source_pkg_prefix=com.example
    #   --package io.acme.svc.order   → source_pkg_prefix=io.acme.svc
    source_pkg_prefix = ".".join(args.package.split(".")[:-1]) or "com.example"
    service_pascal = args.service_name or _derive_service_pascal(overlay_slug)
    try:
        t0 = time.monotonic()
        overlay_result = stage5_overlay.run_overlay(
            ui=args.ui,
            out_dir=args.out_dir,
            target_dir=target,
            domain_slug=overlay_slug,
            domain_label=args.domain,
            service_pascal=service_pascal,
            blueprint_entities=entities,
            overlay_force=args.overlay_force,
            source_pkg_prefix=source_pkg_prefix,
            target_pkg_prefix=args.target_pkg_prefix,
            shell_mode=args.shell_mode,
            # Growth-24: react adapter uses auth_mode to gate LoginPage.tsx
            auth_mode=args.auth_mode,
            auth_lane=args.auth_lane,
        )
        dur = int((time.monotonic() - t0) * 1000)
    except RuntimeError as exc:
        raise StageFailure(f"stage5 conflict: {exc}") from exc
    report.overlay_report = overlay_result
    report.stages_run.append("stage5")
    report.stage_durations_ms["stage5"] = dur


def _write_report(args, report, failure=None):
    lines = [
        f"# Scaffold Report — {args.domain}",
        "",
        f"- domain: `{args.domain}` (slug: `{args.domain_slug}`)",
        f"- wiki_mode: `{args.wiki_mode}` "
        + (f"(preset=`{args.preset}`)" if args.wiki_mode == "preset"
           else f"(wiki=`{args.wiki_path}`)"),
        f"- lane: `{args.lane}` (middle: {display_lane(args.lane)})",
        f"- dialect: `{args.dialect}`",
        f"- default_pattern: `{args.default_pattern}`",
        f"- service_name: `{args.service_name or _derive_service_pascal(args.domain_slug)}`",
        f"- package: `{args.package}`",
        f"- out_dir: `{args.out_dir}`",
        f"- target_project: `{args.target_project or '(none)'}`",
        f"- overlay_force: `{args.overlay_force}`",
        f"- ui: `{args.ui}`",
        "",
        "## Stages",
    ]
    for name in (
        "stage1", "stage2", "stage3",
        "stage4", "stage4-skipped-vanilla",
        "stage5", "stage5-skipped",
    ):
        if name in report.stages_run:
            if name == "stage5-skipped":
                lines.append(f"- stage5: SKIPPED (no --target-project)")
            elif name == "stage4-skipped-vanilla":
                lines.append(
                    "- stage4: SKIPPED (vanilla lane has no nexacro XFDL forms)"
                )
            else:
                lines.append(f"- {name}: OK ({report.stage_durations_ms.get(name, 0)} ms)")
    if failure:
        lines += ["", f"## FAILED: {failure[0]}", "", "```", failure[1], "```"]
    else:
        lines += [
            "", "## 다음 단계",
            f"- DDL: `{args.out_dir / '2-ddl'}`",
            f"- Spring (middle={display_lane(args.lane)}): `{args.out_dir / '3-mybatis'}`",
            f"- Nexacro forms (default={args.default_pattern}): "
            f"`{args.out_dir / '4-nexacro'}`",
        ]
    if report.overlay_report is not None:
        ov = report.overlay_report
        lines += [
            "",
            "## Stage 5 overlay",
            f"- java_copied: {ov.get('java_copied', 0)}",
            f"- resources_copied: {ov.get('resources_copied', 0)}",
            f"- xfdl_copied: {ov.get('xfdl_copied', 0)}",
            f"- renamed_imports: {ov.get('renamed_imports', 0)}",
            f"- backed_up: {ov.get('backed_up', 0)}",
            f"- typedef_added: {ov.get('typedef_added', False)}",
            f"- menu_warning: {ov.get('menu_warning')}",
        ]
        menu_warning = ov.get("menu_warning")
        if menu_warning is not None:
            lines += ["", "```", str(menu_warning), "```"]
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
        (_run_stage5, "stage5"),
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
