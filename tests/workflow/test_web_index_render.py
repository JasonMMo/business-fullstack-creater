"""Tests for scripts/workflow/web_index.py — M3 HTML/CSS/JS rendering.

Covers render_index_html(), render_domain_html(), and the extended build()
that writes index.html, per-domain pages, and assets.

All tests use synthetic Domain/MatrixEntry objects and do NOT depend on
real ~/.karpathy-rdb/catalog or the live learn-log.md.
"""
from __future__ import annotations

import unittest.mock as mock
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_domain(name: str, summary: str = "A test domain"):
    from scripts.workflow.list_domains import Domain
    return Domain(name=name, summary=summary)


def _make_entry(domain: str, lane: str, status: str = "verified"):
    from scripts.workflow.web_index import MatrixEntry
    return MatrixEntry(domain=domain, lane=lane, status=status, source="test")


def _null_resolver(entry):
    return {"ddl": None, "mapper_xml": None, "controller": None, "service": None}


# ---------------------------------------------------------------------------
# Test 1 — render_index_html: all domain tiles present
# ---------------------------------------------------------------------------

def test_render_index_html_contains_all_domain_tiles():
    """Given 3 domains, output contains 3 tile divs."""
    from scripts.workflow.web_index import render_index_html, MatrixEntry

    domains = [_make_domain("alpha"), _make_domain("beta"), _make_domain("gamma")]
    matrix = [
        _make_entry("alpha", "jakarta"),
        _make_entry("beta",  "jakarta"),
        _make_entry("gamma", "javax", "default-unverified"),
    ]
    html = render_index_html(matrix, domains, build_date="2026-05-26")

    assert html.count('class="tile"') == 3, (
        f"Expected 3 tile divs, found {html.count('class=\"tile\"')}"
    )


# ---------------------------------------------------------------------------
# Test 2 — render_index_html: Korean slug href is percent-encoded
# ---------------------------------------------------------------------------

def test_render_index_html_escapes_korean_slug_in_href():
    """Korean domain slug like '고객관리' produces a percent-encoded href."""
    import urllib.parse
    from scripts.workflow.web_index import render_index_html

    slug = "고객관리"
    domains = [_make_domain(slug)]
    matrix = [_make_entry(slug, "jakarta")]
    html = render_index_html(matrix, domains, build_date="2026-05-26")

    encoded = urllib.parse.quote(slug, safe="")
    assert encoded in html, f"Expected percent-encoded slug '{encoded}' in href"
    # Raw Korean characters should NOT appear in href="domain/..." context
    assert f'href="domain/{slug}.html"' not in html, (
        "Raw Korean slug must not appear unencoded in href"
    )


# ---------------------------------------------------------------------------
# Test 3 — render_index_html: verified vs unverified produce different chip classes
# ---------------------------------------------------------------------------

def test_render_index_html_shows_status_chips():
    """verified entry → chip.verified; default-unverified → chip.default-unverified."""
    from scripts.workflow.web_index import render_index_html

    domains = [_make_domain("svc")]
    matrix = [
        _make_entry("svc", "jakarta",  "verified"),
        _make_entry("svc", "nexacro",  "default-unverified"),
    ]
    html = render_index_html(matrix, domains, build_date="2026-05-26")

    assert 'class="chip verified"' in html, "Missing verified chip"
    assert 'class="chip default-unverified"' in html, "Missing default-unverified chip"


# ---------------------------------------------------------------------------
# Test 4 — render_domain_html: lane radio inputs present per lane entry
# ---------------------------------------------------------------------------

def test_render_domain_html_has_lane_radios():
    """Output has one <input type="radio" name="lane"> per distinct lane."""
    from scripts.workflow.web_index import render_domain_html

    domain = _make_domain("order")
    entries = [
        _make_entry("order", "jakarta"),
        _make_entry("order", "javax"),
    ]
    source_files = {
        "jakarta": {"DDL.sql": "CREATE TABLE order_tbl (id INT);", "Mapper.xml": "", "Controller.java": "", "Service.java": ""},
        "javax":   {"DDL.sql": "CREATE TABLE order_tbl (id INT);", "Mapper.xml": "", "Controller.java": "", "Service.java": ""},
    }
    html = render_domain_html(domain, entries, "2026-05-26", source_files)

    radio_count = html.count('type="radio" name="lane"')
    assert radio_count == 2, f"Expected 2 lane radios, found {radio_count}"


# ---------------------------------------------------------------------------
# Test 5 — render_domain_html: four preview tab buttons + first not hidden
# ---------------------------------------------------------------------------

def test_render_domain_html_has_four_preview_tabs():
    """DDL/Mapper/Controller/Service tabs present; first (ddl) block not hidden."""
    from scripts.workflow.web_index import render_domain_html

    domain = _make_domain("product")
    entries = [_make_entry("product", "jakarta")]
    source_files = {
        "jakarta": {
            "DDL.sql": "CREATE TABLE product (id INT);",
            "Mapper.xml": "<mapper/>",
            "Controller.java": "class ProductController {}",
            "Service.java": "class ProductService {}",
        }
    }
    html = render_domain_html(domain, entries, "2026-05-26", source_files)

    for tab in ("ddl", "mapper", "controller", "service"):
        assert f'data-tab="{tab}"' in html, f"Missing data-tab={tab}"

    # The first <pre class="preview-block"> must NOT have hidden attr
    import re
    first_pre = re.search(r'<pre class="preview-block"', html)
    assert first_pre, "No preview-block found"
    # Extract chunk from first <pre> to the end of its opening tag (up to >)
    chunk = html[first_pre.start(): html.index(">", first_pre.start()) + 1]
    assert "hidden" not in chunk, f"First preview block must not be hidden; got: {chunk!r}"


