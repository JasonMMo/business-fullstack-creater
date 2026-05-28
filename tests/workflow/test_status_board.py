"""Growth-72 — tests for scripts/workflow/status_board.py."""
from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from scripts.workflow import status_board as sb


# ---------------------------------------------------------------------------
# Fixture: synthetic learn-log
# ---------------------------------------------------------------------------

_SYNTH_LEARN_LOG = textwrap.dedent(
    """\
    # learn-log.md — fake

    ## 0. Layer Ownership Card

    head row above.

    ## 1. 라이브 WAS 검증대 상태 (lane × runner)

    | lane | 디폴트 러너 | 검증 상태 | 비고 |
    |---|---|---|---|
    | **nexacro** | runner-a | ✅ Growth-42 (envelope CRUD) | nexacro lane note |
    | **jakarta** | runner-b | ✅ Growth-28 (finance) + Growth-31 (sales) | 2 도메인 횡단 |
    | **javax** | runner-c | ⚠️ Growth-47 (partial) | JAVA_HOME=JDK17 |
    | **vanilla** | (호스트) | ⛔ 검증대 부재 | 없음 |

    ## 2. 누적 도메인 카탈로그

    | 도메인 | preset 파일 | 추가 Growth |
    |---|---|---|
    | 고객관리 | a.seed.md | Growth-1 |
    | 주문관리 | b.seed.md | Growth-2A |
    | 재고관리 | c.seed.md | Growth-2B |

    ## 3. 누적 패턴

    | 종류 | 이름 | 추가 |
    |---|---|---|
    | x | D2 | init |

    ## 6. Growth 이력 (요약)

    | Growth | 일자 | 살붙임 요약 |
    |---|---|---|
    | Growth-72 | 2026-05-28 | **Status Board** — Exec dashboard. |
    | Growth-71 | 2026-05-28 | **Ops Pack** — emit_ops_pack.py. |
    | Growth-70 | 2026-05-28 | **target_project overlay** — extract_target_profile.py. |
    | Growth-69 | 2026-05-28 | **Web Form** — FastAPI scaffold UI. |
    | Growth-68 | 2026-05-27 | **mybatis url-prefix** — sibling forwarding. |
    | Growth-67 | 2026-05-27 | **Customer Slice B-3** — gap field wiring. |
    | **Growth-1 ~ Growth-25** | 2026-04 | archive (range row, not parsed as latest). |

    ## 7. 사용 규칙
    """
)

_SYNTH_DIAGNOSE = textwrap.dedent(
    """\
    # diagnose.py stub

    def check_cross_layer_coherence():
        pass  # 12 trap guards intact (G-47/48/50a/50b/58/61/62/63/69/70/71/72)
    """
)


@pytest.fixture
def synth_paths(tmp_path: Path) -> dict[str, Path]:
    learn_log = tmp_path / "learn-log.md"
    learn_log.write_text(_SYNTH_LEARN_LOG, encoding="utf-8")
    diagnose = tmp_path / "diagnose.py"
    diagnose.write_text(_SYNTH_DIAGNOSE, encoding="utf-8")
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()
    (profiles_dir / "_README.md").write_text("schema doc", encoding="utf-8")
    (profiles_dir / "acme.yaml").write_text("version: 1\n", encoding="utf-8")
    (profiles_dir / "foo-bank.yaml").write_text("version: 1\n", encoding="utf-8")
    return {
        "learn_log": learn_log,
        "diagnose": diagnose,
        "profiles_dir": profiles_dir,
    }


# ---------------------------------------------------------------------------
# Section extraction
# ---------------------------------------------------------------------------


def test_extract_section_returns_body_between_headings():
    section = sb._extract_section(_SYNTH_LEARN_LOG, 6)
    assert "Growth-72" in section
    assert "Growth-69" in section
    # Section 7 body should not be included.
    assert "사용 규칙" not in section


def test_extract_section_missing_returns_empty():
    assert sb._extract_section("no headings here", 6) == ""


def test_table_rows_skips_header_and_separator():
    body = "| a | b |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |\n"
    rows = sb._table_rows(body)
    assert rows == [["1", "2"], ["3", "4"]]


# ---------------------------------------------------------------------------
# Metric extractors — unit
# ---------------------------------------------------------------------------


def test_extract_growth_count_max_n():
    assert sb.extract_growth_count(_SYNTH_LEARN_LOG) == 72


def test_extract_growth_count_picks_max_even_from_range_rows():
    text = "## 6. Growth\n| Growth-1 ~ Growth-25 | a | b |\n| Growth-5 | a | b |\n"
    assert sb.extract_growth_count(text) == 25


def test_extract_growth_count_zero_when_missing():
    assert sb.extract_growth_count("nothing here") == 0


def test_extract_domain_count_synth():
    assert sb.extract_domain_count(_SYNTH_LEARN_LOG) == 3


def test_extract_verification_matrix_classifies_status_icons():
    rows = sb.extract_verification_matrix(_SYNTH_LEARN_LOG)
    assert [(r.lane, r.status) for r in rows] == [
        ("nexacro", "verified"),
        ("jakarta", "verified"),
        ("javax", "partial"),
        ("vanilla", "pending"),
    ]
    # Note text stripped of icon.
    nexacro = rows[0]
    assert "✅" not in nexacro.note
    assert "Growth-42" in nexacro.note


def test_extract_latest_growths_descending_and_limit():
    latest = sb.extract_latest_growths(_SYNTH_LEARN_LOG, limit=3)
    assert [g.number for g in latest] == [72, 71, 70]
    assert latest[0].date == "2026-05-28"
    assert "Status Board" in latest[0].summary_head


