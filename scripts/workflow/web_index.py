"""web_index.py — Static portal generator for business-fullstack-creater.

Builds a fully-static HTML portal under docs/ by reusing existing
list_domains.py data and learn-log.md §1 verification table.

CLI:
    python -m scripts.workflow.web_index [--domain <slug>] [--check] [--json] [--help]
    python scripts/workflow/web_index.py [--domain <slug>] [--check] [--json] [--help]
"""
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
import urllib.parse
import zipfile
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Callable, Optional

# Support both `python -m scripts.workflow.web_index` (package import)
# and `python scripts/workflow/web_index.py` (direct script invocation).
try:
    from .list_domains import Domain, load_domains, DEFAULT_INDEX_PATH
except ImportError:
    _root = str(Path(__file__).resolve().parents[2])
    if _root not in sys.path:
        sys.path.insert(0, _root)
    from scripts.workflow.list_domains import Domain, load_domains, DEFAULT_INDEX_PATH

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

CREATER_ROOT = Path(__file__).resolve().parents[2]
LEARN_LOG = CREATER_ROOT / "learn-log.md"
DOCS_ROOT = CREATER_ROOT / "docs"

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

VALID_LANES = ("jakarta", "javax", "vanilla", "nexacro")

# Files expected under docs/scaffolds/<slug>/<lane>/
_SCAFFOLD_FILES = ("DDL.sql", "Mapper.xml", "Controller.java", "Service.java", "project.zip")


@dataclass(frozen=True)
class MatrixEntry:
    domain: str    # ASCII slug matching Domain.name from list_domains.load_domains()
    lane: str      # "jakarta" | "javax" | "vanilla" | "nexacro"
    status: str    # "verified" | "default-unverified"
    source: str    # human-readable provenance, e.g. "learn-log §1 row 1" or "jakarta-default"


@dataclass
class BuildResult:
    domains_ok: list[str] = field(default_factory=list)       # slugs successfully built
    domains_failed: list[str] = field(default_factory=list)   # slugs that encountered errors
    missing_files: list[str] = field(default_factory=list)    # relative paths missing (--check mode only)
    warnings: list[str] = field(default_factory=list)         # non-fatal notes
    # T-Web-EmptyPortal (Growth-57) — empty-portal detection surface
    placeholder_slots: int = 0          # preview files written as placeholder (across all entries)
    total_slots: int = 0                # preview files written in total (placeholder + real)
    catalog_root_missing: bool = False  # ~/.karpathy-rdb/catalog/ absent at build time


# ---------------------------------------------------------------------------
# §1 learn-log parser
# ---------------------------------------------------------------------------

# Matches a table row in §1 that contains a ✅ check mark.
# Format: | **lane** | runner | ✅ Growth-N (domain, ...) | notes |
_SECTION1_START = re.compile(r"^##\s+1\.")
_SECTION_END = re.compile(r"^##\s+[2-9]")
_TABLE_ROW = re.compile(r"^\|")


def _parse_learn_log_section1(text: str) -> list[tuple[str, str, str]]:
    """Parse §1 table from learn-log.md.

    Returns list of (domain_slug, lane, growth_ref) triples for all ✅ rows.
    The domain_slug is extracted from the growth ref annotation, e.g.
    '✅ Growth-28 (finance)' yields domain_slug='finance'.
    """
    lines = text.splitlines()
    in_section = False
    results: list[tuple[str, str, str]] = []

    for line in lines:
        if _SECTION1_START.match(line):
            in_section = True
            continue
        if in_section and _SECTION_END.match(line):
            break
        if not in_section:
            continue
        if not _TABLE_ROW.match(line):
            continue

        # Parse table row — split on | and strip
        parts = [p.strip() for p in line.split("|")]
        # parts[0] is empty (before first |), parts[-1] is empty (after last |)
        # Expect at least: | lane | runner | 검증 상태 | 비고 |
        if len(parts) < 5:
            continue

        # Column 1: lane (may be **bold**)
        raw_lane = parts[1]
        lane_clean = re.sub(r"\*+", "", raw_lane).strip().lower()

        # Skip header/separator rows
        if lane_clean in ("lane", "---", "") or "---" in raw_lane:
            continue

        # Column 3: 검증 상태 — look for ✅
        status_col = parts[3]
        if "✅" not in status_col:
            continue

        # Extract all Growth-N (domain) annotations from the status column
        # Patterns: "Growth-28 (finance)", "Growth-49 (customer fresh scaffold...)"
        for m in re.finditer(r"(Growth-\d+)\s*\(([^)]+)\)", status_col):
            growth_ref = m.group(1)
            domain_hint = m.group(2).strip()
            # Take only the first word as the slug (e.g. "customer fresh scaffold" → "customer")
            # Strip trailing punctuation (e.g. "customer," from "customer, envelope...")
            raw_slug = domain_hint.split()[0].lower()
            domain_slug = raw_slug.rstrip(",.;:")
            results.append((domain_slug, lane_clean, growth_ref))

    return results


# ---------------------------------------------------------------------------
# Matrix builder
# ---------------------------------------------------------------------------

