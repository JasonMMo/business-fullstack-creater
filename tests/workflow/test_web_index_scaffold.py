"""Tests for scripts/workflow/web_index.py — M2 scaffold pre-generation.

Covers materialize_scaffold() and the wired-in build() scaffold pass.
All tests use source_resolver injection — no real ~/.karpathy-rdb/ access.
"""
from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entry(domain: str = "foo", lane: str = "jakarta", status: str = "verified"):
    from scripts.workflow.web_index import MatrixEntry
    return MatrixEntry(domain=domain, lane=lane, status=status, source="test")


def _real_source_resolver(tmp_path: Path):
    """Build a fake source tree in tmp_path, return a source_resolver callable."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    # Create four source files
    ddl = tmp_path / "foo-schema.sql"
    ddl.write_text("CREATE TABLE foo (id INT);\n", encoding="utf-8")

    mapper_xml = tmp_path / "FooMapper.xml"
    mapper_xml.write_text("<mapper namespace='FooMapper'/>\n", encoding="utf-8")

    controller = tmp_path / "FooController.java"
    controller.write_text("public class FooController {}\n", encoding="utf-8")

    service = tmp_path / "FooService.java"
    service.write_text("public class FooService {}\n", encoding="utf-8")

    def resolver(entry):
        return {
            "ddl":        ddl,
            "mapper_xml": mapper_xml,
            "controller": controller,
            "service":    service,
        }

    return resolver


def _null_resolver(entry):
    """Returns None for all keys — triggers placeholder path."""
    return {"ddl": None, "mapper_xml": None, "controller": None, "service": None}


def _make_domains(names: list[str]):
    from scripts.workflow.list_domains import Domain
    return [Domain(name=n) for n in names]


def _fake_learn_log(tmp_path: Path, rows: list[tuple[str, str, str]]) -> Path:
    header = (
        "# learn-log\n\n"
        "## 1. 라이브 WAS 검증대 상태 (lane × runner)\n\n"
        "| lane | 디폴트 러너 | 검증 상태 | 비고 |\n"
        "|---|---|---|---|\n"
    )
    row_lines = []
    for lane, growth_ref, domain_hint in rows:
        status_cell = f"✅ {growth_ref} ({domain_hint})"
        row_lines.append(f"| **{lane}** | runner | {status_cell} | - |")
    content = header + "\n".join(row_lines) + "\n\n## 2. 누적 도메인\n"
    p = tmp_path / "learn-log.md"
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Test 1 — all four preview files written
# ---------------------------------------------------------------------------

def test_materialize_scaffold_writes_four_preview_files(tmp_path):
    """materialize_scaffold writes DDL.sql, Mapper.xml, Controller.java, Service.java."""
    from scripts.workflow.web_index import materialize_scaffold

    entry = _make_entry("foo", "jakarta")
    docs_root = tmp_path / "docs"
    docs_root.mkdir()
    resolver = _real_source_resolver(tmp_path / "src")

    ok, warnings = materialize_scaffold(entry, docs_root, source_resolver=resolver)

    assert ok is True
    out_dir = docs_root / "scaffolds" / "foo" / "jakarta"
    for fname in ("DDL.sql", "Mapper.xml", "Controller.java", "Service.java"):
        assert (out_dir / fname).exists(), f"{fname} missing from {out_dir}"


# ---------------------------------------------------------------------------
# Test 2 — project.zip valid + contains expected entries
# ---------------------------------------------------------------------------

def test_materialize_scaffold_creates_valid_zip(tmp_path):
    """project.zip exists and is a valid zip containing the four preview files."""
    from scripts.workflow.web_index import materialize_scaffold

    entry = _make_entry("foo", "jakarta")
    docs_root = tmp_path / "docs"
    docs_root.mkdir()
    resolver = _real_source_resolver(tmp_path / "src")

    ok, warnings = materialize_scaffold(entry, docs_root, source_resolver=resolver)

    assert ok is True
    zip_path = docs_root / "scaffolds" / "foo" / "jakarta" / "project.zip"
    assert zip_path.exists(), "project.zip was not created"
    assert zipfile.is_zipfile(zip_path), "project.zip is not a valid zip file"

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
    for fname in ("DDL.sql", "Mapper.xml", "Controller.java", "Service.java"):
        assert any(fname in n for n in names), f"{fname} not found in zip: {names}"


# ---------------------------------------------------------------------------
# Test 3 — missing source → placeholder + warning
# ---------------------------------------------------------------------------

def test_materialize_scaffold_missing_source_writes_placeholder(tmp_path):
    """When source_resolver returns None, placeholder files are written and warnings recorded."""
    from scripts.workflow.web_index import materialize_scaffold

    entry = _make_entry("bar", "jakarta")
    docs_root = tmp_path / "docs"
    docs_root.mkdir()

    ok, warnings = materialize_scaffold(entry, docs_root, source_resolver=_null_resolver)

    assert ok is True  # missing sources are non-fatal
    out_dir = docs_root / "scaffolds" / "bar" / "jakarta"

    for fname in ("DDL.sql", "Mapper.xml", "Controller.java", "Service.java"):
        fpath = out_dir / fname
        assert fpath.exists(), f"placeholder {fname} missing"
        content = fpath.read_text(encoding="utf-8")
        assert "not available" in content, f"placeholder text missing in {fname}: {content!r}"

    assert len(warnings) >= 4, f"Expected >=4 warnings (one per missing file), got: {warnings}"


# ---------------------------------------------------------------------------
# Test 4 — idempotent: calling twice produces same files without exception
# ---------------------------------------------------------------------------

def test_materialize_scaffold_idempotent(tmp_path):
    """Calling materialize_scaffold twice produces same files without exception."""
    from scripts.workflow.web_index import materialize_scaffold

    entry = _make_entry("baz", "jakarta")
    docs_root = tmp_path / "docs"
    docs_root.mkdir()
    resolver = _real_source_resolver(tmp_path / "src")

    ok1, w1 = materialize_scaffold(entry, docs_root, source_resolver=resolver)
    ok2, w2 = materialize_scaffold(entry, docs_root, source_resolver=resolver)

    assert ok1 is True
    assert ok2 is True

    out_dir = docs_root / "scaffolds" / "baz" / "jakarta"
    for fname in ("DDL.sql", "Mapper.xml", "Controller.java", "Service.java", "project.zip"):
        assert (out_dir / fname).exists(), f"{fname} missing after second call"


# ---------------------------------------------------------------------------
# Test 5 — build() writes scaffolds for all matrix entries
# ---------------------------------------------------------------------------

def test_build_writes_all_matrix_scaffolds(tmp_path):
    """build() with stub matrix calls materialize_scaffold for all entries."""
    from scripts.workflow.web_index import build

    docs_root = tmp_path / "docs"
    docs_root.mkdir()
    ll = _fake_learn_log(tmp_path, [
        ("jakarta", "Growth-10", "foo"),
        ("javax",   "Growth-11", "foo"),
        ("jakarta", "Growth-12", "bar"),
    ])

    # Build a fake source resolver that returns None-paths (placeholders) — fast, no real I/O
    def stub_resolver(entry):
        return {"ddl": None, "mapper_xml": None, "controller": None, "service": None}

    # Patch load_domains so build() doesn't need INDEX.md
    import unittest.mock as mock
    from scripts.workflow.list_domains import Domain

    fake_domains = [Domain(name="foo"), Domain(name="bar")]
    with mock.patch("scripts.workflow.web_index.load_domains", return_value=fake_domains):
        result = build(
            docs_root=docs_root,
            learn_log_path=ll,
            source_resolver=stub_resolver,
        )

    # All entries should have generated scaffold dirs
    assert (docs_root / "scaffolds" / "foo" / "jakarta").exists()
    assert (docs_root / "scaffolds" / "foo" / "javax").exists()
    assert (docs_root / "scaffolds" / "bar" / "jakarta").exists()

    assert "foo" in result.domains_ok or "foo" in result.domains_failed
    assert "bar" in result.domains_ok or "bar" in result.domains_failed


# ---------------------------------------------------------------------------
# Test 6 — --domain filter: only one domain's scaffolds are written
# ---------------------------------------------------------------------------

def test_build_domain_filter_only_writes_one(tmp_path):
    """build(domains=['foo']) does not write scaffolds for 'bar'."""
    from scripts.workflow.web_index import build

    docs_root = tmp_path / "docs"
    docs_root.mkdir()
    ll = _fake_learn_log(tmp_path, [
        ("jakarta", "Growth-10", "foo"),
        ("jakarta", "Growth-12", "bar"),
    ])

    def stub_resolver(entry):
        return {"ddl": None, "mapper_xml": None, "controller": None, "service": None}

    import unittest.mock as mock
    from scripts.workflow.list_domains import Domain

    fake_domains = [Domain(name="foo"), Domain(name="bar")]
    with mock.patch("scripts.workflow.web_index.load_domains", return_value=fake_domains):
        result = build(
            domains=["foo"],
            docs_root=docs_root,
            learn_log_path=ll,
            source_resolver=stub_resolver,
        )

    # foo scaffold should exist
    assert (docs_root / "scaffolds" / "foo" / "jakarta").exists(), \
        "foo/jakarta scaffold missing"

    # bar scaffold must NOT exist (domain filter)
    assert not (docs_root / "scaffolds" / "bar").exists(), \
        "bar scaffold should not have been written when domain=foo"


# ---------------------------------------------------------------------------
# Test 7 — (bonus) mixed resolver: some files real, some missing
# ---------------------------------------------------------------------------

def test_materialize_scaffold_partial_sources(tmp_path):
    """When only DDL source exists, other files get placeholders and warnings are recorded."""
    from scripts.workflow.web_index import materialize_scaffold

    entry = _make_entry("qux", "nexacro")
    docs_root = tmp_path / "docs"
    docs_root.mkdir()

    ddl_file = tmp_path / "qux-schema.sql"
    ddl_file.write_text("CREATE TABLE qux (id INT);\n", encoding="utf-8")

    def partial_resolver(ent):
        return {
            "ddl":        ddl_file,  # real file
            "mapper_xml": None,
            "controller": None,
            "service":    None,
        }

    ok, warnings = materialize_scaffold(entry, docs_root, source_resolver=partial_resolver)

    assert ok is True
    out_dir = docs_root / "scaffolds" / "qux" / "nexacro"

    # DDL from real file — should NOT be a placeholder
    ddl_content = (out_dir / "DDL.sql").read_text(encoding="utf-8")
    assert "not available" not in ddl_content

    # Others should be placeholders
    for fname in ("Mapper.xml", "Controller.java", "Service.java"):
        content = (out_dir / fname).read_text(encoding="utf-8")
        assert "not available" in content, f"{fname} should be placeholder"

    # 3 warnings expected (mapper_xml, controller, service)
    assert len(warnings) >= 3


# ---------------------------------------------------------------------------
# Growth-57 / T-Web-EmptyPortal — domain-aware placeholder + CLI warning
# ---------------------------------------------------------------------------

def test_format_placeholder_embeds_slug_and_scaffold_hint():
    """_format_placeholder turns the empty preview into a tutorial pointer."""
    from scripts.workflow.web_index import _format_placeholder

    body = _format_placeholder("고객관리", "DDL.sql")

    assert "not available" in body              # back-compat substring
    assert "/scaffold 고객관리" in body         # actionable next-command
    assert "~/.karpathy-rdb/catalog/고객관리/" in body  # source-of-truth path
    assert "Stage 2" in body                    # layer hint for DDL.sql


def test_format_placeholder_layer_label_varies_per_file():
    """Each preview filename gets its own Stage label (G57 inline hint)."""
    from scripts.workflow.web_index import _format_placeholder

    assert "Stage 2" in _format_placeholder("foo", "DDL.sql")
    assert "MyBatis Mapper" in _format_placeholder("foo", "Mapper.xml")
    assert "Spring Controller" in _format_placeholder("foo", "Controller.java")
    assert "Spring Service" in _format_placeholder("foo", "Service.java")


def test_build_tallies_placeholder_and_total_slots(tmp_path):
    """build() with null resolver tallies placeholder_slots == total_slots."""
    from scripts.workflow.web_index import build

    docs_root = tmp_path / "docs"
    docs_root.mkdir()
    ll = _fake_learn_log(tmp_path, [
        ("jakarta", "Growth-10", "foo"),
        ("jakarta", "Growth-12", "bar"),
    ])

    import unittest.mock as mock
    from scripts.workflow.list_domains import Domain

    fake_domains = [Domain(name="foo"), Domain(name="bar")]
    with mock.patch("scripts.workflow.web_index.load_domains", return_value=fake_domains):
        result = build(
            docs_root=docs_root,
            learn_log_path=ll,
            source_resolver=_null_resolver,
        )

    # 2 entries × 4 preview files = 8 total slots, all placeholder
    assert result.total_slots == 8
    assert result.placeholder_slots == 8


def test_build_records_catalog_root_missing(tmp_path, monkeypatch):
    """build() flips catalog_root_missing when ~/.karpathy-rdb/catalog/ absent."""
    from scripts.workflow.web_index import build

    docs_root = tmp_path / "docs"
    docs_root.mkdir()
    ll = _fake_learn_log(tmp_path, [("jakarta", "Growth-10", "foo")])

    # Point Path.home() at an empty dir so ~/.karpathy-rdb/catalog/ definitely does NOT exist
    fake_home = tmp_path / "fakehome"
    fake_home.mkdir()
    monkeypatch.setattr("scripts.workflow.web_index.Path.home", lambda: fake_home)

    import unittest.mock as mock
    from scripts.workflow.list_domains import Domain

    with mock.patch("scripts.workflow.web_index.load_domains", return_value=[Domain(name="foo")]):
        result = build(
            docs_root=docs_root,
            learn_log_path=ll,
            source_resolver=_null_resolver,
        )

    assert result.catalog_root_missing is True


def test_cli_main_emits_empty_portal_warning(tmp_path, monkeypatch, capsys):
    """main() prints EMPTY-PORTAL banner with /scaffold hint when all slots are placeholder."""
    from scripts.workflow import web_index

    docs_root = tmp_path / "docs"
    docs_root.mkdir()
    ll = _fake_learn_log(tmp_path, [("jakarta", "Growth-10", "foo")])

    fake_home = tmp_path / "fakehome"
    fake_home.mkdir()
    monkeypatch.setattr("scripts.workflow.web_index.Path.home", lambda: fake_home)
    monkeypatch.setattr(web_index, "DOCS_ROOT", docs_root)
    monkeypatch.setattr(web_index, "LEARN_LOG", ll)

    import unittest.mock as mock
    from scripts.workflow.list_domains import Domain

    with mock.patch("scripts.workflow.web_index.load_domains", return_value=[Domain(name="foo")]):
        rc = web_index.main([])

    captured = capsys.readouterr()
    assert rc == 0
    # Banner went to stderr with all the actionable bits
    assert "EMPTY-PORTAL" in captured.err
    assert "/scaffold <domain>" in captured.err
    assert "~/.karpathy-rdb/catalog/" in captured.err
    assert "4/4 preview slots" in captured.err  # 1 entry × 4 files
