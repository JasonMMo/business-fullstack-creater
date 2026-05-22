"""Live WAS overlay — apply scaffold output onto jakarta runner (5 points).

Points:
  1. Application.java — inject com.example.<slug> into scanBasePackages + @MapperScan
  2. application.yml — append <slug>-schema.sql / <slug>-data.sql to schema/data-locations
  3. <slug>-schema.sql — copy from scaffold with `;` → `^^`
  4. <slug>-data.sql  — copy from scaffold with `;` → `^^`
  5. mapper XML — PascalCase → kebab-case rename + copy
  + Java source tree copy under src/main/java/com/example/<slug>/

All edits are idempotent — running twice produces the same file content.
"""
from __future__ import annotations
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class OverlayPlan:
    domain_slug: str
    schema_sql: Path
    data_sql: Path
    mapper_xml_dir: Path
    java_src: Path


@dataclass
class OverlayResult:
    files_written: list[Path] = field(default_factory=list)
    files_edited: list[Path] = field(default_factory=list)


_RESERVED_SUBPKGS = {"controller", "service", "mapper", "domain", "config", "dto", "vo", "util", "impl"}


_SCAFFOLD_LANE_RE = re.compile(r"^\s*-\s*lane:\s*`([^`]+)`", re.MULTILINE)


def discover_scaffold_lane(scaffold_dir: Path) -> str | None:
    """Read the `lane: <name>` line from scaffold-report.md.

    Growth-48 (T-Probe-LaneRunner-Mismatch): wire-protocol selection must come
    from the *scaffold* lane (what Stage 3 emitted), not the *runner* lane the
    user picked for deployment. scaffold-report.md is the truth source — Stage
    1 writes `- lane: \\`<name>\\` (middle: ...)` on entry to the report.

    Returns the lane string (e.g. 'nexacro', 'jakarta') or None if the report
    is missing or has no recognizable `lane:` line.
    """
    report = Path(scaffold_dir) / "scaffold-report.md"
    if not report.exists():
        return None
    try:
        text = report.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    m = _SCAFFOLD_LANE_RE.search(text)
    return m.group(1) if m else None


def derive_domain_slug(scaffold_dir: Path) -> str | None:
    """Find unique sub-package under com.nexacro.uiadapter (Stage 3 actual) or com.example (legacy).

    Stage 3 emits `com.nexacro.uiadapter.<slug>.{controller,service,mapper,domain}`.
    Legacy fixtures emit `com.example.<slug>.*`. Checks both, in that order.
    Returns the unique <slug> directory name, or None if not derivable.
    """
    base_root = Path(scaffold_dir) / "3-mybatis" / "src" / "main" / "java" / "com"
    for sub in (("nexacro", "uiadapter"), ("example",)):
        base = base_root.joinpath(*sub)
        if not base.exists():
            continue
        candidates = [
            d.name for d in base.iterdir()
            if d.is_dir() and d.name not in _RESERVED_SUBPKGS and not d.name.startswith(".")
        ]
        if len(candidates) == 1:
            return candidates[0]
    return None


def _find_sql(scaffold_dir: Path, name: str) -> Path | None:
    """Try Stage 3 resources first, fall back to legacy 2-ddl/."""
    for candidate in (
        scaffold_dir / "3-mybatis" / "src" / "main" / "resources" / name,
        scaffold_dir / "2-ddl" / name,
    ):
        if candidate.exists():
            return candidate
    return None


def _find_java_src(scaffold_dir: Path, slug: str) -> Path:
    """Stage 3 actual = com.nexacro.uiadapter.<slug>; legacy fixture = com.example.<slug>."""
    stage3 = (scaffold_dir / "3-mybatis" / "src" / "main" / "java"
              / "com" / "nexacro" / "uiadapter" / slug)
    if stage3.exists():
        return stage3
    return (scaffold_dir / "3-mybatis" / "src" / "main" / "java"
            / "com" / "example" / slug)


def _find_mapper_xml_dir(scaffold_dir: Path) -> Path:
    """Stage 3 actual = mybatis/mapper (singular); legacy fixture = mybatis/mappers."""
    res = scaffold_dir / "3-mybatis" / "src" / "main" / "resources"
    for sub in ("mapper", "mappers"):
        candidate = res / "mybatis" / sub
        if candidate.exists():
            return candidate
    return res / "mybatis" / "mappers"


