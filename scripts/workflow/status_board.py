"""status_board.py — Exec Status Board (Growth-72, 2026-05-28).

M2 (G1 roadmap) — Growth-55 portal 확장 (`docs/index.html`) 의 누적 자산
시각화 레이어. 외부 사용자(특히 CEO 페르소나)가 "이 프로젝트가 사용할수록
얼마나 쌓였는지" 한 화면에 파악하도록 *이미 누적된 자산*을 합성한다.

별도 메트릭 시스템 도입이 아니라 `/orient` 와 동일한 자산-노출 패턴:

- 6축 (skill / ddl / mybatis / nexacro / creater / customer) — `learn-log.md` §0
- Growth 누적 (최대 N + 최근 5개 활동) — `learn-log.md` §6
- 회귀 가드 (G-47/48/.../71) — `scripts/workflow/diagnose.py` PASS detail
- 검증 lane (nexacro / jakarta / javax / vanilla 4행) — `learn-log.md` §1
- 도메인 카탈로그 (14건) — `learn-log.md` §2
- 고객 (customer profile yaml 수) — `profiles/*.yaml`

이 모듈은 read-only 노출 — 새 데이터 소스 신설 없음.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path

CREATER_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LEARN_LOG = CREATER_ROOT / "learn-log.md"
DEFAULT_DIAGNOSE = CREATER_ROOT / "scripts" / "workflow" / "diagnose.py"
DEFAULT_PROFILES_DIR = CREATER_ROOT / "profiles"

# Layer axes documented in CLAUDE.md/AGENTS.md (Growth-63 6th axis customer)
_AXES = ("skill", "ddl", "mybatis", "nexacro", "creater", "customer")


@dataclass
class VerificationRow:
    lane: str
    status: str  # "verified" | "partial" | "pending"
    note: str


@dataclass
class GrowthEntry:
    number: int
    name: str  # "Growth-71"
    date: str
    summary_head: str  # first sentence-ish (truncated)


@dataclass
class StatusBoard:
    axes_count: int
    domain_count: int
    growth_count: int  # max Growth-N
    trap_guards_count: int
    customer_count: int
    verification: list[VerificationRow] = field(default_factory=list)
    latest_growth: list[GrowthEntry] = field(default_factory=list)


# ---------------------------------------------------------------------------
# learn-log section extraction
# ---------------------------------------------------------------------------

_SECTION_RE = re.compile(r"^## (\d+)\.\s+(.+)$", re.MULTILINE)


def _extract_section(text: str, number: int) -> str:
    """Return the body of `## <number>. <title>` up to the next `## ` heading."""
    pattern = re.compile(rf"^##\s+{number}\.\s.*?$", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return ""
    start = match.end()
    next_match = re.search(r"^##\s+\d+\.\s", text[start:], re.MULTILINE)
    if next_match:
        return text[start : start + next_match.start()]
    return text[start:]


def _table_rows(section_text: str) -> list[list[str]]:
    """Extract `|...|` rows skipping header/separator. Each row → trimmed cells."""
    rows: list[list[str]] = []
    seen_separator = False
    for line in section_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        if re.match(r"^\|\s*-+\s*\|", stripped):
            seen_separator = True
            continue
        if not seen_separator:
            # header row — skip
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        rows.append(cells)
    return rows


# ---------------------------------------------------------------------------
# Metric extractors
# ---------------------------------------------------------------------------

_GROWTH_NUM_RE = re.compile(r"Growth-(\d+)")


def extract_growth_count(learn_log_text: str) -> int:
    """Max `Growth-N` found in §6 (counts both single and range rows)."""
    section = _extract_section(learn_log_text, 6)
    nums = [int(m) for m in _GROWTH_NUM_RE.findall(section)]
    return max(nums) if nums else 0


def extract_domain_count(learn_log_text: str) -> int:
    """Count §2 catalog rows (presets/INDEX.md 대용)."""
    section = _extract_section(learn_log_text, 2)
    return len(_table_rows(section))


_VERIFICATION_STATUS_RE = re.compile(r"(✅|⚠️|❌)")


def extract_verification_matrix(learn_log_text: str) -> list[VerificationRow]:
    """Parse §1 lane × runner table."""
    section = _extract_section(learn_log_text, 1)
    rows = _table_rows(section)
    out: list[VerificationRow] = []
    for cells in rows:
        if len(cells) < 3:
            continue
        lane_raw = cells[0]
        status_raw = cells[2]
        # strip markdown bold/asterisks
        lane = re.sub(r"\*+", "", lane_raw).strip()
        status_icon_match = _VERIFICATION_STATUS_RE.search(status_raw)
        if status_icon_match and status_icon_match.group(1) == "✅":
            status = "verified"
        elif status_icon_match and status_icon_match.group(1) == "⚠️":
            status = "partial"
        else:
            status = "pending"
        # short note: first 80 chars after icon stripped
        note = _VERIFICATION_STATUS_RE.sub("", status_raw).strip()
        if len(note) > 80:
            note = note[:77] + "…"
        out.append(VerificationRow(lane=lane, status=status, note=note))
    return out


_LATEST_GROWTH_ROW_RE = re.compile(
    r"^\|\s*\*?\*?Growth-(\d+)\*?\*?\s*\|\s*([0-9]{4}-[0-9]{2}-[0-9]{2})\s*\|\s*(.+?)\s*\|\s*$"
)


def extract_latest_growths(learn_log_text: str, *, limit: int = 5) -> list[GrowthEntry]:
    """Return top-N Growth entries by descending Growth-N."""
    section = _extract_section(learn_log_text, 6)
    seen: dict[int, GrowthEntry] = {}
    for line in section.splitlines():
        m = _LATEST_GROWTH_ROW_RE.match(line.strip())
        if not m:
            continue
        num = int(m.group(1))
        if num in seen:
            continue
        date = m.group(2)
        summary = m.group(3)
        # Strip leading bold marker + take first segment up to em-dash or period.
        summary_clean = re.sub(r"\*+", "", summary).strip()
        head = re.split(r"\s+—\s+|\.\s|\(", summary_clean, maxsplit=1)[0]
        if len(head) > 90:
            head = head[:87] + "…"
        seen[num] = GrowthEntry(
            number=num,
            name=f"Growth-{num}",
            date=date,
            summary_head=head,
        )
    ordered = sorted(seen.values(), key=lambda g: g.number, reverse=True)
    return ordered[:limit]


_TRAP_GUARDS_RE = re.compile(r"(\d+)\s+trap guards intact")


def extract_trap_guards_count(diagnose_text: str) -> int:
    m = _TRAP_GUARDS_RE.search(diagnose_text)
    return int(m.group(1)) if m else 0


def count_customer_profiles(profiles_dir: Path) -> int:
    """Count `*.yaml` (excluding `_README.md` and underscores)."""
    if not profiles_dir.is_dir():
        return 0
    return sum(
        1
        for p in profiles_dir.glob("*.yaml")
        if not p.name.startswith("_")
    )


# ---------------------------------------------------------------------------
# Compute driver
# ---------------------------------------------------------------------------


def compute(
    *,
    learn_log_path: Path | None = None,
    diagnose_path: Path | None = None,
    profiles_dir: Path | None = None,
) -> StatusBoard:
    """Aggregate all metrics. None args fall back to module-level defaults."""
    if learn_log_path is None:
        learn_log_path = DEFAULT_LEARN_LOG
    if diagnose_path is None:
        diagnose_path = DEFAULT_DIAGNOSE
    if profiles_dir is None:
        profiles_dir = DEFAULT_PROFILES_DIR

    learn_log_text = (
        learn_log_path.read_text(encoding="utf-8") if learn_log_path.is_file() else ""
    )
    diagnose_text = (
        diagnose_path.read_text(encoding="utf-8") if diagnose_path.is_file() else ""
    )

    return StatusBoard(
        axes_count=len(_AXES),
        domain_count=extract_domain_count(learn_log_text),
        growth_count=extract_growth_count(learn_log_text),
        trap_guards_count=extract_trap_guards_count(diagnose_text),
        customer_count=count_customer_profiles(profiles_dir),
        verification=extract_verification_matrix(learn_log_text),
        latest_growth=extract_latest_growths(learn_log_text, limit=5),
    )


# ---------------------------------------------------------------------------
# HTML rendering
# ---------------------------------------------------------------------------


def _esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_status_section(board: StatusBoard) -> str:
    """HTML fragment injected into `docs/index.html` (Growth-72).

    Returns a `<section class="status-board">` block with 4 metric tiles +
    verification matrix + latest activity list. No external assets — uses
    classes added to `docs/assets/style.css` in S2.3.
    """
    metric_tiles = [
        ("축 (axes)", str(board.axes_count), "skill·ddl·mybatis·nexacro·creater·customer"),
        ("도메인", str(board.domain_count), "preset-catalog.yaml"),
        ("Growth 누적", str(board.growth_count), "learn-log §6"),
        ("회귀 가드", str(board.trap_guards_count), "diagnose.py cross-layer"),
        ("고객 profile", str(board.customer_count), "profiles/*.yaml"),
    ]
    tile_html = "\n        ".join(
        f'<div class="status-tile">\n'
        f'  <div class="status-tile-value">{_esc(value)}</div>\n'
        f'  <div class="status-tile-label">{_esc(label)}</div>\n'
        f'  <div class="status-tile-source">{_esc(source)}</div>\n'
        f"</div>"
        for label, value, source in metric_tiles
    )

    verification_rows = "\n          ".join(
        f'<tr class="status-verify-{_esc(row.status)}">\n'
        f"  <td>{_esc(row.lane)}</td>\n"
        f'  <td class="status-verify-icon">{_status_icon(row.status)}</td>\n'
        f"  <td>{_esc(row.note)}</td>\n"
        f"</tr>"
        for row in board.verification
    )

    latest_rows = "\n          ".join(
        f"<li>\n"
        f'  <span class="status-growth-name">{_esc(g.name)}</span>\n'
        f'  <span class="status-growth-date">{_esc(g.date)}</span>\n'
        f'  <span class="status-growth-summary">{_esc(g.summary_head)}</span>\n'
        f"</li>"
        for g in board.latest_growth
    )

    return (
        '    <section aria-label="Status board" class="status-board">\n'
        "      <h2>누적 자산 현황</h2>\n"
        '      <div class="status-tile-grid">\n'
        f"        {tile_html}\n"
        "      </div>\n"
        '      <div class="status-detail">\n'
        '        <div class="status-verify-pane">\n'
        "          <h3>lane × runner 검증대</h3>\n"
        '          <table class="status-verify-table">\n'
        "            <thead><tr><th>lane</th><th></th><th>최근 검증</th></tr></thead>\n"
        "            <tbody>\n"
        f"          {verification_rows}\n"
        "            </tbody>\n"
        "          </table>\n"
        "        </div>\n"
        '        <div class="status-latest-pane">\n'
        "          <h3>최근 Growth 5건</h3>\n"
        '          <ol class="status-latest-list">\n'
        f"          {latest_rows}\n"
        "          </ol>\n"
        "        </div>\n"
        "      </div>\n"
        "    </section>"
    )


def _status_icon(status: str) -> str:
    return {
        "verified": "✅",
        "partial": "⚠️",
        "pending": "—",
    }.get(status, "—")


# CSS to be appended once to docs/assets/style.css (callers responsibility).
STATUS_BOARD_CSS = """\
/* Growth-72 status board */
.status-board { margin: 1.5rem 0 2rem; }
.status-tile-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: .75rem; margin: 1rem 0; }
.status-tile { background: #f5f7fa; border: 1px solid #d8dde6; border-radius: 6px; padding: .85rem 1rem; }
.status-tile-value { font-size: 1.9rem; font-weight: 700; color: #1a3c6e; line-height: 1.1; }
.status-tile-label { font-size: .9rem; color: #364152; margin-top: .15rem; }
.status-tile-source { font-size: .75rem; color: #8893a5; margin-top: .25rem; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
.status-detail { display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; margin-top: 1rem; }
.status-verify-table { width: 100%; border-collapse: collapse; font-size: .85rem; }
.status-verify-table th, .status-verify-table td { padding: .35rem .5rem; border-bottom: 1px solid #e1e5ec; text-align: left; }
.status-verify-icon { width: 1.5rem; text-align: center; }
.status-verify-verified td:first-child { color: #1a7332; font-weight: 600; }
.status-verify-partial td:first-child { color: #8a5a00; font-weight: 600; }
.status-latest-list { padding-left: 1.25rem; margin: 0; font-size: .85rem; }
.status-latest-list li { margin-bottom: .35rem; }
.status-growth-name { font-weight: 600; color: #1a3c6e; margin-right: .4rem; }
.status-growth-date { color: #8893a5; font-size: .8rem; margin-right: .4rem; font-family: ui-monospace, monospace; }
@media (max-width: 720px) { .status-detail { grid-template-columns: 1fr; } }
"""


# ---------------------------------------------------------------------------
# JSON dump (for `/status` CLI consumption later)
# ---------------------------------------------------------------------------


def to_dict(board: StatusBoard) -> dict:
    return {
        "axes_count": board.axes_count,
        "domain_count": board.domain_count,
        "growth_count": board.growth_count,
        "trap_guards_count": board.trap_guards_count,
        "customer_count": board.customer_count,
        "verification": [
            {"lane": r.lane, "status": r.status, "note": r.note}
            for r in board.verification
        ],
        "latest_growth": [
            {
                "number": g.number,
                "name": g.name,
                "date": g.date,
                "summary": g.summary_head,
            }
            for g in board.latest_growth
        ],
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Exec Status Board — accumulated asset snapshot (Growth-72)."
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON to stdout.")
    parser.add_argument(
        "--learn-log", type=Path, default=None, help="Override learn-log.md path."
    )
    parser.add_argument(
        "--diagnose", type=Path, default=None, help="Override diagnose.py path."
    )
    parser.add_argument(
        "--profiles-dir", type=Path, default=None, help="Override profiles/ dir."
    )
    args = parser.parse_args(argv)

    board = compute(
        learn_log_path=args.learn_log,
        diagnose_path=args.diagnose,
        profiles_dir=args.profiles_dir,
    )

    if args.json:
        print(json.dumps(to_dict(board), ensure_ascii=False, indent=2))
        return 0

    print(f"axes              {board.axes_count}")
    print(f"domains           {board.domain_count}")
    print(f"growth (max N)    {board.growth_count}")
    print(f"trap guards       {board.trap_guards_count}")
    print(f"customer profiles {board.customer_count}")
    print()
    print("verification:")
    for row in board.verification:
        print(f"  {row.lane:10s} {_status_icon(row.status)}  {row.note}")
    print()
    print("latest growth:")
    for g in board.latest_growth:
        print(f"  {g.name:10s} {g.date}  {g.summary_head}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