def build_matrix(
    domains: list[Domain],
    learn_log_path: Optional[Path] = None,
) -> list[MatrixEntry]:
    """Return MatrixEntry list for all (domain, lane) pairs.

    Algorithm:
    1. Parse learn-log.md §1 table to extract (domain_slug, lane, growth_ref) triples
       marked with ✅ — these become status="verified".
    2. For every domain in `domains`, ensure a jakarta entry exists; if not already
       present from step 1, add status="default-unverified", source="jakarta-default".
    3. Return sorted by (domain, lane).
    """
    if learn_log_path is None:
        learn_log_path = LEARN_LOG

    # Collect verified entries from learn-log §1
    entries: dict[tuple[str, str], MatrixEntry] = {}

    # Build set of domain names from the provided domains list
    domain_names = {d.name for d in domains}

    if learn_log_path.exists():
        text = learn_log_path.read_text(encoding="utf-8")
        verified_triples = _parse_learn_log_section1(text)
        for domain_slug, lane, growth_ref in verified_triples:
            # Only include entries for domains in our working set
            if domain_slug not in domain_names:
                continue
            key = (domain_slug, lane)
            if key not in entries:
                entries[key] = MatrixEntry(
                    domain=domain_slug,
                    lane=lane,
                    status="verified",
                    source=f"learn-log §1 {growth_ref}",
                )

    # Ensure every domain has at least a jakarta entry
    for d in domains:
        key = (d.name, "jakarta")
        if key not in entries:
            entries[key] = MatrixEntry(
                domain=d.name,
                lane="jakarta",
                status="default-unverified",
                source="jakarta-default",
            )

    # Also ensure verified entries reference real domains (keep all verified regardless)
    result = sorted(entries.values(), key=lambda e: (e.domain, e.lane))
    return result


# ---------------------------------------------------------------------------
# Expected output paths for --check
# ---------------------------------------------------------------------------

def _expected_output_paths(
    matrix: list[MatrixEntry],
    docs_root: Path,
) -> list[str]:
    """Return list of relative paths (relative to docs_root) that should exist
    after a full build, based on spec §2.
    """
    paths: list[str] = []

    # Top-level generated files
    paths.append("index.html")
    paths.append("assets/style.css")
    paths.append("assets/preview.js")

    # Per-domain pages and scaffold files
    seen_domains: set[str] = set()
    for entry in matrix:
        slug = entry.domain
        lane = entry.lane

        if slug not in seen_domains:
            paths.append(f"domain/{slug}.html")
            seen_domains.add(slug)

        for fname in _SCAFFOLD_FILES:
            paths.append(f"scaffolds/{slug}/{lane}/{fname}")

    return paths


# ---------------------------------------------------------------------------
# Scaffold pre-generation (M2)
# ---------------------------------------------------------------------------

# Layer label per preview filename — used by _format_placeholder to give
# the user a hint about which generator stage produces this file.
_PREVIEW_LAYER_LABELS: dict[str, str] = {
    "DDL.sql":         "DDL (Stage 2 — andrej-karpathy-rdb-ddl)",
    "Mapper.xml":      "MyBatis Mapper (Stage 3 — andrej-karpathy-rdb-mybatis)",
    "Controller.java": "Spring Controller (Stage 3 — andrej-karpathy-rdb-mybatis)",
    "Service.java":    "Spring Service (Stage 3 — andrej-karpathy-rdb-mybatis)",
}


def _format_placeholder(slug: str, fname: str) -> str:
    """Domain/layer-aware placeholder shown when the generator cannot find source.

    Keeps the literal substring ``"not available"`` for downstream tests, but
    extends the body with a one-line ``/scaffold`` hint and the catalog path
    this portal reads from — turning the empty preview into a tutorial pointer
    (T-Web-EmptyPortal mitigation, Growth-57).
    """
    layer = _PREVIEW_LAYER_LABELS.get(fname, "source")
    return (
        f"// {layer} not available — generator could not find source\n"
        f"//\n"
        f"// run `/scaffold {slug}` first to populate this preview.\n"
        f"// Stage 2 (DDL) will produce files under\n"
        f"// ~/.karpathy-rdb/catalog/{slug}/ that this portal reads from.\n"
    )


# Maps each preview filename to a callable that extracts the source path
# from a SourceMap dict.  SourceMap keys: "ddl", "mapper_xml", "controller", "service"
_PREVIEW_FILE_KEYS: list[tuple[str, str]] = [
    ("DDL.sql",         "ddl"),
    ("Mapper.xml",      "mapper_xml"),
    ("Controller.java", "controller"),
    ("Service.java",    "service"),
]


