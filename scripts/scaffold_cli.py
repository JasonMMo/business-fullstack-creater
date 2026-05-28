"""scaffold_cli.py — CLI entry point for the 5-stage scaffold orchestrator.

Usage:
    python scripts/scaffold_cli.py --domain "주문관리" --package com.example.order \
        --out ./order-scaffold [--wiki-mode preset --preset 주문관리] [--lane nexacro] \
        [--default-pattern D2] [--stop-after-stage 5] \
        [--target-project <dir>] [--overlay-force]
"""
import argparse
import os
import re
import sys
import pathlib


def derive_slug(domain: str) -> str:
    """Convert a domain name to a URL-safe slug.

    Rules: lowercase, spaces → hyphens, drop characters that are not
    alphanumeric or hyphens. Returns "domain" when input collapses to empty
    (e.g., Korean-only input). Use `resolve_slug()` for CLI flow with explicit
    `--slug` + `--package` fallback (R1).
    """
    slug = domain.lower()
    slug = slug.replace(" ", "-")
    slug = re.sub(r"[^a-z0-9\-]", "", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "domain"


def _sanitize_slug(s: str) -> str:
    """ASCII-clean slug sanitization without the 'domain' fallback."""
    s = s.lower().replace(" ", "-")
    s = re.sub(r"[^a-z0-9\-]", "", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s


def resolve_slug(
    domain: str,
    *,
    explicit_slug: str | None = None,
    package_fallback: str | None = None,
) -> tuple[str, str]:
    """R1 (서비스 리뷰 2026-05-26): explicit slug 우선 → ASCII 도메인 자동 derive →
    package 마지막 segment fallback. 무음 'domain' 폴백 제거.

    Returns (slug, source) where source ∈ {'explicit', 'derived', 'package-fallback'}.
    Raises ValueError when no usable slug can be produced.
    """
    if explicit_slug:
        s = _sanitize_slug(explicit_slug)
        if not s:
            raise ValueError(f"--slug {explicit_slug!r} sanitizes to empty after ASCII cleanup")
        return s, "explicit"
    derived = _sanitize_slug(domain)
    if derived:
        return derived, "derived"
    if package_fallback:
        s = _sanitize_slug(package_fallback)
        if s:
            return s, "package-fallback"
    raise ValueError(
        f"cannot derive slug from domain={domain!r} (non-ASCII); pass --slug=<ascii-name>"
    )


def resolve_ui_default(ui: str | None, lane: str) -> str:
    """Growth-59: lane-aware --ui default.

    Explicit --ui always wins. When omitted, vanilla lane defaults to 'react'
    (pure REST, no nexacro XFDL forms); all other lanes default to 'nexacro'.
    """
    if ui is not None:
        return ui
    return "react" if lane == "vanilla" else "nexacro"


_ENV_VAR_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _interpolate_env(value):
    """Replace ${VAR} occurrences with os.environ[VAR]. Missing vars stay literal."""
    if isinstance(value, str):
        return _ENV_VAR_RE.sub(lambda m: os.environ.get(m.group(1), m.group(0)), value)
    if isinstance(value, dict):
        return {k: _interpolate_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_interpolate_env(v) for v in value]
    return value


def load_customer_profile(slug, *, profiles_root=None):
    """Growth-63: load profiles/<slug>.yaml.

    - Enforces top-level `version: 1` (G-62; matches preset-catalog / blueprint).
    - Verifies `customer.slug` matches the requested slug (catches typo/rename).
    - Interpolates ${ENV_VAR} placeholders against os.environ.
    Returns the parsed dict, or None when slug is None.
    Raises ValueError on missing file, malformed YAML, or version mismatch.
    """
    if slug is None:
        return None
    import yaml  # local import: only needed when feature is exercised
    if profiles_root is None:
        profiles_root = pathlib.Path(__file__).resolve().parent.parent / "profiles"
    profiles_root = pathlib.Path(profiles_root)
    path = profiles_root / f"{slug}.yaml"
    if not path.exists():
        raise ValueError(
            f"customer profile not found: {path}\n"
            f"available: {sorted(p.stem for p in profiles_root.glob('*.yaml')) if profiles_root.exists() else '(profiles/ missing)'}"
        )
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"customer profile root must be a mapping: {path}")
    version = data.get("version")
    if version != 1:
        raise ValueError(
            f"customer profile {path.name}: unsupported version: {version!r} (expected 1)"
        )
    declared_slug = (data.get("customer") or {}).get("slug")
    if declared_slug and declared_slug != slug:
        raise ValueError(
            f"customer profile {path.name}: customer.slug={declared_slug!r} "
            f"does not match filename slug={slug!r}"
        )
    return _interpolate_env(data)


def _profile_get(profile, *path, default=None):
    """Safe nested lookup. _profile_get(profile, 'mybatis', 'base_package')."""
    if profile is None:
        return default
    cur = profile
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return default if cur is None else cur


def resolve_with_profile(cli_value, profile, *path, default=None):
    """CLI > profile > default. CLI wins whenever it is not None."""
    if cli_value is not None:
        return cli_value
    return _profile_get(profile, *path, default=default)


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
        "--slug",
        metavar="<ascii-name>",
        default=None,
        help=(
            "Explicit URL-safe slug (ASCII only). Recommended when --domain is "
            "non-ASCII (e.g., Korean). When omitted and --domain has no ASCII chars, "
            "falls back to --package's last segment (R1 service review 2026-05-26)."
        ),
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
        default=None,
        help=(
            "Stage 3 lane (default resolution: --customer-profile defaults.lane → 'nexacro'). "
            "Middle-layer display labels: "
            "nexacro=jakarta-for-nexacro (MyBatis + jakarta, NexacroN-compatible), "
            "vanilla, jakarta, javax."
        ),
    )
    p.add_argument(
        "--ui",
        choices=("nexacro", "react"),
        default=None,
        help=(
            "Stage 5 UI overlay adapter. Lane-aware default when omitted: "
            "--lane vanilla → 'react', other lanes → 'nexacro'. "
            "'react' emits frontend/src/api/*.ts fetch modules."
        ),
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
        required=False,
        default=None,
        metavar="<java.pkg>",
        help=(
            "Spring base package (e.g. com.example.order). "
            "Required unless --customer-profile supplies mybatis.base_package."
        ),
    )
    p.add_argument(
        "--customer-profile",
        metavar="<slug>",
        default=None,
        dest="customer_profile",
        help=(
            "Growth-63: load profiles/<slug>.yaml and apply as defaults across "
            "Stage 1-5 (6th axis). Explicit CLI flags always override profile values. "
            "Profile must have version: 1 and customer.slug matching <slug>."
        ),
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
        default=None,
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
        default=None,
        help=(
            "Stage 2 SQL dialect (default resolution: --customer-profile ddl.dialect → 'postgres'). "
            "Use 'hsqldb' for in-DB test, 'mysql' for MySQL targets."
        ),
    )
    p.add_argument(
        "--uia-namespace",
        choices=("jakarta", "spring"),
        default=None,
        dest="uia_namespace",
        help=(
            "Growth-47: nexacro-uiadapter Spring flavor package segment for Stage 3 "
            "(lane=nexacro only). 'jakarta' (default) → Spring 6 / jakarta.servlet "
            "(boot-jdk17-jakarta runner). 'spring' → Spring 5 / javax.servlet "
            "(boot-jdk8-javax runner). Mismatch causes ParamDataSet/NexacroResult "
            "symbol-not-found at L4 build (T-NexacroUiaPkg-javax trap)."
        ),
    )
    p.add_argument(
        "--service-name",
        metavar="<PascalCase>",
        default=None,
        dest="service_name",
        help="Explicit nexacro service name (e.g. 'Order'). Auto-derived from --domain when omitted.",
    )
    # ---- Growth-16: standalone shell controls ---------------------------
    p.add_argument(
        "--shell-mode",
        choices=("none", "MDI", "SDI"),
        default="none",
        dest="shell_mode",
        help=(
            "Standalone nexacro shell variant rendered into <target>/nxui/packageN/. "
            "'none' (default) preserves existing overlay-only behavior. "
            "'MDI' or 'SDI' renders frame_main/mdi|sdi/left/top/login + typedefinition.xml + packageN.xadl."
        ),
    )
    p.add_argument(
        "--nexacrolib-from",
        metavar="<dir>",
        default=None,
        dest="nexacrolib_from",
        help=(
            "When set, copies the given nexacrolib tree into <target>/nxui/nexacrolib/. "
            "Only honored together with --shell-mode."
        ),
    )
    p.add_argument(
        "--shell-app-id",
        metavar="<name>",
        default=None,
        dest="shell_app_id",
        help="branding.app_id passed to the shell adapter (profile overlay.shell_app_id → 'packageN').",
    )
    p.add_argument(
        "--auth-mode",
        choices=("none", "session", "jwt", "oauth2"),
        default=None,
        dest="auth_mode",
        help=(
            "Growth-21a: SHELL Spring Security auth bundle. "
            "'none' (default) emits no auth classes. "
            "'session' = form-login + BCrypt + JDBC UserDetailsService. "
            "'jwt' = session + JwtTokenProvider (Bearer). "
            "'oauth2' = jwt + OAuth2 starter + JIT provisioning."
        ),
    )
    p.add_argument(
        "--auth-lane",
        choices=("jakarta", "javax"),
        default=None,
        dest="auth_lane",
        help=(
            "Growth-23: SHELL auth bundle servlet flavor. "
            "'jakarta' (default) = Spring Security 6 + jakarta.servlet. "
            "'javax' = Spring Security 5 + javax.servlet. "
            "Ignored when --auth-mode=none."
        ),
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

    # Growth-63: load customer profile (6th axis) — CLI > profile > default.
    try:
        profile = load_customer_profile(a.customer_profile)
    except ValueError as exc:
        p.error(str(exc))
    if profile is not None:
        print(
            f"INFO: customer-profile={a.customer_profile!r} loaded "
            f"(customer.display={(profile.get('customer') or {}).get('display')!r})",
            file=sys.stderr,
        )

    # Resolve --package: CLI > profile.mybatis.base_package > error.
    # When the profile supplies only the base package (e.g. com.acme), append
    # the domain ASCII slug as the final segment (acme + customer → com.acme.customer).
    package = a.package
    if package is None:
        base_pkg = _profile_get(profile, "mybatis", "base_package")
        if base_pkg:
            # Derive last segment from --slug if explicit, else from a sanitized domain.
            tail = a.slug or _sanitize_slug(a.domain)
            if not tail:
                p.error(
                    "cannot derive package tail: --domain is non-ASCII and --slug not set. "
                    "Pass --slug or --package."
                )
            package = f"{base_pkg}.{tail}"
    if package is None:
        p.error("--package is required (or supply mybatis.base_package via --customer-profile)")

    # R1 (서비스 리뷰 2026-05-26): explicit --slug > ASCII derive > --package last segment.
    pkg_last = package.split(".")[-1] if package else None
    try:
        domain_slug, slug_source = resolve_slug(
            a.domain, explicit_slug=a.slug, package_fallback=pkg_last,
        )
    except ValueError as exc:
        p.error(str(exc))
    if slug_source == "package-fallback":
        print(
            f"INFO: domain={a.domain!r} is non-ASCII; using slug={domain_slug!r} "
            f"from --package last segment. Pass --slug=<name> to override.",
            file=sys.stderr,
        )
    elif slug_source == "explicit":
        print(f"INFO: using explicit --slug={domain_slug!r}", file=sys.stderr)

    # CLI > profile > hardcoded default for every remaining knob.
    lane = resolve_with_profile(a.lane, profile, "defaults", "lane", default="nexacro")
    dialect = resolve_with_profile(a.dialect, profile, "ddl", "dialect", default="postgres")
    default_pattern = resolve_with_profile(
        a.default_pattern, profile, "nexacro", "default_pattern", default="D2",
    )
    target_pkg_prefix = resolve_with_profile(
        a.target_pkg_prefix, profile, "overlay", "target_pkg_prefix",
        default="com.nexacro.uiadapter",
    )
    shell_app_id = resolve_with_profile(
        a.shell_app_id, profile, "overlay", "shell_app_id", default="packageN",
    )
    auth_mode = resolve_with_profile(a.auth_mode, profile, "auth", "mode", default="none")
    auth_lane = resolve_with_profile(a.auth_lane, profile, "auth", "lane", default="jakarta")
    uia_namespace = resolve_with_profile(
        a.uia_namespace, profile, "mybatis", "uia_namespace", default="jakarta",
    )

    # Resolve creator_root: parent of this script's parent directory
    creator_root = pathlib.Path(__file__).resolve().parent.parent

    # Build wiki_path if wiki mode
    wiki_path = pathlib.Path(a.wiki).resolve() if a.wiki else None

    # Import here so PYTHONPATH only needs to include scripts/
    from scaffold_orchestrator import ScaffoldArgs, run_scaffold, StageFailure

    out_dir = pathlib.Path(a.out)
    report_path = out_dir / "scaffold-report.md"

    # Growth-59: lane-aware --ui default. Profile defaults.ui beats lane heuristic.
    ui_from_profile = _profile_get(profile, "defaults", "ui")
    if a.ui is not None:
        ui_resolved = a.ui
    elif ui_from_profile is not None:
        ui_resolved = ui_from_profile
    else:
        ui_resolved = resolve_ui_default(a.ui, lane)
    if a.ui is None:
        print(
            f"INFO: --ui not specified; defaulting to {ui_resolved!r} for --lane {lane}",
            file=sys.stderr,
        )

    args = ScaffoldArgs(
        domain=a.domain,
        domain_slug=domain_slug,
        wiki_mode=a.wiki_mode,
        preset=a.preset,
        wiki_path=wiki_path,
        lane=lane,
        default_pattern=default_pattern,
        package=package,
        out_dir=out_dir,
        creator_root=creator_root,
        stop_after_stage=a.stop_after_stage,
        dialect=dialect,
        service_name=a.service_name,
        target_project=pathlib.Path(a.target_project).resolve() if a.target_project else None,
        overlay_force=a.overlay_force,
        target_pkg_prefix=target_pkg_prefix,
        ui=ui_resolved,
        shell_mode=a.shell_mode,
        nexacrolib_from=(
            pathlib.Path(a.nexacrolib_from).resolve() if a.nexacrolib_from else None
        ),
        shell_app_id=shell_app_id,
        auth_mode=auth_mode,
        auth_lane=auth_lane,
        uia_namespace=uia_namespace,
        customer_profile=profile,
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
