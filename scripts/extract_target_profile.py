"""Growth-70 (M5 Slice C) — extract customer profile from an existing
SpringBoot project directory.

Reads `pom.xml` + `src/main/resources/application.yml` (or `.properties`)
and emits a `profiles/<slug>.yaml` matching the v1 schema documented in
`profiles/_README.md`.

Status of extracted profile is `draft` — the user is expected to review,
fill in `contact`, set status to `active`, and adjust placeholders before
running `/scaffold --customer-profile <slug>`.

CLI
---

    python scripts/extract_target_profile.py <project-dir>
        [--slug <ascii-slug>]
        [--out profiles/<slug>.yaml]
        [--force]            # overwrite existing profile

Stdlib + PyYAML only (no third-party).
"""
from __future__ import annotations

import argparse
import os
import pathlib
import re
import sys
import xml.etree.ElementTree as ET
from typing import Any, Dict, Optional, Tuple

import yaml

_MVN_NS = {"m": "http://maven.apache.org/POM/4.0.0"}

# JDBC URL → dialect mapping. Order matters (specific before generic).
_JDBC_DIALECTS = (
    ("jdbc:postgresql:", "postgres"),
    ("jdbc:mysql:", "mysql"),
    ("jdbc:hsqldb:", "hsqldb"),
    ("jdbc:h2:", "h2"),
    ("jdbc:oracle:", "oracle"),
    ("jdbc:sqlserver:", "mssql"),
)


# ---------------------------------------------------------------------------
# pom.xml parsing
# ---------------------------------------------------------------------------

def _pom_text(root: ET.Element, *paths: str) -> Optional[str]:
    """Find first `<paths>` element under root, with or without maven NS."""
    for path in paths:
        for ns_path in (path, "./" + "/".join(f"m:{p}" for p in path.split("/"))):
            node = root.find(ns_path, _MVN_NS) if ":" in ns_path else root.find(ns_path)
            if node is not None and node.text:
                return node.text.strip()
    return None


def parse_pom(pom_path: pathlib.Path) -> Dict[str, Any]:
    """Return {groupId, artifactId, version, name, description, lane}.

    `lane` is "jakarta" if any dependency mentions `jakarta.` or
    `mybatis.spring.boot.jakarta`; otherwise "javax".
    """
    tree = ET.parse(str(pom_path))
    root = tree.getroot()
    group_id = _pom_text(root, "groupId")
    artifact_id = _pom_text(root, "artifactId")
    version = _pom_text(root, "version")
    name = _pom_text(root, "name")
    description = _pom_text(root, "description")

    raw = pom_path.read_text(encoding="utf-8", errors="replace")
    lane = "jakarta" if (
        "jakarta.servlet" in raw
        or "mybatis-spring-boot-starter-jakarta" in raw
        or "mybatis.spring.boot.jakarta" in raw
        or "spring-boot-starter-web" in raw and "boot3" in raw
    ) else "javax"
    return {
        "group_id": group_id,
        "artifact_id": artifact_id,
        "version": version,
        "name": name,
        "description": description,
        "lane": lane,
        "raw": raw,
    }


# ---------------------------------------------------------------------------
# application.yml / .properties parsing
# ---------------------------------------------------------------------------

def _flatten(d: Any, prefix: str = "") -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if isinstance(d, dict):
        for k, v in d.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            if isinstance(v, dict):
                out.update(_flatten(v, key))
            else:
                out[key] = v
    return out


def _read_properties(text: str) -> Dict[str, str]:
    flat: Dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            flat[k.strip()] = v.strip()
        elif ":" in line:
            k, v = line.split(":", 1)
            flat[k.strip()] = v.strip()
    return flat


def parse_application_config(resources_dir: pathlib.Path) -> Dict[str, Any]:
    """Return flat dict from application.yml or application.properties."""
    yml = resources_dir / "application.yml"
    yaml_alt = resources_dir / "application.yaml"
    props = resources_dir / "application.properties"
    if yml.exists() or yaml_alt.exists():
        path = yml if yml.exists() else yaml_alt
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return _flatten(data)
    if props.exists():
        return _read_properties(props.read_text(encoding="utf-8"))
    return {}


