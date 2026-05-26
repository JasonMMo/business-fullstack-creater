"""orient.py — Newcomer entry synthesizer (Growth-52, 2026-05-26).

신규 사용자가 클론 직후 "여기서 무엇부터 만지면 되는지" 한 화면에 파악하도록
세 소스를 합성한다:

- `docs/USER-GUIDE.md` 첫 blockquote (프로젝트 한 줄 정의)
- `learn-log.md` §0 Layer Ownership Card (5축 + 현재 트랩 카운트)
- `learn-log.md` §6 마지막 Growth (가장 최근 활동)

별도 문서 신설이 아니라 *이미 누적된 자산*을 노출한다 — list-domains 와 동일한
"자산 노출형 하네스" 패턴.

CLI:
    python scripts/workflow/orient.py
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


CREATER_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_USER_GUIDE = CREATER_ROOT / "docs" / "USER-GUIDE.md"
DEFAULT_LEARN_LOG = CREATER_ROOT / "learn-log.md"


@dataclass
class LayerRow:
    axis: str
    traps: str


@dataclass
class GrowthRow:
    name: str
    date: str
    summary: str


@dataclass
class Orientation:
    pitch: str
    layers: list[LayerRow] = field(default_factory=list)
    latest: GrowthRow | None = None


_LAYER_LINE_RE = re.compile(r"^\|\s*\*\*([^*]+)\*\*\s*\|")
_GROWTH_LINE_RE = re.compile(r"^\|\s*(?:\*\*)?(Growth-[^|*]*?)(?:\*\*)?\s*\|")


def extract_pitch(text: str) -> str:
    """First contiguous `> ` blockquote block at the top — project tagline."""
    lines: list[str] = []
    for raw in text.splitlines():
        if raw.startswith("> "):
            lines.append(raw[2:].strip())
        elif lines:
            break
        elif raw.strip() and not raw.startswith("#"):
            # encountered non-blockquote, non-heading content before any pitch
            break
    return " ".join(lines)


def extract_layer_card(text: str) -> list[LayerRow]:
    """Parse §0 Layer Ownership Card — return (axis, accumulated-traps) rows."""
    out: list[LayerRow] = []
    in_section = False
    for raw in text.splitlines():
        if raw.startswith("## 0. Layer Ownership Card"):
            in_section = True
            continue
        if in_section and raw.startswith("## "):
            break
        if not in_section:
            continue
        m = _LAYER_LINE_RE.match(raw)
        if not m:
            continue
        cells = [c.strip() for c in raw.split("|")[1:-1]]
        if len(cells) < 4:
            continue
        axis = m.group(1).strip()
        traps = cells[3]
        out.append(LayerRow(axis=axis, traps=traps))
    return out


def extract_latest_growth(text: str) -> GrowthRow | None:
    """Find §6 Growth 이력 table, return the row with the highest Growth-N number.

    Rows are not always chronologically ordered (Growth-43/42/45 interleave), so
    sort by numeric suffix when present.
    """
    in_section = False
    rows: list[tuple[int, GrowthRow]] = []
    for raw in text.splitlines():
        if raw.startswith("## 6. Growth"):
            in_section = True
            continue
        if in_section and raw.startswith("## "):
            break
        if not in_section:
            continue
        m = _GROWTH_LINE_RE.match(raw)
        if not m:
            continue
        cells = [c.strip() for c in raw.split("|")[1:-1]]
        if len(cells) < 3:
            continue
        gname = m.group(1).strip()
        date = cells[1]
        summary = cells[2]
        # extract last Growth number from "Growth-X" or "Growth-X ~ Growth-Y"
        nums = re.findall(r"Growth-(\d+)", gname)
        if not nums:
            continue
        n = int(nums[-1])
        rows.append((n, GrowthRow(name=gname, date=date, summary=summary)))
    if not rows:
        return None
    rows.sort(key=lambda x: x[0], reverse=True)
    return rows[0][1]


def build_orientation(
    user_guide: Path = DEFAULT_USER_GUIDE,
    learn_log: Path = DEFAULT_LEARN_LOG,
) -> Orientation:
    pitch = ""
    if user_guide.exists():
        pitch = extract_pitch(user_guide.read_text(encoding="utf-8"))
    layers: list[LayerRow] = []
    latest: GrowthRow | None = None
    if learn_log.exists():
        log_text = learn_log.read_text(encoding="utf-8")
        layers = extract_layer_card(log_text)
        latest = extract_latest_growth(log_text)
    return Orientation(pitch=pitch, layers=layers, latest=latest)


def format_orientation(o: Orientation, *, summary_chars: int = 240) -> str:
    out: list[str] = []
    out.append("business-fullstack-creater — orientation")
    out.append("=" * 48)
    if o.pitch:
        out.append("")
        out.append(f"  {o.pitch}")
    if o.layers:
        out.append("")
        out.append("5축 (현재 누적 트랩):")
        axis_w = max(len(r.axis) for r in o.layers)
        for r in o.layers:
            # Trim trap column — it can be a long parenthesized list; show prefix only.
            t = r.traps
            if len(t) > 80:
                t = t[:77] + "..."
            out.append(f"  - {r.axis:<{axis_w}}  {t}")
    if o.latest:
        out.append("")
        out.append(f"최근 Growth: {o.latest.name} ({o.latest.date})")
        s = o.latest.summary
        if len(s) > summary_chars:
            s = s[:summary_chars - 3] + "..."
        out.append(f"  {s}")
    out.append("")
    out.append("다음 명령:")
    out.append("  /diagnose       — 환경 pre-flight (JDK/runner/카탈로그 점검)")
    out.append("  /list-domains   — 14 preset 도메인 둘러보기")
    out.append("  /scaffold <도메인>  — 신규 프로젝트 생성")
    out.append("  /full-test <lane>   — 4계층 풀테스트 (실패 시 R3 recovery hint)")
    return "\n".join(out)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="orient.py",
        description="Synthesize a newcomer orientation from USER-GUIDE + learn-log",
    )
    p.add_argument(
        "--user-guide", type=Path, default=DEFAULT_USER_GUIDE, help="USER-GUIDE.md path"
    )
    p.add_argument(
        "--learn-log", type=Path, default=DEFAULT_LEARN_LOG, help="learn-log.md path"
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    o = build_orientation(args.user_guide, args.learn_log)
    print(format_orientation(o))
    return 0


if __name__ == "__main__":
    sys.exit(main())