def test_extract_latest_growths_skips_range_rows():
    latest = sb.extract_latest_growths(_SYNTH_LEARN_LOG, limit=10)
    # Range row "Growth-1 ~ Growth-25" has no single ISO date column → no entry.
    assert all(g.number not in {1, 25} for g in latest)


def test_extract_trap_guards_count():
    assert sb.extract_trap_guards_count(_SYNTH_DIAGNOSE) == 12


def test_extract_trap_guards_count_zero_when_missing():
    assert sb.extract_trap_guards_count("no marker") == 0


def test_count_customer_profiles_excludes_readme(tmp_path):
    d = tmp_path / "profiles"
    d.mkdir()
    (d / "_README.md").write_text("doc", encoding="utf-8")
    (d / "acme.yaml").write_text("v: 1", encoding="utf-8")
    (d / "bar.yaml").write_text("v: 1", encoding="utf-8")
    assert sb.count_customer_profiles(d) == 2


def test_count_customer_profiles_missing_dir(tmp_path):
    assert sb.count_customer_profiles(tmp_path / "no-such") == 0


# ---------------------------------------------------------------------------
# compute() driver
# ---------------------------------------------------------------------------


def test_compute_aggregates_all_metrics(synth_paths):
    board = sb.compute(
        learn_log_path=synth_paths["learn_log"],
        diagnose_path=synth_paths["diagnose"],
        profiles_dir=synth_paths["profiles_dir"],
    )
    assert board.axes_count == 6
    assert board.domain_count == 3
    assert board.growth_count == 72
    assert board.trap_guards_count == 12
    assert board.customer_count == 2
    assert len(board.verification) == 4
    assert len(board.latest_growth) == 5  # default limit


def test_compute_graceful_when_files_missing(tmp_path):
    board = sb.compute(
        learn_log_path=tmp_path / "missing.md",
        diagnose_path=tmp_path / "missing.py",
        profiles_dir=tmp_path / "no-profiles",
    )
    assert board.axes_count == 6  # constant
    assert board.domain_count == 0
    assert board.growth_count == 0
    assert board.trap_guards_count == 0
    assert board.customer_count == 0


# ---------------------------------------------------------------------------
# HTML rendering
# ---------------------------------------------------------------------------


def test_render_status_section_has_all_panels(synth_paths):
    board = sb.compute(
        learn_log_path=synth_paths["learn_log"],
        diagnose_path=synth_paths["diagnose"],
        profiles_dir=synth_paths["profiles_dir"],
    )
    html = sb.render_status_section(board)
    assert 'class="status-board"' in html
    assert 'class="status-tile-grid"' in html
    assert "축 (axes)" in html
    assert "회귀 가드" in html
    assert ">12<" in html  # trap guards count from synth fixture
    assert ">72<" in html  # growth count
    assert "lane × runner 검증대" in html
    assert "최근 Growth 5건" in html
    # Verification statuses rendered with semantic class.
    assert "status-verify-verified" in html
    assert "status-verify-partial" in html


def test_render_status_section_escapes_html():
    board = sb.StatusBoard(
        axes_count=6,
        domain_count=1,
        growth_count=1,
        trap_guards_count=1,
        customer_count=0,
        verification=[sb.VerificationRow(lane="<script>", status="pending", note="<b>")],
        latest_growth=[
            sb.GrowthEntry(
                number=1, name="Growth-1", date="2026-01-01", summary_head="<x>"
            )
        ],
    )
    html = sb.render_status_section(board)
    assert "&lt;script&gt;" in html
    assert "<script>" not in html
    assert "&lt;b&gt;" in html
    assert "&lt;x&gt;" in html


# ---------------------------------------------------------------------------
# JSON dump
# ---------------------------------------------------------------------------


def test_to_dict_round_trips_through_json(synth_paths):
    board = sb.compute(
        learn_log_path=synth_paths["learn_log"],
        diagnose_path=synth_paths["diagnose"],
        profiles_dir=synth_paths["profiles_dir"],
    )
    payload = sb.to_dict(board)
    s = json.dumps(payload, ensure_ascii=False)
    decoded = json.loads(s)
    assert decoded["growth_count"] == 72
    assert decoded["customer_count"] == 2
    assert decoded["latest_growth"][0]["number"] == 72
    assert {row["lane"] for row in decoded["verification"]} == {
        "nexacro",
        "jakarta",
        "javax",
        "vanilla",
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_main_text_output(capsys, synth_paths):
    rc = sb.main(
        [
            "--learn-log",
            str(synth_paths["learn_log"]),
            "--diagnose",
            str(synth_paths["diagnose"]),
            "--profiles-dir",
            str(synth_paths["profiles_dir"]),
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "axes" in out
    assert "growth (max N)    72" in out
    assert "Growth-72" in out


def test_main_json_output(capsys, synth_paths):
    rc = sb.main(
        [
            "--json",
            "--learn-log",
            str(synth_paths["learn_log"]),
            "--diagnose",
            str(synth_paths["diagnose"]),
            "--profiles-dir",
            str(synth_paths["profiles_dir"]),
        ]
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["trap_guards_count"] == 12


# ---------------------------------------------------------------------------
# Drift smoke against real artifacts (cheap — no network, no scaffold)
# ---------------------------------------------------------------------------


def test_real_compute_returns_sane_numbers():
    """If the real workspace files exist, compute() returns growing values."""
    if not sb.DEFAULT_LEARN_LOG.is_file():
        pytest.skip("learn-log.md not present")
    board = sb.compute()
    assert board.axes_count == 6
    assert board.growth_count >= 71  # Growth-71 closed in this session
    assert board.trap_guards_count >= 11
    assert board.customer_count >= 1  # acme.yaml committed
    assert any(r.lane == "jakarta" for r in board.verification)
