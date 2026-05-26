"""Tests for orient.py — Growth-52 (2026-05-26)."""
from __future__ import annotations

from pathlib import Path

from scripts.workflow import orient


SAMPLE_USER_GUIDE = """\
# business-fullstack-creater 사용자 가이드

> 업무별 fullstack 코드 생성 파이프라인. 한 마디로 nexacroN + Spring Boot.
> 4-stage 코드 생성 도구 모음입니다.

본 문서는 통합 가이드입니다.
"""

SAMPLE_LEARN_LOG = """\
# learn-log.md

## 0. Layer Ownership Card (Phase A — 2026-05-22)

| 축 | 깊이 누적 위치 | 단위 테스트 | 누적 트랩 | 미해결 환류 |
|---|---|---|---|---|
| **skill (Stage 1)** | a | b | 0 | — |
| **ddl (Stage 2)** | a | b | 3 (HSQLDB IDENTITY 0-base, SQL:2008 LEAD) | — |
| **creater (Orchestrator)** | a | b | 4 (javax lane URL, JDK8 source/target) | done |

## 1. next

## 6. Growth 이력 (요약)

| Growth | 일자 | 살붙임 요약 |
|---|---|---|
| Growth-1 ~ Growth-25 | 2026-04 | early growth |
| Growth-43 | 2026-05-22 | karpathy alignment plan 완료 |
| Growth-51 | 2026-05-26 | 서비스 리뷰 R1/R3/R4 환류 — 외부 사용자 첫인상 보강 |
| Growth-48 | 2026-05-22 | T-Probe-LaneRunner-Mismatch 픽스 |

## 7. 사용 규칙
"""


def test_extract_pitch_collapses_blockquote_lines():
    pitch = orient.extract_pitch(SAMPLE_USER_GUIDE)
    assert pitch.startswith("업무별 fullstack")
    assert "4-stage 코드 생성" in pitch
    # multi-line blockquote joined with single spaces
    assert "\n" not in pitch


def test_extract_pitch_no_blockquote_returns_empty():
    assert orient.extract_pitch("# title\n\nbody only\n") == ""


def test_extract_layer_card_returns_axis_and_traps():
    rows = orient.extract_layer_card(SAMPLE_LEARN_LOG)
    assert [r.axis for r in rows] == ["skill (Stage 1)", "ddl (Stage 2)", "creater (Orchestrator)"]
    assert rows[0].traps == "0"
    assert "HSQLDB IDENTITY" in rows[1].traps
    assert rows[2].traps.startswith("4")


def test_extract_layer_card_stops_at_next_section():
    log = SAMPLE_LEARN_LOG + "\n## 0. fake later section\n| **xxx** | a | b | 99 |\n"
    rows = orient.extract_layer_card(log)
    # section header is only matched once at the first occurrence; later lines
    # in §1 are not bold-pipe rows so should not contaminate
    assert all(r.axis != "xxx" for r in rows)


def test_extract_latest_growth_picks_highest_number():
    g = orient.extract_latest_growth(SAMPLE_LEARN_LOG)
    assert g is not None
    assert g.name == "Growth-51"
    assert g.date == "2026-05-26"
    assert "R1/R3/R4" in g.summary


def test_extract_latest_growth_handles_range_entry():
    log = """\
## 6. Growth
| Growth | 일자 | 살붙임 요약 |
|---|---|---|
| Growth-1 ~ Growth-25 | 2026-04 | early |
"""
    g = orient.extract_latest_growth(log)
    assert g is not None
    assert g.name == "Growth-1 ~ Growth-25"


def test_extract_latest_growth_none_when_no_table():
    assert orient.extract_latest_growth("# nothing\n") is None


def test_build_orientation_with_both_files(tmp_path):
    ug = tmp_path / "USER-GUIDE.md"
    ll = tmp_path / "learn-log.md"
    ug.write_text(SAMPLE_USER_GUIDE, encoding="utf-8")
    ll.write_text(SAMPLE_LEARN_LOG, encoding="utf-8")
    o = orient.build_orientation(ug, ll)
    assert "업무별" in o.pitch
    assert len(o.layers) == 3
    assert o.latest is not None and o.latest.name == "Growth-51"


def test_build_orientation_tolerates_missing_files(tmp_path):
    o = orient.build_orientation(tmp_path / "no.md", tmp_path / "no.md")
    assert o.pitch == ""
    assert o.layers == []
    assert o.latest is None


def test_format_orientation_includes_all_sections(tmp_path):
    o = orient.Orientation(
        pitch="hello world",
        layers=[orient.LayerRow("skill", "0"), orient.LayerRow("ddl", "3 (x)")],
        latest=orient.GrowthRow("Growth-51", "2026-05-26", "summary text" * 30),
    )
    out = orient.format_orientation(o, summary_chars=50)
    assert "hello world" in out
    assert "skill" in out and "ddl" in out
    assert "Growth-51" in out
    assert "..." in out  # summary truncated
    assert "/diagnose" in out
    assert "/list-domains" in out


def test_format_orientation_empty_state():
    out = orient.format_orientation(orient.Orientation(pitch=""))
    assert "business-fullstack-creater" in out
    assert "/diagnose" in out  # next-command block always present


def test_cli_smoke(tmp_path, capsys):
    ug = tmp_path / "USER-GUIDE.md"
    ll = tmp_path / "learn-log.md"
    ug.write_text(SAMPLE_USER_GUIDE, encoding="utf-8")
    ll.write_text(SAMPLE_LEARN_LOG, encoding="utf-8")
    rc = orient.main(["--user-guide", str(ug), "--learn-log", str(ll)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "Growth-51" in captured.out
    assert "/diagnose" in captured.out


def test_real_files_smoke(tmp_path):
    """Guard against drift: real USER-GUIDE.md + learn-log.md must still parse."""
    import os
    creater = Path(__file__).resolve().parents[2]
    ug = creater / "docs" / "USER-GUIDE.md"
    ll = creater / "learn-log.md"
    if not (ug.exists() and ll.exists()):
        import pytest
        pytest.skip("real files missing")
    o = orient.build_orientation(ug, ll)
    assert o.pitch, "real USER-GUIDE pitch should be non-empty"
    assert len(o.layers) >= 4, "real learn-log §0 should have ≥4 axes"
    assert o.latest is not None
