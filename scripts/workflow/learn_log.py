"""Parse and update learn-log.md §6 Growth ledger."""
from __future__ import annotations
import re
from pathlib import Path
from datetime import date

LEARN_LOG = Path(__file__).resolve().parents[2] / "learn-log.md"
SECTION_HEADER = "## 6. Growth 이력 (요약)"
GROWTH_ROW = re.compile(r"^\|\s*Growth-(?P<num>\d+)(?P<suffix>[a-zA-Z~\-]*)\s*\|")

def _section_bounds(lines: list[str]) -> tuple[int, int]:
    try:
        start = next(i for i, l in enumerate(lines) if l.strip() == SECTION_HEADER)
    except StopIteration:
        raise ValueError(f"section header not found: §6 ({SECTION_HEADER})")
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return start, end

def latest_growth_num() -> int:
    text = LEARN_LOG.read_text(encoding="utf-8")
    lines = text.splitlines()
    start, end = _section_bounds(lines)
    nums = [int(m["num"]) for line in lines[start:end] if (m := GROWTH_ROW.match(line))]
    if not nums:
        raise ValueError("no Growth rows found in §6")
    return max(nums)

def append_row(name: str, today: str | None = None) -> int:
    today = today or date.today().isoformat()
    text = LEARN_LOG.read_text(encoding="utf-8")
    lines = text.splitlines()
    start, end = _section_bounds(lines)
    next_num = latest_growth_num() + 1
    row = f"| Growth-{next_num} | {today} | {name} (in_progress) |"
    insert_at = end
    for i in range(end - 1, start, -1):
        if GROWTH_ROW.match(lines[i]):
            insert_at = i + 1
            break
    lines.insert(insert_at, row)
    LEARN_LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return next_num

def update_label(growth_num: int, label: str) -> None:
    text = LEARN_LOG.read_text(encoding="utf-8")
    lines = text.splitlines()
    pattern = re.compile(rf"^\|\s*Growth-{growth_num}(?:[a-zA-Z~\-]*)\s*\|")
    for i, line in enumerate(lines):
        if pattern.match(line) and "(in_progress)" in line:
            lines[i] = line.replace("(in_progress)", f"({label})")
            break
    LEARN_LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")