def _default_source_resolver(entry: MatrixEntry) -> dict[str, Path | None]:
    """Locate scaffold source files via live_overlay.discover_scaffold.

    Returns a dict with keys: "ddl", "mapper_xml", "controller", "service".
    Values are Path objects (may not exist) or None when discovery fails.
    """
    # Import lazily so tests can patch without importing
    try:
        from scripts.workflow.live_overlay import discover_scaffold  # type: ignore
    except ImportError:
        try:
            from .live_overlay import discover_scaffold  # type: ignore
        except ImportError:
            return {"ddl": None, "mapper_xml": None, "controller": None, "service": None}

    # Typical scaffold output root convention for this project
    scaffold_root = Path.home() / ".karpathy-rdb" / "catalog" / entry.domain

    try:
        # Growth-61 T-Web-CatalogSlugMismatch: entry.domain is the Korean catalog
        # subdir name (e.g., '고객관리'), but scaffold Java packages use the ASCII
        # slug (e.g., 'customer'). Pass domain_slug=None so discover_scaffold
        # auto-derives the slug from com.nexacro.uiadapter.<slug>/com.example.<slug>
        # via derive_domain_slug() — otherwise Controller/Service lookups miss.
        plan = discover_scaffold(scaffold_root, domain_slug=None)
    except Exception:
        return {"ddl": None, "mapper_xml": None, "controller": None, "service": None}

    # DDL: schema.sql from Stage 2
    ddl_path = plan.schema_sql if plan.schema_sql and plan.schema_sql.exists() else None

    # Mapper.xml: first XML in mapper_xml_dir
    mapper_xml: Path | None = None
    if plan.mapper_xml_dir and plan.mapper_xml_dir.exists():
        xmls = sorted(plan.mapper_xml_dir.glob("*.xml"))
        if xmls:
            mapper_xml = xmls[0]

    # Controller.java / Service.java: look in java_src sub-packages
    controller: Path | None = None
    service: Path | None = None
    if plan.java_src and plan.java_src.exists():
        controllers = list(plan.java_src.rglob("*Controller.java"))
        services = list(plan.java_src.rglob("*Service.java"))
        if controllers:
            controller = controllers[0]
        if services:
            service = services[0]

    return {
        "ddl":        ddl_path,
        "mapper_xml": mapper_xml,
        "controller": controller,
        "service":    service,
    }


def materialize_scaffold(
    entry: MatrixEntry,
    docs_root: Path,
    *,
    source_resolver: Callable[[MatrixEntry], dict[str, "Path | None"]] | None = None,
) -> tuple[bool, list[str]]:
    """Copy/render four preview files + project.zip for (domain, lane) into docs_root.

    Target layout:
        docs_root/scaffolds/<slug>/<lane>/DDL.sql
        docs_root/scaffolds/<slug>/<lane>/Mapper.xml
        docs_root/scaffolds/<slug>/<lane>/Controller.java
        docs_root/scaffolds/<slug>/<lane>/Service.java
        docs_root/scaffolds/<slug>/<lane>/project.zip

    Missing source files produce inline placeholder files and a warning entry.
    Returns (success, warnings).  Never raises — missing sources are non-fatal.
    """
    warnings: list[str] = []
    slug = entry.domain
    lane = entry.lane

    out_dir = docs_root / "scaffolds" / slug / lane
    out_dir.mkdir(parents=True, exist_ok=True)

    resolver = source_resolver if source_resolver is not None else _default_source_resolver
    try:
        sources: dict[str, Path | None] = resolver(entry)
    except Exception as exc:  # noqa: BLE001
        sources = {"ddl": None, "mapper_xml": None, "controller": None, "service": None}
        warnings.append(f"{slug}/{lane}: source_resolver raised {exc!r}; using placeholders")

    for fname, key in _PREVIEW_FILE_KEYS:
        dst = out_dir / fname
        src: Path | None = sources.get(key)
        if src is not None and Path(src).exists():
            try:
                shutil.copy2(src, dst)
            except OSError as exc:
                warnings.append(f"{slug}/{lane}/{fname}: copy failed ({exc}); using placeholder")
                dst.write_text(_format_placeholder(slug, fname), encoding="utf-8")
        else:
            if src is not None:
                warnings.append(
                    f"{slug}/{lane}/{fname}: source path {src} does not exist; using placeholder"
                )
            else:
                warnings.append(f"{slug}/{lane}/{fname}: source not found; using placeholder")
            dst.write_text(_format_placeholder(slug, fname), encoding="utf-8")

    # Build project.zip from all files in out_dir (excluding the zip itself)
    zip_path = out_dir / "project.zip"
    try:
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for f in sorted(out_dir.iterdir()):
                if f.name == "project.zip":
                    continue
                zf.write(f, arcname=f"{slug}/{lane}/{f.name}")
    except OSError as exc:
        warnings.append(f"{slug}/{lane}/project.zip: zip creation failed ({exc})")
        return False, warnings

    return True, warnings


# ---------------------------------------------------------------------------
# HTML rendering helpers (M3)
# ---------------------------------------------------------------------------

def _escape_html(s: str) -> str:
    """html.escape(s, quote=True) wrapper."""
    return html.escape(s, quote=True)


# ---------------------------------------------------------------------------
# Embedded asset strings (M3)
# ---------------------------------------------------------------------------