# ---------------------------------------------------------------------------
# Derivation helpers
# ---------------------------------------------------------------------------

_SLUG_SUFFIXES = ("-shell-mdi", "-shell-sdi", "-shell", "-portal", "-uiadapter", "-app")


def derive_slug(artifact_id: str) -> str:
    s = artifact_id.lower()
    for suf in _SLUG_SUFFIXES:
        if s.endswith(suf):
            s = s[: -len(suf)]
            break
    s = re.sub(r"[^a-z0-9_-]+", "-", s).strip("-_")
    return s or artifact_id


def detect_dialect(jdbc_url: Optional[str]) -> str:
    if not jdbc_url:
        return "postgres"  # safe default; user can override
    url = jdbc_url.strip().lower()
    for prefix, name in _JDBC_DIALECTS:
        if url.startswith(prefix):
            return name
    return "postgres"


def derive_base_package(type_aliases_pkg: Optional[str], group_id: Optional[str]) -> str:
    """`mybatis.base_package` — used for compile.py --package."""
    if type_aliases_pkg:
        # type-aliases-package is usually <root>.<domain>.domain;
        # drop trailing ".domain" to land on <root>.<domain>; then drop one
        # more segment to land on <root>. Fall back when shorter.
        parts = type_aliases_pkg.split(".")
        if parts[-1] in ("domain", "model", "dto", "entity"):
            parts = parts[:-1]
        if len(parts) >= 3:
            return ".".join(parts[:-1])
        return ".".join(parts)
    return group_id or "com.example"


def derive_project_root_pkg(type_aliases_pkg: Optional[str], group_id: Optional[str]) -> str:
    """`mybatis.project_root_pkg` — typically `<group_id>.uiadapter`."""
    if group_id and group_id.endswith(".uiadapter"):
        return group_id
    if type_aliases_pkg:
        parts = type_aliases_pkg.split(".")
        if "uiadapter" in parts:
            idx = parts.index("uiadapter")
            return ".".join(parts[: idx + 1])
    return f"{group_id}.uiadapter" if group_id else "com.example.uiadapter"


def derive_target_pkg_prefix(project_root_pkg: str) -> str:
    return project_root_pkg


def derive_url_template(jdbc_url: Optional[str]) -> Tuple[str, Optional[str], Optional[int], Optional[str]]:
    """Return (url_template, host, port, db).

    For jdbc:postgresql://HOST:PORT/DB returns parametric template + parts.
    Falls back to literal url when parsing fails.
    """
    if not jdbc_url:
        return ("jdbc:postgresql://{host}:{port}/{db}", "localhost", 5432, "app")
    m = re.match(
        r"^(jdbc:[a-z]+:(?://)?)([^:/]+)(?::(\d+))?/([^?;]+)",
        jdbc_url.strip(),
        re.IGNORECASE,
    )
    if not m:
        return (jdbc_url, None, None, None)
    scheme, host, port, db = m.group(1), m.group(2), m.group(3), m.group(4)
    port_i = int(port) if port else None
    return (f"{scheme}{{host}}:{{port}}/{{db}}", host, port_i, db)


# ---------------------------------------------------------------------------
# Profile assembly
# ---------------------------------------------------------------------------