def discover_scaffold(scaffold_dir: Path, domain_slug: str | None = None) -> OverlayPlan:
    """Walk scaffold output (Stage 2 DDL + Stage 3 mybatis) for the given (or derived) domain.

    Slug resolution: explicit arg wins; else parse `com.nexacro.uiadapter.<slug>` from Stage 3.
    SQL resolution: prefer `3-mybatis/src/main/resources/{schema,data}.sql`, fall back to `2-ddl/`.
    """
    scaffold_dir = Path(scaffold_dir)
    if domain_slug is None:
        domain_slug = derive_domain_slug(scaffold_dir)
        if domain_slug is None:
            raise ValueError(
                f"could not derive domain slug from {scaffold_dir} — no unique sub-package "
                "under 3-mybatis/.../com/nexacro/uiadapter/. Pass slug explicitly."
            )
    schema_sql = _find_sql(scaffold_dir, "schema.sql")
    if schema_sql is None:
        raise FileNotFoundError(f"schema.sql not found under {scaffold_dir} (checked 3-mybatis/resources and 2-ddl)")
    data_sql = _find_sql(scaffold_dir, "data.sql")
    if data_sql is None:
        raise FileNotFoundError(f"data.sql not found under {scaffold_dir} (checked 3-mybatis/resources and 2-ddl)")
    return OverlayPlan(
        domain_slug=domain_slug,
        schema_sql=schema_sql,
        data_sql=data_sql,
        mapper_xml_dir=_find_mapper_xml_dir(scaffold_dir),
        java_src=_find_java_src(scaffold_dir, domain_slug),
    )


def _pascal_to_kebab(name: str) -> str:
    """AccountMapper.xml → account-mapper.xml; JournalEntryMapper.xml → journalentry-mapper.xml."""
    stem, _, ext = name.rpartition(".")
    if stem.endswith("Mapper"):
        prefix = stem[: -len("Mapper")]
        return f"{prefix.lower()}-mapper.{ext}"
    return f"{stem.lower()}.{ext}"


def _edit_application_java(app_path: Path, slug: str) -> None:
    """Inject "com.example.<slug>" into scanBasePackages and @MapperScan, idempotent.

    Handles two runner shapes:
      A) Annotation already parameterised — `@SpringBootApplication(scanBasePackages = { ... })`
         plus an existing `@MapperScan(basePackages = { ... })` — just append our slug.
      B) Bare `@SpringBootApplication` with no scanBasePackages and no @MapperScan
         (the boot-jdk17-jakarta default). We must INSERT the parameters and the
         @MapperScan annotation, not just substitute.
    """
    text = app_path.read_text(encoding="utf-8")
    pkg = f'"com.example.{slug}"'
    mapper_pkg = f'"com.example.{slug}.mapper"'

    if pkg not in text:
        if re.search(r'scanBasePackages\s*=\s*\{', text):
            text = re.sub(
                r'(scanBasePackages\s*=\s*\{)([^}]*)(\})',
                lambda m: f'{m.group(1)}{m.group(2).rstrip()}, {pkg}{m.group(3)}',
                text,
                count=1,
            )
        else:
            # Bare @SpringBootApplication — parameterise it, including the runner's
            # own root package so the original controllers stay scanned.
            base_pkg = _root_package(text)
            text = re.sub(
                r'@SpringBootApplication\b(?!\s*\()',
                f'@SpringBootApplication(scanBasePackages = {{"{base_pkg}", {pkg}}})',
                text,
                count=1,
            )

    if mapper_pkg not in text:
        if re.search(r'@MapperScan\s*\(\s*basePackages\s*=\s*\{', text):
            text = re.sub(
                r'(@MapperScan\s*\(\s*basePackages\s*=\s*\{)([^}]*)(\})',
                lambda m: f'{m.group(1)}{m.group(2).rstrip()}, {mapper_pkg}{m.group(3)}',
                text,
                count=1,
            )
        else:
            # Add @MapperScan annotation + import line. Include the runner's own
            # .mapper subpackage so runner-native @Mapper interfaces stay discovered
            # (an explicit @MapperScan overrides MyBatis' default AutoConfigurationPackages scan).
            if "org.mybatis.spring.annotation.MapperScan" not in text:
                text = re.sub(
                    r'(import org\.springframework\.boot\.autoconfigure\.SpringBootApplication;\s*\n)',
                    r'\1import org.mybatis.spring.annotation.MapperScan;\n',
                    text,
                    count=1,
                )
            base_pkg = _root_package(text)
            base_mapper_pkg = f'"{base_pkg}.mapper"'
            text = re.sub(
                r'(@SpringBootApplication[^\n]*\n)',
                f'\\1@MapperScan(basePackages = {{{base_mapper_pkg}, {mapper_pkg}}})\n',
                text,
                count=1,
            )

    app_path.write_text(text, encoding="utf-8")