_STYLE_CSS = """\
/* business-fullstack-creater portal — style.css (generated) */
:root {
  --color-bg: #f8f9fa;
  --color-surface: #ffffff;
  --color-border: #dee2e6;
  --color-text: #212529;
  --color-text-muted: #6c757d;
  --color-primary: #0d6efd;
  --color-primary-hover: #0a58ca;
  --color-header-bg: #1a1a2e;
  --color-header-text: #ffffff;
  --color-footer-bg: #e9ecef;
  --chip-verified: #198754;
  --chip-unverified: #6c757d;
  --chip-text: #ffffff;
  --radius: 6px;
  --shadow: 0 1px 4px rgba(0,0,0,.08);
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 40px;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: system-ui, -apple-system, sans-serif;
  background: var(--color-bg);
  color: var(--color-text);
  line-height: 1.6;
}

/* Header */
header {
  background: var(--color-header-bg);
  color: var(--color-header-text);
  padding: var(--space-lg) var(--space-xl);
}
header h1 { font-size: 1.6rem; margin-bottom: var(--space-xs); }
header .tagline { color: #adb5bd; font-size: 0.95rem; margin-bottom: var(--space-sm); }
header nav a {
  color: #74c0fc;
  text-decoration: none;
  margin-right: var(--space-md);
  font-size: 0.9rem;
}
header nav a:hover { text-decoration: underline; }

/* Main */
main { max-width: 1200px; margin: 0 auto; padding: var(--space-xl) var(--space-lg); }
main h2 { margin-bottom: var(--space-md); font-size: 1.25rem; }

/* Tile grid */
.tile-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: var(--space-md);
}
.tile {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: var(--space-md);
  box-shadow: var(--shadow);
}
.tile h3 { font-size: 1rem; margin-bottom: var(--space-xs); }
.tile h3 a { color: var(--color-primary); text-decoration: none; }
.tile h3 a:hover { text-decoration: underline; }
.tile .summary { font-size: 0.85rem; color: var(--color-text-muted); margin-bottom: var(--space-sm); }

/* Chips */
.chip-row { display: inline-flex; flex-wrap: wrap; gap: var(--space-xs); }
.chip {
  font-size: 0.75rem;
  padding: 2px 8px;
  border-radius: 20px;
  color: var(--chip-text);
  font-weight: 500;
}
.chip.verified { background: var(--chip-verified); }
.chip.default-unverified { background: var(--chip-unverified); }

/* Lane radios + layer cards */
.lane-radios { border: none; padding: 0; margin-bottom: var(--space-md); }
.lane-radios legend { font-weight: 600; margin-bottom: var(--space-sm); }
.lane-radios label { margin-right: var(--space-md); cursor: pointer; }
.layer-cards { display: flex; flex-wrap: wrap; gap: var(--space-sm); margin-bottom: var(--space-lg); }
.layer-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: var(--space-sm) var(--space-md);
  font-size: 0.85rem;
}

/* Tab bar */
.tab-bar { display: flex; border-bottom: 2px solid var(--color-border); margin-bottom: var(--space-md); }
.tab-bar button {
  background: none;
  border: none;
  padding: var(--space-sm) var(--space-md);
  cursor: pointer;
  font-size: 0.9rem;
  color: var(--color-text-muted);
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
}
.tab-bar button[aria-selected="true"] {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
  font-weight: 600;
}

/* Preview blocks */
.preview-block {
  background: #1e1e2e;
  color: #cdd6f4;
  padding: var(--space-md);
  border-radius: var(--radius);
  overflow-x: auto;
  font-size: 0.82rem;
  line-height: 1.5;
  max-height: 420px;
  white-space: pre;
}

/* Try-it panel */
.try-it { margin-top: var(--space-lg); }
.btn-download {
  display: inline-block;
  background: var(--color-primary);
  color: #fff;
  padding: var(--space-sm) var(--space-lg);
  border-radius: var(--radius);
  text-decoration: none;
  font-weight: 600;
  margin-bottom: var(--space-md);
}
.btn-download:hover { background: var(--color-primary-hover); }
.snippet-block { position: relative; }
.copy-btn {
  position: absolute;
  top: var(--space-sm);
  right: var(--space-sm);
  background: #444;
  color: #fff;
  border: none;
  border-radius: var(--radius);
  padding: 2px 10px;
  cursor: pointer;
  font-size: 0.78rem;
}
.copy-btn:hover { background: #666; }

/* Breadcrumb */
header nav[aria-label="Breadcrumb"] {
  font-size: 0.85rem;
  margin-bottom: var(--space-sm);
  color: #adb5bd;
}
header nav[aria-label="Breadcrumb"] a { color: #74c0fc; text-decoration: none; }
header nav[aria-label="Breadcrumb"] a:hover { text-decoration: underline; }

/* Footer */
footer {
  background: var(--color-footer-bg);
  text-align: center;
  padding: var(--space-md);
  font-size: 0.82rem;
  color: var(--color-text-muted);
  margin-top: var(--space-xl);
}
footer a { color: var(--color-primary); }
"""

