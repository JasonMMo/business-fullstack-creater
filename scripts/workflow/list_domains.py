"""list_domains.py — R4 (서비스 리뷰 2026-05-26): /list-domains 슬래시 커맨드 백엔드.

andrej-karpathy-rdb-skill/.claude/skills/karpathy-rdb/presets/INDEX.md 의 14개 도메인을
한 줄 요약 + aliases 로 출력한다. preset 카탈로그 노출 = 외부 사용자의 첫 도메인 선택
경로 단축.

CLI:
    python scripts/workflow/list_domains.py            # 한줄 표 (기본)
    python scripts/workflow/list_domains.py --verbose  # aliases + entities 포함
    python scripts/workflow/list_domains.py --json     # 구조화 출력
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path


DEFAULT_INDEX_PATH = Path(
    r"D:\AI\workspace\andrej-karpathy-rdb-skill\.claude\skills\karpathy-rdb\presets\INDEX.md"
)


@dataclass
class Domain:
    name: str
    aliases: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    summary: str = ""


_FIELD_RE = re.compile(r"^-\s+(aliases|keywords|entities|한 줄):\s*(.+)$")


def parse_index_md(text: str) -> list[Domain]:
    """Extract domain entries from INDEX.md content.

    Stops at the trailing `## 매칭 알고리즘` section — that is meta, not a domain.
    """
    domains: list[Domain] = []
    current: Domain | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("## "):
            heading = line[3:].strip()
            if heading.startswith("매칭"):
                current = None
                break
            current = Domain(name=heading)
            domains.append(current)
            continue
        if current is None:
            continue
        m = _FIELD_RE.match(line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        items = [x.strip() for x in val.split(",")] if key != "한 줄" else None
        if key == "aliases":
            current.aliases = items or []
        elif key == "keywords":
            current.keywords = items or []
        elif key == "entities":
            current.entities = items or []
        elif key == "한 줄":
            current.summary = val
    return domains


def format_table(domains: list[Domain], *, verbose: bool = False) -> str:
    """Pretty 1-line per domain (or 3 lines per domain in verbose)."""
    if not domains:
        return "(no domains found)"
    name_w = max(len(d.name) for d in domains)
    out: list[str] = []
    out.append(f"{len(domains)} preset domains:")
    for d in domains:
        out.append(f"  {d.name:<{name_w}}  {d.summary}")
        if verbose:
            if d.aliases:
                out.append(f"  {'':<{name_w}}    aliases:  {', '.join(d.aliases)}")
            if d.entities:
                out.append(f"  {'':<{name_w}}    entities: {', '.join(d.entities)}")
    return "\n".join(out)


def load_domains(index_path: Path = DEFAULT_INDEX_PATH) -> list[Domain]:
    if not index_path.exists():
        raise FileNotFoundError(f"INDEX.md not found: {index_path}")
    return parse_index_md(index_path.read_text(encoding="utf-8"))


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="list_domains.py", description="List preset domains from rdb-skill INDEX.md")
    p.add_argument("--index", type=Path, default=DEFAULT_INDEX_PATH, help="Path to INDEX.md (override for tests)")
    p.add_argument("--verbose", action="store_true", help="Include aliases + entities")
    p.add_argument("--json", action="store_true", help="JSON output instead of table")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        domains = load_domains(args.index)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    if args.json:
        sys.stdout.write(json.dumps([asdict(d) for d in domains], ensure_ascii=False, indent=2))
        sys.stdout.write("\n")
    else:
        print(format_table(domains, verbose=args.verbose))
    return 0


if __name__ == "__main__":
    sys.exit(main())