def _root_package(text: str) -> str:
    """Extract the Application class's own package declaration."""
    m = re.search(r'^\s*package\s+([\w.]+)\s*;', text, re.MULTILINE)
    return m.group(1) if m else "com.nexacro.uiadapter"


def _edit_application_yml(yml_path: Path, slug: str) -> None:
    """Append <slug>-schema.sql / <slug>-data.sql to schema/data-locations, idempotent."""
    text = yml_path.read_text(encoding="utf-8")
    schema_entry = f"classpath:{slug}-schema.sql"
    data_entry = f"classpath:{slug}-data.sql"

    if f"{slug}-schema.sql" not in text:
        text = re.sub(
            r'(schema-locations:\s*)(\S.*)',
            lambda m: f'{m.group(1)}{m.group(2)},{schema_entry}',
            text,
            count=1,
        )
    if f"{slug}-data.sql" not in text:
        text = re.sub(
            r'(data-locations:\s*)(\S.*)',
            lambda m: f'{m.group(1)}{m.group(2)},{data_entry}',
            text,
            count=1,
        )
    yml_path.write_text(text, encoding="utf-8")


def _copy_sql_with_separator(src: Path, dst: Path) -> None:
    """Copy SQL file, substituting `;` → `^^` (HSQLDB statement separator override)."""
    text = src.read_text(encoding="utf-8").replace(";", "^^")
    dst.write_text(text, encoding="utf-8")


def apply_overlay(runner_dir: Path, plan: OverlayPlan) -> OverlayResult:
    """Apply 5-point overlay onto a jakarta runner. Returns paths written/edited."""
    runner_dir = Path(runner_dir)
    result = OverlayResult()
    slug = plan.domain_slug

    # 1. Application.java
    app = runner_dir / "src/main/java/com/nexacro/uiadapter/Application.java"
    _edit_application_java(app, slug)
    result.files_edited.append(app)

    # 2. application.yml
    yml = runner_dir / "src/main/resources/application.yml"
    _edit_application_yml(yml, slug)
    result.files_edited.append(yml)

    # 3. <slug>-schema.sql
    schema_out = runner_dir / "src/main/resources" / f"{slug}-schema.sql"
    _copy_sql_with_separator(plan.schema_sql, schema_out)
    result.files_written.append(schema_out)

    # 4. <slug>-data.sql
    data_out = runner_dir / "src/main/resources" / f"{slug}-data.sql"
    _copy_sql_with_separator(plan.data_sql, data_out)
    result.files_written.append(data_out)

    # 5. mapper XML rename + copy
    mapper_dst_dir = runner_dir / "src/main/resources/mybatis/mappers"
    mapper_dst_dir.mkdir(parents=True, exist_ok=True)
    if plan.mapper_xml_dir.exists():
        for xml in sorted(plan.mapper_xml_dir.glob("*.xml")):
            dst = mapper_dst_dir / _pascal_to_kebab(xml.name)
            shutil.copy2(xml, dst)
            result.files_written.append(dst)

    # Java source tree copy
    java_dst_root = runner_dir / "src/main/java/com/example" / slug
    if plan.java_src.exists():
        for src_file in sorted(plan.java_src.rglob("*.java")):
            rel = src_file.relative_to(plan.java_src)
            dst = java_dst_root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dst)
            result.files_written.append(dst)

    return result