_PREVIEW_JS = """\
/* business-fullstack-creater portal — preview.js (generated) */
(function () {
  'use strict';

  function init() {
    setupTabs();
    setupLaneRadios();
    setupCopyButtons();
  }

  /* --- Tab switching ---------------------------------------------------- */
  function setupTabs() {
    var tabBar = document.querySelector('.tab-bar[role="tablist"]');
    if (!tabBar) return;

    tabBar.addEventListener('click', function (e) {
      var btn = e.target.closest('[role="tab"]');
      if (!btn) return;

      var tabName = btn.getAttribute('data-tab');

      // Update aria-selected
      tabBar.querySelectorAll('[role="tab"]').forEach(function (t) {
        t.setAttribute('aria-selected', t === btn ? 'true' : 'false');
      });

      // Show/hide preview blocks for the active tab
      var activeLane = getActiveLane();
      document.querySelectorAll('.preview-block').forEach(function (block) {
        var matchTab = block.getAttribute('data-tab') === tabName;
        var matchLane = block.getAttribute('data-lane') === activeLane;
        block.hidden = !(matchTab && matchLane);
      });
    });
  }

  /* --- Lane radio change ------------------------------------------------ */
  function setupLaneRadios() {
    document.querySelectorAll('input[name="lane"]').forEach(function (radio) {
      radio.addEventListener('change', function () {
        var lane = radio.value;
        var activeTab = getActiveTab();

        // Filter preview blocks
        document.querySelectorAll('.preview-block').forEach(function (block) {
          var matchTab = block.getAttribute('data-tab') === activeTab;
          var matchLane = block.getAttribute('data-lane') === lane;
          block.hidden = !(matchTab && matchLane);
        });

        // Update download href
        document.querySelectorAll('.btn-download').forEach(function (a) {
          var href = a.getAttribute('href') || '';
          // Replace lane segment: ../scaffolds/<slug>/<old-lane>/project.zip
          a.setAttribute('href', href.replace(/\/scaffolds\/([^/]+)\/[^/]+\/project\.zip/, '/scaffolds/$1/' + lane + '/project.zip'));
        });
      });
    });
  }

  /* --- Copy to clipboard ------------------------------------------------ */
  function setupCopyButtons() {
    document.querySelectorAll('.copy-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var targetId = btn.getAttribute('data-target');
        var el = targetId ? document.getElementById(targetId) : null;
        if (!el) return;

        var text = el.textContent || '';
        if (!navigator.clipboard) return;

        navigator.clipboard.writeText(text).then(function () {
          var orig = btn.textContent;
          btn.textContent = 'Copied!';
          setTimeout(function () { btn.textContent = orig; }, 1500);
        });
      });
    });
  }

  /* --- Helpers ---------------------------------------------------------- */
  function getActiveLane() {
    var checked = document.querySelector('input[name="lane"]:checked');
    return checked ? checked.value : 'jakarta';
  }

  function getActiveTab() {
    var active = document.querySelector('[role="tab"][aria-selected="true"]');
    return active ? active.getAttribute('data-tab') : 'ddl';
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
"""


def _write_assets(docs_root: Path) -> None:
    """Write style.css and preview.js into docs_root/assets/."""
    assets_dir = docs_root / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    (assets_dir / "style.css").write_text(_STYLE_CSS, encoding="utf-8")
    (assets_dir / "preview.js").write_text(_PREVIEW_JS, encoding="utf-8")


# ---------------------------------------------------------------------------
# HTML rendering functions (M3)
# ---------------------------------------------------------------------------

_INDEX_PITCH = (
    "복리식 축적 — 사용할수록 쌓이는 도메인 지식 기반의 풀스택 스캐폴드 생성기"
)


def render_index_html(
    matrix: list[MatrixEntry],
    domains: list["Domain"],
    *,
    build_date: str,
) -> str:
    """Return full index.html string per spec §5."""
    # Build per-domain chip map: {domain_name: [(lane, status), ...]}
    chip_map: dict[str, list[tuple[str, str]]] = {}
    for entry in matrix:
        chip_map.setdefault(entry.domain, []).append((entry.lane, entry.status))

    tiles_html: list[str] = []
    for domain in domains:
        slug = domain.name
        encoded_slug = urllib.parse.quote(slug, safe="")
        summary = _escape_html(domain.summary or "")
        display_name = _escape_html(slug)

        chips: list[str] = []
        for lane, status in chip_map.get(slug, []):
            css_class = "verified" if status == "verified" else "default-unverified"
            chips.append(
                f'<span class="chip {css_class}">{_escape_html(lane)}</span>'
            )
        chip_row = "".join(chips)

        tiles_html.append(
            f'<div class="tile" data-domain="{_escape_html(encoded_slug)}">\n'
            f'  <h3><a href="domain/{encoded_slug}.html">{display_name}</a></h3>\n'
            f'  <p class="summary">{summary}</p>\n'
            f'  <div class="chip-row">{chip_row}</div>\n'
            f'</div>'
        )

    tiles = "\n        ".join(tiles_html)
    domain_count = len(domains)
    pitch = _escape_html(_INDEX_PITCH)
    build_date_esc = _escape_html(build_date)

    return (
        "<!DOCTYPE html>\n"
        '<html lang="ko">\n'
        "<head>\n"
        '  <meta charset="UTF-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        "  <title>business-fullstack-creater — Domain Portal</title>\n"
        '  <link rel="stylesheet" href="assets/style.css">\n'
        "</head>\n"
        "<body>\n"
        "  <header>\n"
        "    <h1>business-fullstack-creater</h1>\n"
        f'    <p class="tagline">{pitch}</p>\n'
        "    <nav>\n"
        '      <a href="https://github.com/masonmore/business-fullstack-creater">GitHub</a>\n'
        '      <a href="USER-GUIDE.md">User Guide</a>\n'
        "    </nav>\n"
        "  </header>\n"
        "\n"
        "  <main>\n"
        '    <section aria-label="Domain tiles">\n'
        f"      <h2>{domain_count} Preset Domains</h2>\n"
        '      <div class="tile-grid">\n'
        f"        {tiles}\n"
        "      </div>\n"
        "    </section>\n"
        "  </main>\n"
        "\n"
        "  <footer>\n"
        f'    <p>Generated {build_date_esc} · <a href="https://github.com/masonmore/business-fullstack-creater">source</a></p>\n'
        "  </footer>\n"
        "</body>\n"
        "</html>\n"
    )


