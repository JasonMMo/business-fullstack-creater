# scripts/stage5_overlay.py
"""Stage 5 overlay orchestrator.

Copies 3-mybatis + 4-nexacro scaffold output onto the nexacro-fullstack-starter
target tree, applying Java package renames and injecting menu / typedef entries.

xml.etree is intentionally forbidden — use regex / string substitution only.
"""
import pathlib
import shutil
from typing import Optional

# Local imports (scripts/ must be on sys.path)
import menu_injector
import typedef_merger


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _rewrite_java(text: str, domain_slug: str) -> tuple[str, bool]:
    """Apply com.example.<slug> → com.nexacro.uiadapter.<slug> substitutions.

    Returns (new_text, changed).
    """
    old = text
    text = text.replace(
        f"package com.example.{domain_slug}",
        f"package com.nexacro.uiadapter.{domain_slug}",
    )
    text = text.replace(
        f"import com.example.{domain_slug}.",
        f"import com.nexacro.uiadapter.{domain_slug}.",
    )
    return text, text != old


def _rewrite_xml(text: str, domain_slug: str) -> tuple[str, bool]:
    """Apply namespace/type/resultType/parameterType renames in mapper xml."""
    old = text
    for attr in ("namespace", "type", "resultType", "parameterType"):
        text = text.replace(
            f'{attr}="com.example.{domain_slug}',
            f'{attr}="com.nexacro.uiadapter.{domain_slug}',
        )
    return text, text != old


def _safe_backup(src: pathlib.Path, bak: pathlib.Path) -> bool:
    """Copy src → bak only if bak does not already exist. Returns True if backup made."""
    if not bak.exists():
        shutil.copy2(src, bak)
        return True
    return False


# ---------------------------------------------------------------------------
# Conflict scan
# ---------------------------------------------------------------------------

def _collect_java_targets(out_dir: pathlib.Path, target_dir: pathlib.Path, domain_slug: str) -> list[pathlib.Path]:
    """Return list of target paths for each .java file in 3-mybatis."""
    src_root = out_dir / "3-mybatis" / "src" / "main" / "java" / "com" / "example" / domain_slug
    if not src_root.exists():
        return []
    targets = []
    for src_file in src_root.rglob("*.java"):
        rel = src_file.relative_to(src_root)
        dest = target_dir / "src" / "main" / "java" / "com" / "nexacro" / "uiadapter" / domain_slug / rel
        targets.append((src_file, dest))
    return targets


def _collect_resource_targets(
    out_dir: pathlib.Path, target_dir: pathlib.Path
) -> list[tuple[pathlib.Path, pathlib.Path]]:
    """Return list of (src, dest) for each resource file in 3-mybatis/resources."""
    res_root = out_dir / "3-mybatis" / "src" / "main" / "resources"
    if not res_root.exists():
        return []
    pairs = []
    for src_file in res_root.rglob("*"):
        if src_file.is_dir():
            continue
        rel = src_file.relative_to(res_root)
        dest = target_dir / "src" / "main" / "resources" / rel
        pairs.append((src_file, dest))
    return pairs