# ---------------------------------------------------------------------------
# Test 6 — render_domain_html: HTML-escapes source code with < > &
# ---------------------------------------------------------------------------

def test_render_domain_html_escapes_source_html():
    """Source content containing <script> is escaped to &lt;script&gt; in <pre>."""
    from scripts.workflow.web_index import render_domain_html

    domain = _make_domain("vuln")
    entries = [_make_entry("vuln", "jakarta")]
    source_files = {
        "jakarta": {
            "DDL.sql": "<script>alert('xss')</script> & more",
            "Mapper.xml": "",
            "Controller.java": "",
            "Service.java": "",
        }
    }
    html = render_domain_html(domain, entries, "2026-05-26", source_files)

    assert "&lt;script&gt;" in html, "< in source must be escaped to &lt;"
    assert "&amp;" in html, "& in source must be escaped to &amp;"
    assert "<script>" not in html, "Raw <script> must not appear in output"


# ---------------------------------------------------------------------------
# Test 7 — render_domain_html: try-it panel has download anchor + copy button
# ---------------------------------------------------------------------------

def test_render_domain_html_try_it_panel_has_download_and_copy():
    """try-it panel contains an <a download> anchor and a .copy-btn button."""
    from scripts.workflow.web_index import render_domain_html

    domain = _make_domain("invoice")
    entries = [_make_entry("invoice", "jakarta")]
    source_files = {"jakarta": {"DDL.sql": "", "Mapper.xml": "", "Controller.java": "", "Service.java": ""}}
    html = render_domain_html(domain, entries, "2026-05-26", source_files)

    assert "download" in html, "Missing 'download' attribute on anchor"
    assert 'class="copy-btn"' in html, "Missing copy-btn class"
    assert 'class="btn-download"' in html, "Missing btn-download class"


# ---------------------------------------------------------------------------
# Test 8 — build(): writes index.html + domain page + assets
# ---------------------------------------------------------------------------

def test_build_writes_index_and_domain_pages(tmp_path):
    """build(domains=[Domain(...)], docs_root=tmp_path) produces all expected files."""
    from scripts.workflow.web_index import build
    from scripts.workflow.list_domains import Domain

    docs_root = tmp_path / "docs"
    docs_root.mkdir()

    fake_domains = [Domain(name="customer", summary="고객 관리")]

    # minimal learn-log — customer+jakarta verified
    ll = tmp_path / "learn-log.md"
    ll.write_text(
        "# learn-log\n\n"
        "## 1. 라이브 WAS 검증대 상태\n\n"
        "| lane | 디폴트 러너 | 검증 상태 | 비고 |\n"
        "|---|---|---|---|\n"
        "| **jakarta** | runner | ✅ Growth-10 (customer) | - |\n"
        "\n## 2.\n",
        encoding="utf-8",
    )

    with mock.patch("scripts.workflow.web_index.load_domains", return_value=fake_domains):
        result = build(
            docs_root=docs_root,
            learn_log_path=ll,
            source_resolver=_null_resolver,
        )

    # index.html
    index_file = docs_root / "index.html"
    assert index_file.exists(), "index.html was not written"
    index_content = index_file.read_text(encoding="utf-8")
    assert 'class="tile"' in index_content, "index.html missing tile"

    # domain page — customer slug is ASCII so no encoding needed
    domain_file = docs_root / "domain" / "customer.html"
    assert domain_file.exists(), "domain/customer.html was not written"

    # assets
    assert (docs_root / "assets" / "style.css").exists(), "style.css not written"
    assert (docs_root / "assets" / "preview.js").exists(), "preview.js not written"


# ---------------------------------------------------------------------------
# Test 9 — build(): assets written even with no domains
# ---------------------------------------------------------------------------

def test_build_writes_assets_even_if_no_domains(tmp_path):
    """Assets (style.css, preview.js) are always written; index.html has 0 tiles."""
    from scripts.workflow.web_index import build

    docs_root = tmp_path / "docs"
    docs_root.mkdir()

    # Empty learn-log, no domains
    ll = tmp_path / "learn-log.md"
    ll.write_text("# learn-log\n\n## 1.\n\n## 2.\n", encoding="utf-8")

    with mock.patch("scripts.workflow.web_index.load_domains", return_value=[]):
        result = build(
            docs_root=docs_root,
            learn_log_path=ll,
            source_resolver=_null_resolver,
        )

    assert (docs_root / "assets" / "style.css").exists(), "style.css must be written even with 0 domains"
    assert (docs_root / "assets" / "preview.js").exists(), "preview.js must be written even with 0 domains"

    index_file = docs_root / "index.html"
    assert index_file.exists(), "index.html must be written even with 0 domains"
    index_content = index_file.read_text(encoding="utf-8")
    assert index_content.count('class="tile"') == 0, "0 domains → 0 tiles"


# ---------------------------------------------------------------------------
# Test 10 — render_index_html: build_date and domain count appear in output
# ---------------------------------------------------------------------------

def test_render_index_html_build_date_and_count():
    """BUILD_DATE and DOMAIN_COUNT slots are filled in rendered output."""
    from scripts.workflow.web_index import render_index_html

    domains = [_make_domain("aaa"), _make_domain("bbb")]
    matrix = [_make_entry("aaa", "jakarta"), _make_entry("bbb", "jakarta")]
    html = render_index_html(matrix, domains, build_date="2099-12-31")

    assert "2099-12-31" in html, "BUILD_DATE not in output"
    assert "2 Preset Domains" in html, "DOMAIN_COUNT not in output"