def render_domain_html(
    domain: "Domain",
    lane_entries: list[MatrixEntry],
    build_date: str,
    source_files: dict[str, dict[str, str]],  # {lane: {"DDL.sql": "...", "Mapper.xml": "...", ...}}
) -> str:
    """Return full per-domain page HTML per spec §5.

    source_files keys per lane: "DDL.sql", "Mapper.xml", "Controller.java", "Service.java".
    Values are raw file content strings — this function HTML-escapes them before insertion.
    """
    slug = domain.name
    encoded_slug = urllib.parse.quote(slug, safe="")
    display_name = _escape_html(slug)
    summary = _escape_html(domain.summary or "")
    build_date_esc = _escape_html(build_date)

    # Lane radios — first lane gets checked
    lane_list = [e.lane for e in lane_entries]
    # deduplicate while preserving order
    seen_lanes: list[str] = []
    for ln in lane_list:
        if ln not in seen_lanes:
            seen_lanes.append(ln)
    if not seen_lanes:
        seen_lanes = ["jakarta"]

    default_lane = seen_lanes[0]

    radio_items: list[str] = []
    for i, ln in enumerate(seen_lanes):
        checked = " checked" if i == 0 else ""
        radio_items.append(
            f'  <label><input type="radio" name="lane" value="{_escape_html(ln)}"{checked}> {_escape_html(ln)}</label>'
        )
    radios_html = "\n".join(radio_items)

    # Detect dialect from first verified lane or default
    dialect = "MySQL"

    layer_cards = (
        '  <div class="layer-cards">\n'
        '    <div class="layer-card" data-layer="skill">Stage 1 — Blueprint seed</div>\n'
        f'    <div class="layer-card" data-layer="ddl">Stage 2 — DDL ({_escape_html(dialect)})</div>\n'
        '    <div class="layer-card" data-layer="mybatis">Stage 3 — MyBatis / Spring</div>\n'
        '    <div class="layer-card" data-layer="nexacro">Stage 4+5 — Nexacro overlay</div>\n'
        "  </div>"
    )

    layer_selector = (
        '<fieldset class="lane-radios">\n'
        "  <legend>Lane</legend>\n"
        f"{radios_html}\n"
        "</fieldset>\n"
        f"{layer_cards}"
    )

    # Preview tabs — one <pre> per (tab, lane)
    # tab_name → filename mapping
    tab_file_map = [
        ("ddl",        "DDL.sql"),
        ("mapper",     "Mapper.xml"),
        ("controller", "Controller.java"),
        ("service",    "Service.java"),
    ]
    preview_blocks: list[str] = []
    first_block = True
    for tab, fname in tab_file_map:
        for lane in seen_lanes:
            lane_files = source_files.get(lane, {})
            raw_content = lane_files.get(fname, "")
            if raw_content:
                escaped_content = _escape_html(raw_content)
            else:
                escaped_content = "<!-- not available -->"
            hidden_attr = "" if first_block else " hidden"
            first_block = False
            preview_blocks.append(
                f'<pre class="preview-block"\n'
                f'     data-tab="{_escape_html(tab)}"\n'
                f'     data-lane="{_escape_html(lane)}"{hidden_attr}>{escaped_content}</pre>'
            )

    preview_tabs_html = "\n      ".join(preview_blocks)

    # Try-it panel
    try_it_panel = (
        '<div class="try-it">\n'
        f'  <a class="btn-download" href="../scaffolds/{encoded_slug}/{_escape_html(default_lane)}/project.zip"\n'
        "     download>Download project.zip</a>\n"
        '  <div class="snippet-block">\n'
        '    <button class="copy-btn" data-target="run-snippet">Copy</button>\n'
        f'    <pre id="run-snippet">cd {_escape_html(encoded_slug)}-scaffold &amp;&amp; mvn spring-boot:run</pre>\n'
        "  </div>\n"
        "</div>"
    )

    return (
        "<!DOCTYPE html>\n"
        '<html lang="ko">\n'
        "<head>\n"
        '  <meta charset="UTF-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f"  <title>{display_name} — business-fullstack-creater</title>\n"
        '  <link rel="stylesheet" href="../assets/style.css">\n'
        '  <script src="../assets/preview.js" defer></script>\n'
        "</head>\n"
        "<body>\n"
        "  <header>\n"
        '    <nav aria-label="Breadcrumb">\n'
        '      <a href="../index.html">Home</a> / <span>' + display_name + "</span>\n"
        "    </nav>\n"
        f"    <h1>{display_name}</h1>\n"
        f'    <p class="summary">{summary}</p>\n'
        "  </header>\n"
        "\n"
        "  <main>\n"
        '    <section aria-label="Layer selector" class="layer-selector">\n'
        f"      {layer_selector}\n"
        "    </section>\n"
        "\n"
        '    <section aria-label="File preview" class="preview-pane" id="preview-pane">\n'
        '      <nav class="tab-bar" role="tablist">\n'
        '        <button role="tab" aria-selected="true"  data-tab="ddl">DDL</button>\n'
        '        <button role="tab" aria-selected="false" data-tab="mapper">Mapper</button>\n'
        '        <button role="tab" aria-selected="false" data-tab="controller">Controller</button>\n'
        '        <button role="tab" aria-selected="false" data-tab="service">Service</button>\n'
        "      </nav>\n"
        f"      {preview_tabs_html}\n"
        "    </section>\n"
        "\n"
        '    <section aria-label="Try it" class="try-it-panel" id="try-it-panel">\n'
        f"      {try_it_panel}\n"
        "    </section>\n"
        "  </main>\n"
        "\n"
        "  <footer>\n"
        f"    <p>Generated {build_date_esc}</p>\n"
        "  </footer>\n"
        "</body>\n"
        "</html>\n"
    )


