"""scaffold_cli.py — CLI entry point for the 5-stage scaffold orchestrator.

Usage:
    python scripts/scaffold_cli.py --domain "주문관리" --package com.example.order \
        --out ./order-scaffold [--wiki-mode preset --preset 주문관리] [--lane nexacro] \
        [--default-pattern D2] [--stop-after-stage 5] \
        [--target-project <dir>] [--overlay-force]
"""
import argparse
import re
import sys
import pathlib


def derive_slug(domain: str) -> str:
    """Convert a domain name to a URL-safe slug.

    Rules: lowercase, spaces → hyphens, drop characters that are not
    alphanumeric or hyphens.
    """
    slug = domain.lower()
    slug = slug.replace(" ", "-")
    slug = re.sub(r"[^a-z0-9\-]", "", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "domain"


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="scaffold_cli",
        description="5-stage scaffold orchestrator: wiki → DDL → MyBatis → Nexacro → Overlay",
    )
    p.add_argument(
        "--domain",
        required=True,
        metavar="<name>",
        help="Domain name (e.g. '주문관리'). Used as human-readable label.",
    )
    p.add_argument(
        "--wiki-mode",
        choices=("preset", "wiki"),
        default="preset",
        dest="wiki_mode",
        help="Wiki input mode: 'preset' (use rdb-skill catalog) or 'wiki' (existing dir).",
    )
    p.add_argument(
        "--preset",
        metavar="<name>",
        default=None,
        help="Preset name (required when --wiki-mode=preset).",
    )
    p.add_argument(
        "--wiki",
        metavar="<path>",
        default=None,
        dest="wiki",
        help="Path to existing wiki directory (required when --wiki-mode=wiki).",
    )
    p.add_argument(
        "--lane",
        choices=("nexacro", "vanilla", "jakarta", "javax"),
        default="nexacro",
        help="Stage 3 lane (default: nexacro).",
    )
    p.add_argument(
        "--ui",
        choices=("nexacro", "react"),
        default="nexacro",
        help="Stage 5 UI overlay adapter (default: nexacro). 'react' emits frontend/src/api/*.ts fetch modules.",
    )
    p.add_argument(
        "--default-pattern",
        metavar="<pattern>",
        default=None,
        dest="default_pattern",
        help="Stage 4 default form pattern, e.g. D2, F1, C1 (optional).",
    )
    p.add_argument(
        "--package",
        required=True,
        metavar="<java.pkg>",
        help="Spring base package (e.g. com.example.order).",
    )
    p.add_argument(
        "--out",
        required=True,
        metavar="<dir>",
        dest="out",
        help="Output directory root.",
    )
    p.add_argument(
        "--stop-after-stage",
        type=int,
        choices=(1, 2, 3, 4, 5),
        default=5,
        dest="stop_after_stage",
        help="Stop after this stage number (default: 5).",
    )
    p.add_argument(
        "--target-project",
        metavar="<dir>",
        default=None,
        dest="target_project",
        help="Stage 5 overlay target root (base scaffold from /nexacro-fullstack-starter). Stage 5 is skipped when omitted.",
    )
    p.add_argument(
        "--overlay-force",
        action="store_true",
        dest="overlay_force",
        help="Allow Stage 5 overlay to overwrite existing files (creates .bak backups).",
    )
    p.add_argument(
        "--target-package-prefix",
        metavar="<java.pkg>",
        default="com.nexacro.uiadapter",
        dest="target_pkg_prefix",
        help=(
            "Stage 5 Java/XML target package prefix (default: com.nexacro.uiadapter). "
            "Source prefix is derived from --package (all segments except the last, "
            "which becomes the domain slug)."
        ),
    )
    p.add_argument(
        "--dialect",
        choices=("postgres", "hsqldb", "mysql"),
        default="postgres",
        help="Stage 2 SQL dialect (default: postgres). Use 'hsqldb' for in-DB test, 'mysql' for MySQL targets.",
    )
    p.add_argument(
        "--service-name",
        metavar="<PascalCase>",
        default=None,
        dest="service_name",
        help="Explicit nexacro service name (e.g. 'Order'). Auto-derived from --domain when omitted.",
    )
    return p


def main(argv=None):
    p = _build_parser()
    a = p.parse_args(argv)

    # Validate wiki-mode constraints
    if a.wiki_mode == "preset" and not a.preset:
        p.error("--wiki-mode=preset requires --preset <name>")
    if a.wiki_mode == "wiki" and not a.wiki:
        p.error("--wiki-mode=wiki requires --wiki <path>")

    # Derive slug. If non-ASCII domain collapses to the "domain" fallback, warn
    # that Stage 5 will pick up its slug from --package's last segment instead.
    domain_slug = derive_slug(a.domain)
    if domain_slug == "domain" and a.domain != "domain":
        print(
            f"WARN: derive_slug({a.domain!r}) → 'domain' (non-ASCII fallback). "
            f"Stage 5 overlay will use --package last segment "
            f"({a.package.split('.')[-1]!r}) as the actual domain slug.",
            file=sys.stderr,
        )

    # Resolve creator_root: parent of this script's parent directory
    creator_root = pathlib.Path(__file__).resolve().parent.parent

    # Build wiki_path if wiki mode
    wiki_path = pathlib.Path(a.wiki).resolve() if a.wiki else None

    # Import here so PYTHONPATH only needs to include scripts/
    from scaffold_orchestrator import ScaffoldArgs, run_scaffold, StageFailure

    out_dir = pathlib.Path(a.out)
    report_path = out_dir / "scaffold-report.md"

    args = ScaffoldArgs(
        domain=a.domain,
        domain_slug=domain_slug,
        wiki_mode=a.wiki_mode,
        preset=a.preset,
        wiki_path=wiki_path,
        lane=a.lane,
        default_pattern=a.default_pattern or "D2",
        package=a.package,
        out_dir=out_dir,
        creator_root=creator_root,
        stop_after_stage=a.stop_after_stage,
        dialect=a.dialect,
        service_name=a.service_name,
        target_project=pathlib.Path(a.target_project).resolve() if a.target_project else None,
        overlay_force=a.overlay_force,
        target_pkg_prefix=a.target_pkg_prefix,
        ui=a.ui,
    )

    try:
        run_scaffold(args)
    except StageFailure as exc:
        stage_label = str(exc).split("\n")[0]
        print(f"FAILED at {stage_label}. See {report_path}", file=sys.stderr)
        sys.exit(1)

    print(f"OK. Report: {report_path}")


if __name__ == "__main__":
    main()