def _collect_xfdl_targets(
    out_dir: pathlib.Path, target_dir: pathlib.Path, domain_slug: str
) -> list[tuple[pathlib.Path, pathlib.Path]]:
    """Return (src, dest) pairs for xfdl forms."""
    form_dir = out_dir / "4-nexacro" / "nxui" / "_form_"
    if not form_dir.exists():
        return []
    pairs = []
    for src_file in form_dir.glob("*.xfdl"):
        dest = target_dir / "nxui" / "packageN" / domain_slug / src_file.name
        pairs.append((src_file, dest))
    return pairs


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_overlay(
    *,
    out_dir: pathlib.Path,
    target_dir: pathlib.Path,
    domain_slug: str,
    domain_label: str,
    service_pascal: str,
    blueprint_entities: list[dict],
    overlay_force: bool = False,
) -> dict:
    """Overlay scaffold output onto target_dir.

    Returns a report dict with these keys:
        java_copied: list[str]    relative paths under target src/main/java/
        resources_copied: list[str]
        xfdl_copied: list[str]
        backed_up: list[str]      paths of .bak files created
        renamed_imports: int      count of files where package/import rewrite happened
        menu_warning: Optional[str]  user-facing schema mismatch message, None if OK
        typedef_added: bool       True if a new <Service> was inserted
        conflicts: list[str]      conflicting files (only if overlay_force=False and a clash exists)
    """
    out_dir = pathlib.Path(out_dir)
    target_dir = pathlib.Path(target_dir)

    report: dict = {
        "java_copied": [],
        "resources_copied": [],
        "xfdl_copied": [],
        "backed_up": [],
        "renamed_imports": 0,
        "menu_warning": None,
        "typedef_added": False,
        "conflicts": [],
    }

    # -----------------------------------------------------------------------
    # Conflict-scan pass (Steps 1–3) — only when not forcing
    # -----------------------------------------------------------------------
    java_pairs = _collect_java_targets(out_dir, target_dir, domain_slug)
    resource_pairs = _collect_resource_targets(out_dir, target_dir)
    xfdl_pairs = _collect_xfdl_targets(out_dir, target_dir, domain_slug)

    if not overlay_force:
        conflicts: list[str] = []

        for _src, dest in java_pairs:
            if dest.exists():
                conflicts.append(str(dest))

        for src_file, dest in resource_pairs:
            name = src_file.name
            if name in ("schema.sql", "data.sql"):
                # These are always written (with scaffold.bak backup) — not a conflict
                continue
            if dest.exists():
                conflicts.append(str(dest))

        for _src, dest in xfdl_pairs:
            if dest.exists():
                conflicts.append(str(dest))

        if conflicts:
            raise RuntimeError(
                "Stage 5 overlay would overwrite existing files "
                "(use --overlay-force to allow):\n"
                + "\n".join(f"  - {p}" for p in conflicts)
            )

    # -----------------------------------------------------------------------
    # Step 1: Java overlay with package rename
    # -----------------------------------------------------------------------
    for src_file, dest in java_pairs:
        text = src_file.read_text(encoding="utf-8")
        new_text, changed = _rewrite_java(text, domain_slug)

        if dest.exists() and overlay_force:
            bak = pathlib.Path(str(dest) + ".bak")
            bak.write_text(dest.read_text(encoding="utf-8"), encoding="utf-8")
            report["backed_up"].append(str(bak))

        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(new_text, encoding="utf-8")

        rel = str(dest.relative_to(target_dir / "src" / "main" / "java"))
        report["java_copied"].append(rel)
        if changed:
            report["renamed_imports"] += 1

    # -----------------------------------------------------------------------
    # Step 2: Resources overlay
    # -----------------------------------------------------------------------
    for src_file, dest in resource_pairs:
        name = src_file.name
        suffix = src_file.suffix.lower()

        if name in ("schema.sql", "data.sql"):
            # One-shot scaffold backup (don't overwrite existing .scaffold.bak)
            if dest.exists():
                scaffold_bak = dest.parent / f"{name}.scaffold.bak"
                _safe_backup(dest, scaffold_bak)
                if scaffold_bak.exists() and str(scaffold_bak) not in report["backed_up"]:
                    # only track if we just created it
                    pass
            dest.parent.mkdir(parents=True, exist_ok=True)
            text = src_file.read_text(encoding="utf-8")
            dest.write_text(text, encoding="utf-8")

        elif suffix == ".xml":
            if dest.exists() and overlay_force:
                bak = pathlib.Path(str(dest) + ".bak")
                bak.write_text(dest.read_text(encoding="utf-8"), encoding="utf-8")
                report["backed_up"].append(str(bak))

            dest.parent.mkdir(parents=True, exist_ok=True)
            text = src_file.read_text(encoding="utf-8")
            new_text, _changed = _rewrite_xml(text, domain_slug)
            dest.write_text(new_text, encoding="utf-8")

        else:
            # Binary or other files
            if dest.exists() and overlay_force:
                bak = pathlib.Path(str(dest) + ".bak")
                shutil.copy2(dest, bak)
                report["backed_up"].append(str(bak))

            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dest)

        rel = str(dest.relative_to(target_dir / "src" / "main" / "resources"))
        report["resources_copied"].append(rel)

    # -----------------------------------------------------------------------
    # Step 3: xfdl form copy
    # -----------------------------------------------------------------------
    for src_file, dest in xfdl_pairs:
        if dest.exists() and overlay_force:
            bak = pathlib.Path(str(dest) + ".bak")
            shutil.copy2(dest, bak)
            report["backed_up"].append(str(bak))

        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dest)
        report["xfdl_copied"].append(dest.name)

    # -----------------------------------------------------------------------
    # Step 4: Menu injection
    # -----------------------------------------------------------------------
    frame_login = target_dir / "nxui" / "packageN" / "frame" / "frameLogin.xfdl"
    if not frame_login.exists():
        report["menu_warning"] = (
            f"frameLogin.xfdl not found at {frame_login}; skipping menu injection"
        )
    else:
        # One-shot backup
        frame_bak = pathlib.Path(str(frame_login) + ".bak")
        if _safe_backup(frame_login, frame_bak):
            report["backed_up"].append(str(frame_bak))

        domain_id = f"BIZ_{service_pascal.upper()}"
        entries = [
            (
                e["name"],
                e.get("label_ko") or e["name"],
                f"{domain_slug}::{e['name']}.xfdl",
            )
            for e in blueprint_entities
        ]

        try:
            menu_injector.inject_menu_rows(
                frame_login,
                domain_id=domain_id,
                domain_label=domain_label,
                domain_sort=10,
                entries=entries,
            )
        except menu_injector.SchemaMismatch as exc:
            missing = [c for c in exc.required if c not in exc.target_cols]
            report["menu_warning"] = (
                "frameLogin.xfdl dsSample column schema mismatch — menu injection skipped.\n"
                f"  target ColumnInfo: {exc.target_cols}\n"
                f"  required by tool : {exc.required}\n"
                f"  missing          : {missing}\n"
                "  → Add the missing columns to dsSample <ColumnInfo>, or map them in blueprint."
            )

    # -----------------------------------------------------------------------
    # Step 5: Typedef merge
    # -----------------------------------------------------------------------
    typedef_path = target_dir / "nxui" / "packageN" / "typedefinition.xml"
    if not typedef_path.exists():
        td_warning = f"typedefinition.xml not found at {typedef_path}; skipping typedef merge"
        if report["menu_warning"]:
            report["typedef_warning"] = td_warning
        else:
            report["typedef_warning"] = td_warning
    else:
        typedef_bak = pathlib.Path(str(typedef_path) + ".bak")
        if _safe_backup(typedef_path, typedef_bak):
            report["backed_up"].append(str(typedef_bak))

        before = typedef_path.read_bytes()
        typedef_merger.merge_service(
            typedef_path,
            prefixid=domain_slug,
            url=f"./{domain_slug}/",
        )
        after = typedef_path.read_bytes()
        report["typedef_added"] = after != before

    # -----------------------------------------------------------------------
    # Step 6: Return report
    # -----------------------------------------------------------------------
    return report