def _load_scaffold_preview(
    domain_slug: str,
    lane: str,
    docs_root: Path,
) -> dict[str, str]:
    """Load scaffold preview file contents from docs_root/scaffolds/<slug>/<lane>/.

    Returns dict keyed by filename: {"DDL.sql": "...", "Mapper.xml": "...", ...}.
    Missing files produce empty string values.
    """
    lane_dir = docs_root / "scaffolds" / domain_slug / lane
    filenames = ("DDL.sql", "Mapper.xml", "Controller.java", "Service.java")
    result: dict[str, str] = {}
    for fname in filenames:
        fpath = lane_dir / fname
        if fpath.exists():
            result[fname] = fpath.read_text(encoding="utf-8")
        else:
            result[fname] = ""
    return result


def _load_all_lane_previews(
    domain_slug: str,
    lanes: list[str],
    docs_root: Path,
) -> dict[str, dict[str, str]]:
    """Load preview files for all lanes of a domain.

    Returns {lane: {"DDL.sql": "...", ...}} — shape expected by render_domain_html.
    """
    return {lane: _load_scaffold_preview(domain_slug, lane, docs_root) for lane in lanes}


# ---------------------------------------------------------------------------
# Core build function
# ---------------------------------------------------------------------------

def build(
    domains: Optional[list[str]] = None,        # None = all domains from list_domains.py
    check_only: bool = False,                   # True = verify outputs exist; no writes
    json_output: bool = False,                  # True = emit JSON report to stdout
    docs_root: Optional[Path] = None,           # override for tests; None → DOCS_ROOT
    learn_log_path: Optional[Path] = None,      # override for tests; None → LEARN_LOG
    source_resolver: Optional[Callable[["MatrixEntry"], dict]] = None,  # injected for tests
) -> BuildResult:
    """Build (or check) the static portal.

    M2: scaffold pre-generation via materialize_scaffold() for all matrix entries.
    Full HTML generation is handled in M3.
    """
    # Resolve defaults at call time so monkeypatch on module-level DOCS_ROOT/LEARN_LOG
    # in tests takes effect (Growth-52 lesson: keyword defaults bind at def time).
    if docs_root is None:
        docs_root = DOCS_ROOT
    if learn_log_path is None:
        learn_log_path = LEARN_LOG

    result = BuildResult()

    # Load domain list — gracefully handle missing INDEX.md (e.g. in CI)
    try:
        all_domains = load_domains()
    except FileNotFoundError:
        all_domains = []

    # Filter to requested domains if specified
    if domains:
        slug_set = set(domains)
        filtered = [d for d in all_domains if d.name in slug_set]
        unknown = slug_set - {d.name for d in filtered}
        for u in sorted(unknown):
            result.warnings.append(f"unknown domain slug: {u}")
        all_domains = filtered

    # Build matrix (always, even in check_only — it drives expected paths)
    matrix = build_matrix(all_domains, learn_log_path=learn_log_path)

    if check_only:
        expected = _expected_output_paths(matrix, docs_root)
        for rel_path in expected:
            full = docs_root / rel_path
            if not full.exists():
                result.missing_files.append(rel_path)
        # domains_ok / domains_failed not relevant in check-only mode
    else:
        # T-Web-EmptyPortal (Growth-57): record catalog-root presence up front
        # so empty-portal detection survives even if later steps short-circuit.
        result.catalog_root_missing = not (
            Path.home() / ".karpathy-rdb" / "catalog"
        ).exists()

        # M2: materialize scaffolds for each matrix entry
        seen_domains: set[str] = set()
        for entry in matrix:
            ok, warns = materialize_scaffold(entry, docs_root, source_resolver=source_resolver)
            result.warnings.extend(warns)
            # Per-file placeholder write produces exactly one warning ending in
            # "using placeholder" — count those to tally placeholder vs real slots.
            result.placeholder_slots += sum(1 for w in warns if w.endswith("using placeholder"))
            result.total_slots += len(_PREVIEW_FILE_KEYS)  # 4 preview files per entry
            if ok:
                seen_domains.add(entry.domain)
            else:
                if entry.domain not in result.domains_failed:
                    result.domains_failed.append(entry.domain)

        # domains_ok = all domains that had at least one successful entry
        # (and did not fail entirely)
        for d in all_domains:
            if d.name not in result.domains_failed:
                result.domains_ok.append(d.name)

        # M3: write CSS/JS assets
        _write_assets(docs_root)

        # M3: render index.html
        import datetime
        build_date = datetime.date.today().isoformat()
        (docs_root / "domain").mkdir(parents=True, exist_ok=True)

        index_html = render_index_html(matrix, all_domains, build_date=build_date)
        (docs_root / "index.html").write_text(index_html, encoding="utf-8")

        # M3: render per-domain pages
        # Build per-domain lane list from matrix
        domain_lanes: dict[str, list[str]] = {}
        for entry in matrix:
            domain_lanes.setdefault(entry.domain, [])
            if entry.lane not in domain_lanes[entry.domain]:
                domain_lanes[entry.domain].append(entry.lane)

        domain_map = {d.name: d for d in all_domains}

        for domain in all_domains:
            slug = domain.name
            lanes = domain_lanes.get(slug, ["jakarta"])
            lane_entries = [e for e in matrix if e.domain == slug]
            source_files = _load_all_lane_previews(slug, lanes, docs_root)
            try:
                domain_html = render_domain_html(domain, lane_entries, build_date, source_files)
                encoded_slug = urllib.parse.quote(slug, safe="")
                (docs_root / "domain" / f"{encoded_slug}.html").write_text(
                    domain_html, encoding="utf-8"
                )
            except Exception as exc:
                result.warnings.append(f"{slug}: domain page render failed ({exc})")

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m scripts.workflow.web_index",
        description=(
            "Static portal generator for business-fullstack-creater.\n\n"
            "Builds a fully-static HTML portal under docs/ that exposes all\n"
            "verified domains as a tile grid with per-domain detail pages."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--domain",
        metavar="SLUG",
        help="Rebuild one domain only (slug must match a Domain.name from list_domains.py)",
    )
    p.add_argument(
        "--check",
        action="store_true",
        help="Verify every expected output file exists; print missing list; no writes",
    )
    p.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Emit a JSON BuildResult dict to stdout instead of human-readable output",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        # argparse calls sys.exit(2) on bad args, sys.exit(0) on --help
        return int(e.code) if e.code is not None else 2

    domains = [args.domain] if args.domain else None

    result = build(
        domains=domains,
        check_only=args.check,
        json_output=args.json_output,
    )

    if args.json_output:
        sys.stdout.write(json.dumps(asdict(result), ensure_ascii=False, indent=2))
        sys.stdout.write("\n")
    else:
        if args.check:
            if result.missing_files:
                print(f"MISSING ({len(result.missing_files)} files):")
                for f in result.missing_files:
                    print(f"  {f}")
            else:
                print("OK — all expected output files present.")
        else:
            built = len(result.domains_ok)
            failed = len(result.domains_failed)
            print(f"Build complete: {built} domains OK, {failed} failed.")

        # T-Web-EmptyPortal (Growth-57): summary banner if any preview slot
        # fell back to placeholder. Printed once, before the per-warning dump,
        # so users notice the actionable hint before scrolling through detail.
        if result.placeholder_slots > 0:
            tag = "EMPTY-PORTAL" if result.placeholder_slots == result.total_slots else "PARTIAL-PORTAL"
            reason = (
                " (no catalog found at ~/.karpathy-rdb/catalog/)"
                if result.catalog_root_missing
                else ""
            )
            print(
                f"⚠ {tag}: {result.placeholder_slots}/{result.total_slots} preview slots "
                f"filled with placeholder{reason}. Run `/scaffold <domain>` first to expose "
                f"real DDL/Mapper/Controller/Service content.",
                file=sys.stderr,
            )

        for w in result.warnings:
            print(f"WARNING: {w}", file=sys.stderr)

    # Exit code: 0=success, 1=partial/missing, 2=bad args
    if result.missing_files or result.domains_failed:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
