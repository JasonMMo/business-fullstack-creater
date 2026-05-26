"""Tests for list_domains.py — R4 (서비스 리뷰 2026-05-26).

Verifies INDEX.md parsing, table/JSON formatting, and CLI smoke against the
real INDEX.md in the sibling rdb-skill repo.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.workflow import list_domains


SAMPLE_INDEX = """\
---
type: preset-index
---

# Preset Catalog Index

## 결재
- aliases: 승인, 전자결재, approval
- keywords: 결재요청, 결재라인
- entities: approval_template, approval_request
- 한 줄: 한국 SI 표준 — 순차/병렬/혼합 결재 라인

## 고객관리
- aliases: CRM, 회원관리
- keywords: 고객, 연락처
- entities: customer, customer_category
- 한 줄: B2C/B2B 고객 + 다중 주소 + 분류 트리

---

## 매칭 알고리즘 (LLM이 따를 절차)

1. ...
"""


def test_parse_skips_matching_algorithm_section():
    domains = list_domains.parse_index_md(SAMPLE_INDEX)
    assert [d.name for d in domains] == ["결재", "고객관리"]


def test_parse_extracts_aliases_keywords_entities_summary():
    domains = list_domains.parse_index_md(SAMPLE_INDEX)
    d = domains[0]
    assert d.aliases == ["승인", "전자결재", "approval"]
    assert d.keywords == ["결재요청", "결재라인"]
    assert d.entities == ["approval_template", "approval_request"]
    assert "순차/병렬/혼합" in d.summary


def test_format_table_default_one_line_per_domain():
    domains = list_domains.parse_index_md(SAMPLE_INDEX)
    out = list_domains.format_table(domains, verbose=False)
    assert "2 preset domains:" in out
    assert "결재" in out and "한국 SI 표준" in out
    # default form omits aliases line
    assert "aliases:" not in out


def test_format_table_verbose_includes_aliases_and_entities():
    domains = list_domains.parse_index_md(SAMPLE_INDEX)
    out = list_domains.format_table(domains, verbose=True)
    assert "aliases:" in out and "전자결재" in out
    assert "entities:" in out and "approval_request" in out


def test_format_table_empty_input():
    assert list_domains.format_table([]) == "(no domains found)"


def test_cli_json_smoke(tmp_path, capsys):
    idx = tmp_path / "INDEX.md"
    idx.write_text(SAMPLE_INDEX, encoding="utf-8")
    rc = list_domains.main(["--index", str(idx), "--json"])
    captured = capsys.readouterr()
    assert rc == 0
    data = json.loads(captured.out)
    assert len(data) == 2
    assert data[0]["name"] == "결재"
    assert "approval_template" in data[0]["entities"]


def test_cli_missing_index_returns_error_code(tmp_path, capsys):
    rc = list_domains.main(["--index", str(tmp_path / "missing.md")])
    captured = capsys.readouterr()
    assert rc == 1
    assert "ERROR" in captured.err


# Real INDEX.md smoke — guards against future shape drift in the catalog
def test_real_index_md_has_14_domains():
    if not list_domains.DEFAULT_INDEX_PATH.exists():
        pytest.skip(f"sibling repo INDEX.md not found at {list_domains.DEFAULT_INDEX_PATH}")
    domains = list_domains.load_domains()
    assert len(domains) == 14
    names = {d.name for d in domains}
    assert {"결재", "고객관리", "주문관리", "재무관리"}.issubset(names)
    # every domain has a non-empty summary
    for d in domains:
        assert d.summary, f"empty summary for {d.name}"
