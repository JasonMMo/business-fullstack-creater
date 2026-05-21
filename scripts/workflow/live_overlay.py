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


def discover_scaffold(scaffold_dir: Path, domain_slug: str) -> OverlayPlan:
    """Walk scaffold output (Stage 2 DDL + Stage 3 mybatis) for the given domain."""
    scaffold_dir = Path(scaffold_dir)
    schema_sql = scaffold_dir / "2-ddl" / "schema.sql"
    if not schema_sql.exists():
        raise FileNotFoundError(f"schema.sql not found at {schema_sql}")
    data_sql = scaffold_dir / "2-ddl" / "data.sql"
    if not data_sql.exists():
        raise FileNotFoundError(f"data.sql not found at {data_sql}")
    java_src = (scaffold_dir / "3-mybatis" / "src" / "main" / "java"
                / "com" / "example" / domain_slug)
    mapper_xml_dir = (scaffold_dir / "3-mybatis" / "src" / "main" / "resources"
                     / "mybatis" / "mappers")
    return OverlayPlan(
        domain_slug=domain_slug,
        schema_sql=schema_sql,
        data_sql=data_sql,
        mapper_xml_dir=mapper_xml_dir,
        java_src=java_src,
    )


def _pascal_to_kebab(name: str) -> str:
    """AccountMapper.xml → account-mapper.xml; JournalEntryMapper.xml → journalentry-mapper.xml."""
    stem, _, ext = name.rpartition(".")
    if stem.endswith("Mapper"):
        prefix = stem[: -len("Mapper")]
        return f"{prefix.lower()}-mapper.{ext}"
    return f"{stem.lower()}.{ext}"


def _edit_application_java(app_path: Path, slug: str) -> None:
    """Inject "com.example.<slug>" into scanBasePackages and @MapperScan, idempotent."""
    text = app_path.read_text(encoding="utf-8")
    pkg = f'"com.example.{slug}"'
    mapper_pkg = f'"com.example.{slug}.mapper"'

    if pkg not in text:
        text = re.sub(
            r'(scanBasePackages\s*=\s*\{)([^}]*)(\})',
            lambda m: f'{m.group(1)}{m.group(2).rstrip()}, {pkg}{m.group(3)}',
            text,
            count=1,
        )
    if mapper_pkg not in text:
        text = re.sub(
            r'(@MapperScan\s*\(\s*basePackages\s*=\s*\{)([^}]*)(\})',
            lambda m: f'{m.group(1)}{m.group(2).rstrip()}, {mapper_pkg}{m.group(3)}',
            text,
            count=1,
        )
    app_path.write_text(text, encoding="utf-8")


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
