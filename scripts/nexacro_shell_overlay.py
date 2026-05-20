# scripts/nexacro_shell_overlay.py
"""Nexacro standalone shell overlay adapter (Growth-16).

Unlike `_nexacro_overlay_run` which *overlays* a domain onto an existing
nexacro-fullstack-starter base, this adapter renders the **whole project
shell** (frame_main/frame_mdi/frame_left/frame_top/frame_login +
typedefinition.xml + packageN.xadl) into `target_dir/nxui/packageN/`.

Inputs (kwargs):
    out_dir, target_dir, domain_slug, domain_label, service_pascal,
    blueprint_entities, overlay_force
    shell_variant: "MDI" | "SDI" | <custom-registered>
    shell_menu: list[dict] — entries with id/label/form_url/parent_id/level/sort
    shell_login: dict | None — {title, ...}
    shell_branding: dict | None — {brand_text, app_title}
    shell_frame_overrides: dict | None — {frame_name: pathlib.Path}
    shell_extra_services: list[dict] | None
    nexacro_skill_root: pathlib.Path | str — path to
        andrej-karpathy-rdb-nexacro/.claude/skills/karpathy-rdb-nexacro/patterns
    nexacro_global_root: pathlib.Path | str | None — optional global override
        catalog (priority: skill-local > global). Project-local overrides
        flow in via shell_frame_overrides directly.

Returns:
    {
      "shell_variant": str,
      "frames_rendered": list[str],   # relative paths under target_dir
      "typedef_rendered": str,
      "xadl_rendered": str,
      "menu_entries": int,
      "backed_up": list[str],
      "conflicts": list[str],
      "source": "bundled" | "global",
    }
"""
import pathlib
import sys
import shutil
from typing import Optional

import jinja2

# Ensure scripts/ next to this file is importable for sibling helpers
_THIS = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parent))

import ui_overlay_registry


def _load_resolve_shell(nexacro_skill_root: pathlib.Path):
    """Import resolve_shell from the nexacro repo's scripts/ dir.

    nexacro_skill_root = <repo>/.claude/skills/karpathy-rdb-nexacro/patterns
    parents: [0]=karpathy-rdb-nexacro, [1]=skills, [2]=.claude, [3]=<repo>
    """
    nx_scripts = (
        pathlib.Path(nexacro_skill_root).resolve().parents[3] / "scripts"
    )
    if str(nx_scripts) not in sys.path:
        sys.path.insert(0, str(nx_scripts))
    import importlib
    pl = importlib.import_module("pattern_loader")
    return pl.resolve_shell, pl.ShellNotFoundError


_FRAME_SUFFIX_CASING = {
    "main": "Main",
    "mdi": "MDI",
    "sdi": "SDI",
    "left": "Left",
    "top": "Top",
    "login": "Login",
}


def _frame_filename(template_key: str) -> str:
    """Map a frame template key (e.g. ``frame_mdi``) to the runtime filename
    stem (``frameMDI``). Variant acronyms are preserved verbatim so the
    rendered filename matches the ``work_frame`` references inside
    ``frameMain.xfdl`` — Linux WAR runtimes are case-sensitive and
    ``frameMdi.xfdl`` does NOT satisfy a ``frameMDI`` lookup.
    """
    parts = template_key.split("_")[1:]  # drop the leading "frame"
    pieces = [_FRAME_SUFFIX_CASING.get(p.lower(), p.capitalize()) for p in parts]
    return "frame" + "".join(pieces)


def _render(tpl_path: pathlib.Path, ctx: dict) -> str:
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(tpl_path.parent)),
        keep_trailing_newline=True,
        undefined=jinja2.StrictUndefined,
    )
    # Allow shared templates to reference each other; resolve by name
    return env.get_template(tpl_path.name).render(**ctx)


def _safe_backup(dest: pathlib.Path, report: dict) -> None:
    if dest.exists():
        bak = pathlib.Path(str(dest) + ".bak")
        if not bak.exists():
            shutil.copy2(dest, bak)
            report["backed_up"].append(str(bak))


def _derive_menu_items(
    shell_menu: list,
    blueprint_entities: list,
    domain_slug: str,
) -> list:
    """Use blueprint.shell.menu when provided, else auto-derive from entities."""
    if shell_menu:
        return sorted(
            shell_menu,
            key=lambda m: (m.get("sort", 9999), m.get("id", "")),
        )
    return [
        {
            "id": e["name"],
            "parent_id": "",
            "label": e.get("label_ko") or e["name"],
            "form_url": f"{domain_slug}::{e['name']}.xfdl",
            "level": 0,
            "sort": idx,
        }
        for idx, e in enumerate(blueprint_entities or [])
    ]