def build_profile(
    project_dir: pathlib.Path,
    *,
    slug_override: Optional[str] = None,
) -> Dict[str, Any]:
    pom = project_dir / "pom.xml"
    if not pom.exists():
        raise FileNotFoundError(
            f"pom.xml not found under {project_dir} — only Maven SpringBoot projects "
            f"are supported in M5 Slice C (Gradle is deferred)."
        )
    pom_data = parse_pom(pom)
    if not pom_data["artifact_id"]:
        raise ValueError(f"pom.xml at {pom} is missing <artifactId>")

    resources = project_dir / "src" / "main" / "resources"
    app = parse_application_config(resources) if resources.exists() else {}

    slug = slug_override or derive_slug(pom_data["artifact_id"])
    if not re.match(r"^[a-z][a-z0-9_-]*$", slug):
        raise ValueError(
            f"derived slug {slug!r} is not a valid ASCII slug; pass --slug=<ascii>"
        )

    jdbc_url = app.get("spring.datasource.url")
    dialect = detect_dialect(jdbc_url)
    url_template, host, port, db = derive_url_template(jdbc_url)

    type_aliases_pkg = app.get("mybatis.type-aliases-package")
    base_package = derive_base_package(type_aliases_pkg, pom_data["group_id"])
    project_root_pkg = derive_project_root_pkg(type_aliases_pkg, pom_data["group_id"])
    target_pkg_prefix = derive_target_pkg_prefix(project_root_pkg)

    env_prefix = slug.upper().replace("-", "_")
    display = pom_data.get("name") or pom_data.get("description") or slug
    if display and len(display) > 80:
        display = display[:77] + "..."

    return {
        "version": 1,
        "customer": {
            "slug": slug,
            "display": display,
            "status": "draft",
        },
        "ddl": {"dialect": dialect},
        "mybatis": {
            "base_package": base_package,
            "project_root_pkg": project_root_pkg,
            "uia_namespace": pom_data["lane"],
        },
        "nexacro": {"default_pattern": "D2"},
        "overlay": {
            "target_pkg_prefix": target_pkg_prefix,
            "shell_app_id": pom_data["artifact_id"],
            "maven": {
                "group_id": pom_data["group_id"],
                "artifact_id_template": "{slug}-shell",
                "version": pom_data.get("version") or "1.0.0-SNAPSHOT",
            },
            "datasource": {
                "username": f"${{{env_prefix}_DB_USER}}",
                "password": f"${{{env_prefix}_DB_PASS}}",
                "url_template": url_template,
            },
        },
        "auth": {"mode": "session", "lane": pom_data["lane"]},
        "defaults": {"lane": pom_data["lane"], "ui": "nexacro"},
        "datasource": {
            "username": f"${{{env_prefix}_DB_USER}}",
            "password": f"${{{env_prefix}_DB_PASS}}",
            "url_template": url_template,
            "host": host or "localhost",
            "port": port if port is not None else 5432,
            "db": db or slug,
        },
        "domains_seen": [],
        "_extracted_from": str(project_dir.resolve()).replace("\\", "/"),
    }


# ---------------------------------------------------------------------------
# Serializer — keep ${...} placeholders literal, plus a friendly header
# ---------------------------------------------------------------------------

_HEADER = (
    "# Auto-extracted by scripts/extract_target_profile.py (Growth-70).\n"
    "# Status is `draft` — review before promoting to `active`. Fill in\n"
    "# customer.contact, override host/port if needed, and set the\n"
    "# referenced env vars in your .env / secret store.\n"
    "\n"
)


def dump_profile(profile: Dict[str, Any]) -> str:
    """yaml.safe_dump + header. Round-trips through load_customer_profile."""
    body = yaml.safe_dump(
        profile,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=120,
    )
    return _HEADER + body


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _default_out_path(slug: str) -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent.parent / "profiles" / f"{slug}.yaml"


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(
        prog="extract_target_profile",
        description="Extract customer profile YAML from an existing SpringBoot project.",
    )
    p.add_argument("project_dir", help="path to SpringBoot project root (containing pom.xml)")
    p.add_argument("--slug", default=None, help="override derived slug (ASCII)")
    p.add_argument("--out", default=None, help="output path (defaults to profiles/<slug>.yaml)")
    p.add_argument("--force", action="store_true", help="overwrite existing profile")
    p.add_argument("--print", dest="print_only", action="store_true", help="print to stdout instead of writing")
    args = p.parse_args(argv)

    project_dir = pathlib.Path(args.project_dir).resolve()
    if not project_dir.is_dir():
        print(f"ERROR: not a directory: {project_dir}", file=sys.stderr)
        return 2

    try:
        profile = build_profile(project_dir, slug_override=args.slug)
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    payload = dump_profile(profile)
    if args.print_only:
        sys.stdout.write(payload)
        return 0

    out = pathlib.Path(args.out) if args.out else _default_out_path(profile["customer"]["slug"])
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and not args.force:
        print(
            f"ERROR: {out} already exists — pass --force to overwrite, "
            f"or pick a different --slug.",
            file=sys.stderr,
        )
        return 1
    out.write_text(payload, encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
