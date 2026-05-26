"""Scan recent git changes across 5 repos and classify backflow candidates."""
from __future__ import annotations
import re
import subprocess
import sys
from pathlib import Path
from datetime import date, timedelta

# Support both `python -m scripts.workflow.contribute_back` (package import)
# and `python scripts/workflow/contribute_back.py` (direct script invocation).
try:
    from . import learn_log
except ImportError:
    _root = str(Path(__file__).resolve().parents[2])
    if _root not in sys.path:
        sys.path.insert(0, _root)
    from scripts.workflow import learn_log

REPOS = [
    Path(r"D:\AI\workspace\andrej-karpathy-rdb-skill"),
    Path(r"D:\AI\workspace\andrej-karpathy-rdb-ddl"),
    Path(r"D:\AI\workspace\andrej-karpathy-rdb-mybatis"),
    Path(r"D:\AI\workspace\andrej-karpathy-rdb-nexacro"),
    Path(r"D:\AI\workspace\business-fullstack-creater"),
]

CATEGORY_GUIDE = {
    "catalog":  ("§2 catalog/preset",  "preset/catalog 환류 (rdb-skill/ddl)"),
    "template": ("§3 templates",       "lane 템플릿 (rdb-mybatis)"),
    "pattern":  ("§3 patterns",        "frontend pattern (rdb-nexacro)"),
    "dialect":  ("§4 dialect traps",   "dialect 어댑터 (rdb-ddl)"),
    "other":    ("§5 / §6 freeform",   "검토 후 §5 gap 또는 §6 환류 결정"),
}


def classify(paths: list[str]) -> dict[str, list[str]]:
    """Classify file paths into backflow categories."""
    out: dict[str, list[str]] = {k: [] for k in CATEGORY_GUIDE}
    for p in paths:
        if "preset" in p and (p.endswith(".seed.md") or "catalog" in p):
            out["catalog"].append(p)
        elif p.endswith(".yaml") and "catalog" in p:
            out["catalog"].append(p)
        elif "templates/" in p and p.endswith(".j2"):
            out["template"].append(p)
        elif "patterns/" in p and p.endswith("manifest.yaml"):
            out["pattern"].append(p)
        elif "dialect" in p and p.endswith(".py"):
            out["dialect"].append(p)
        else:
            out["other"].append(p)
    return out


def questions_for(grouped: dict[str, list[str]]) -> list[dict]:
    """Return one question dict per non-empty, non-other category."""
    return [
        {
            "category": cat,
            "where": CATEGORY_GUIDE[cat][0],
            "hint": CATEGORY_GUIDE[cat][1],
            "files": files,
        }
        for cat, files in grouped.items()
        if files and cat != "other"
    ]


def collect_changes(since: str) -> dict[str, list[str]]:
    """Map repo name → changed path list since given ISO date."""
    out: dict[str, list[str]] = {}
    for repo in REPOS:
        if not (repo / ".git").exists():
            continue
        p = subprocess.run(
            ["git", "-C", str(repo), "log", f"--since={since}",
             "--name-only", "--pretty=format:"],
            capture_output=True, text=True,
        )
        paths = sorted({line.strip() for line in p.stdout.splitlines() if line.strip()})
        if paths:
            out[repo.name] = paths
    return out


def _growth_start_date() -> str:
    """Return the start date of the last in-progress Growth row, or today-7."""
    try:
        text = learn_log.LEARN_LOG.read_text(encoding="utf-8")
        m = re.findall(r"\|\s*Growth-\d+\s*\|\s*(\d{4}-\d{2}-\d{2})", text)
        if m:
            return m[-1]
    except Exception:
        pass
    return (date.today() - timedelta(days=7)).isoformat()


def run() -> int:
    since = _growth_start_date()
    print(f"[contribute-back] scanning changes since {since}")
    repos_changes = collect_changes(since)
    if not repos_changes:
        print("환류 대상 없음.")
        return 0

    flat: list[str] = []
    for repo, paths in repos_changes.items():
        print(f"\n=== {repo} ===")
        for p in paths:
            print(f"  {p}")
            flat.append(p)

    grouped = classify(flat)
    qs = questions_for(grouped)
    if not qs:
        print("\n분류된 환류 후보 없음.")
        return 0

    print("\n=== 환류 후보 (카테고리별) ===")
    missing = []
    for q in qs:
        print(f"\n[{q['category']}] → {q['where']}: {q['hint']}")
        for f in q["files"]:
            print(f"  - {f}")
        try:
            answer = input("  환류 완료했나요? (y/N) ").strip().lower()
        except EOFError:
            answer = "n"
        if answer != "y":
            missing.append(q["category"])

    if missing:
        print(f"\n미환류 카테고리: {', '.join(missing)}", file=sys.stderr)
        try:
            n = learn_log.latest_growth_num()
            existing = learn_log.LEARN_LOG.read_text(encoding="utf-8")
            if re.search(rf"Growth-{n}[^|]*\(in_progress\)", existing):
                learn_log.update_label(n, "환류 미완")
        except Exception:
            pass
        print("\n[warn] 환류 미완 후보 있음 — Growth 종료 전 §2~§5 확인.", file=sys.stderr)

    # --- web_index rebuild (Phase A5 hook) ---
    _run_web_hook()

    return 0


def _run_web_hook() -> None:
    """Trigger a non-blocking web_index rebuild after the contribute-back checklist.

    Any exception from web_index.build() is caught and printed as a warning so
    that contribute_back.run() always returns 0 on its own success.
    """
    try:
        from scripts.workflow import web_index as _wi
        result = _wi.build(json_output=False)
        if result.domains_failed:
            print(f"[contribute-back] web_index partial failure: {result.domains_failed}",
                  file=sys.stderr)
        else:
            print(f"[contribute-back] web_index rebuilt OK "
                  f"({len(result.domains_ok)} domains)")
    except Exception as exc:  # never block the checklist on web errors
        print(f"[contribute-back] web_index skip (error: {exc})", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(run())