def _shell_overlay_run(
    *,
    out_dir,
    target_dir,
    domain_slug: str,
    domain_label: str,
    service_pascal: str,
    blueprint_entities: list,
    overlay_force: bool = False,
    # SHELL-specific
    shell_variant: str = "MDI",
    shell_menu: Optional[list] = None,
    shell_login: Optional[dict] = None,
    shell_branding: Optional[dict] = None,
    shell_frame_overrides: Optional[dict] = None,
    shell_extra_services: Optional[list] = None,
    nexacro_skill_root=None,
    nexacro_global_root=None,
    # Accept-and-ignore (signature parity with _nexacro_overlay_run)
    source_pkg_prefix: str = "com.example",
    target_pkg_prefix: str = "com.nexacro.uiadapter",
    # Growth-17b: Maven build artifacts
    maven_group_id: str = "com.example",
    maven_artifact_id: Optional[str] = None,
    maven_version: str = "0.1.0-SNAPSHOT",
    **_unused,
) -> dict:
    if nexacro_skill_root is None:
        raise ValueError(
            "nexacro_shell_overlay requires nexacro_skill_root pointing to "
            "andrej-karpathy-rdb-nexacro/.claude/skills/karpathy-rdb-nexacro/patterns"
        )

    target_dir = pathlib.Path(target_dir)
    pkg_dir = target_dir / "nxui" / "packageN"
    frame_dir = pkg_dir / "frame"

    resolve_shell, ShellNotFoundError = _load_resolve_shell(nexacro_skill_root)
    try:
        resolved = resolve_shell(
            shell_variant,
            bundled_root=nexacro_skill_root,
            global_root=nexacro_global_root,
            frame_overrides=shell_frame_overrides or {},
        )
    except ShellNotFoundError as exc:
        raise RuntimeError(f"SHELL pattern resolve failed: {exc}") from exc

    branding = shell_branding or {}
    login = shell_login or {}
    has_login = bool(login)
    menu_items = _derive_menu_items(
        shell_menu or [], blueprint_entities or [], domain_slug
    )

    artifact_id = maven_artifact_id or f"{domain_slug}-shell"
    ctx_common = {
        "title": branding.get("app_title", domain_label or "Application"),
        "brand_text": branding.get("brand_text", domain_label or "Application"),
        "menu_title": branding.get("menu_title", "메뉴"),
        "has_login": has_login,
        "login_title": login.get("title", "로그인"),
        "service_base_url": branding.get(
            "service_base_url", f"./services/{domain_slug}/"
        ),
        "extra_services": shell_extra_services or [],
        "app_id": branding.get("app_id", "packageN"),
        "work_frame": "frameMDI" if shell_variant == "MDI" else "frameSDI",
        "menu_items": menu_items,
        "domain_slug": domain_slug,
        "domain_label": domain_label,
        "shell_variant": shell_variant,
        "target_pkg_prefix": target_pkg_prefix,
        "source_pkg_prefix": source_pkg_prefix,
        "maven_group_id": maven_group_id,
        "maven_artifact_id": artifact_id,
        "maven_version": maven_version,
    }

    report: dict = {
        "shell_variant": shell_variant,
        "frames_rendered": [],
        "typedef_rendered": "",
        "xadl_rendered": "",
        "build_files_rendered": [],
        "menu_entries": len(menu_items),
        "backed_up": [],
        "conflicts": [],
        "source": resolved.source,
    }

    pkg_path = target_pkg_prefix.replace(".", "/")

    # Conflict scan
    targets: list[tuple[pathlib.Path, pathlib.Path, str]] = []
    for name, tpl in resolved.frames.items():
        # name → frame{Main|MDI|Left|Top|Login|SDI}.xfdl
        out_name = _frame_filename(name)
        targets.append((tpl, frame_dir / f"{out_name}.xfdl", "frame"))
    targets.append((resolved.typedef_template, pkg_dir / "typedefinition.xml", "typedef"))
    targets.append((resolved.xadl_template, pkg_dir / "packageN.xadl", "xadl"))
    for tpl, rel in resolved.build_files:
        rel_resolved = rel.replace("{pkg_path}", pkg_path)
        targets.append((tpl, target_dir / rel_resolved, "build"))

    if not overlay_force:
        for _tpl, dest, _kind in targets:
            if dest.exists():
                report["conflicts"].append(str(dest))
        if report["conflicts"]:
            raise RuntimeError(
                "nexacro-shell overlay would overwrite existing files "
                "(use --overlay-force):\n"
                + "\n".join(f"  - {p}" for p in report["conflicts"])
            )

    # Render
    pkg_dir.mkdir(parents=True, exist_ok=True)
    frame_dir.mkdir(parents=True, exist_ok=True)

    for tpl, dest, kind in targets:
        dest.parent.mkdir(parents=True, exist_ok=True)
        _safe_backup(dest, report)
        rendered = _render(tpl, ctx_common)
        dest.write_text(rendered, encoding="utf-8")
        rel = str(dest.relative_to(target_dir))
        if kind == "frame":
            report["frames_rendered"].append(rel)
        elif kind == "typedef":
            report["typedef_rendered"] = rel
        elif kind == "xadl":
            report["xadl_rendered"] = rel
        elif kind == "build":
            report["build_files_rendered"].append(rel)

    return report


# Register at import time
ui_overlay_registry.register("nexacro-shell", _shell_overlay_run)
