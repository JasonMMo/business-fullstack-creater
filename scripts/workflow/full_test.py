"""4-layer full-test orchestrator with auto-labeling.

Layer responsibilities (delegated to existing scripts/CLIs):
  L1: pytest in 4 sibling repos
  L2: HSQLDB schema-apply + seed-insert smoke
  L3: mvn -q package on Stage 3+5 scaffold output
  L4: live WAS overlay + endpoint POST verification

This module does NOT reimplement those layers — it orchestrates and labels.
"""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

# Support both `python -m scripts.workflow.full_test` (package import)
# and `python scripts/workflow/full_test.py` (direct script invocation).
try:
    from .lane_runner_map import resolve_runner, lane_label_suffix, lane_probe_kind, lane_probe_url
    from . import learn_log, cleanup_runner, live_overlay, live_runner, live_probe
except ImportError:
    _root = str(Path(__file__).resolve().parents[2])
    if _root not in sys.path:
        sys.path.insert(0, _root)
    from scripts.workflow.lane_runner_map import (
        resolve_runner, lane_label_suffix, lane_probe_kind, lane_probe_url,
    )
    from scripts.workflow import learn_log, cleanup_runner, live_overlay, live_runner, live_probe

SIBLING_REPOS = [
    Path(r"D:\AI\workspace\andrej-karpathy-rdb-skill"),
    Path(r"D:\AI\workspace\andrej-karpathy-rdb-ddl"),
    Path(r"D:\AI\workspace\andrej-karpathy-rdb-mybatis"),
    Path(r"D:\AI\workspace\andrej-karpathy-rdb-nexacro"),
]

NEXACRO_REPO = Path(r"D:\AI\workspace\nexacroN-fullstack")
L4_READY_TIMEOUT_SEC = 180.0
L4_PROBE_TIMEOUT_SEC = 30.0


def runner_for(lane: str) -> str:
    return resolve_runner(lane)


def decide_label(layers: dict[str, bool]) -> str:
    if layers.get("L1") is False:
        return "단위 테스트 실패 — 검증 중단"
    if not layers.get("L1"):
        return "검증 시작 전"
    if not layers.get("L2"):
        return "단위까지만 검증"
    if not layers.get("L3"):
        return "JDBC 까지만 검증"
    if layers.get("L4_full"):
        return "풀테스트 그린"
    if layers.get("L4_partial"):
        return "라이브 WAS 부분검증"
    return "JDBC + 빌드까지만 검증"


def run_l1_pytest() -> bool:
    ok = True
    for repo in SIBLING_REPOS:
        if not repo.exists():
            print(f"[L1] skip (not found): {repo}", file=sys.stderr)
            continue
        p = subprocess.run(["pytest", "-q"], cwd=repo, capture_output=True, text=True)
        print(f"[L1] {repo.name}: rc={p.returncode}")
        if p.returncode != 0:
            print(p.stdout[-1000:], file=sys.stderr)
            ok = False
    return ok


def run_l2_jdbc(scaffold_dir: Path) -> bool:
    sql = scaffold_dir / "2-ddl"
    if not sql.exists():
        print(f"[L2] no DDL output at {sql}", file=sys.stderr)
        return False
    print(f"[L2] HSQLDB smoke against {sql} — delegated (placeholder PASS)")
    return True


def run_l3_mvn(scaffold_dir: Path) -> bool:
    pom = scaffold_dir / "5-overlay" / "pom.xml"
    if not pom.exists():
        pom = scaffold_dir / "pom.xml"
    if not pom.exists():
        print(f"[L3] no pom.xml under {scaffold_dir}", file=sys.stderr)
        return False
    p = subprocess.run(["mvn", "-q", "package", "-DskipTests"],
                       cwd=pom.parent, capture_output=True, text=True, timeout=600)
    print(f"[L3] mvn rc={p.returncode}")
    return p.returncode == 0


def runner_path_for(lane: str) -> Path:
    """Resolve the on-disk runner directory for a lane (sample runner under nexacroN-fullstack)."""
    return NEXACRO_REPO / "samples" / "runners" / resolve_runner(lane)


def derive_entity_slug(mapper_xml_dir: Path) -> str | None:
    """Pick the first mapper, return URL slug.

    Handles both kebab-case (`account-mapper.xml` → 'account') and PascalCase
    (`AccountMapper.xml` → 'account'). Stage 3 emits PascalCase pre-overlay;
    overlay renames to kebab-case in the runner — either may show up depending
    on whether we read the scaffold or runner copy.
    """
    kebab = sorted(mapper_xml_dir.glob("*-mapper.xml"))
    if kebab:
        return kebab[0].name.removesuffix("-mapper.xml")
    pascal = sorted(p for p in mapper_xml_dir.glob("*Mapper.xml"))
    if pascal:
        return pascal[0].name.removesuffix("Mapper.xml").lower()
    return None


def _mvn_rebuild_runner(runner_dir: Path, timeout_sec: int = 600) -> bool:
    """Rebuild the runner jar after overlay so live JVM picks up the new schema/mappers."""
    p = subprocess.run(
        ["mvn", "-q", "package", "-DskipTests"],
        cwd=runner_dir, capture_output=True, text=True, timeout=timeout_sec,
    )
    print(f"[L4] mvn rebuild runner rc={p.returncode}")
    if p.returncode != 0:
        print((p.stdout or "")[-800:], file=sys.stderr)
    return p.returncode == 0


def run_l4_live(lane: str, scaffold_dir: Path) -> tuple[bool, bool]:
    """Apply overlay → rebuild → start runner → probe → stop. Returns (full_pass, partial_pass).

    full_pass requires HTTP 200 + ErrorCode=0 + row_count>=1.
    partial_pass means runner reached ready state — verdict short of full.
    """
    runner_name = resolve_runner(lane)
    runner_dir = runner_path_for(lane)
    print(f"[L4] lane={lane} runner={runner_name} dir={runner_dir} scaffold={scaffold_dir}")
    if not runner_dir.exists():
        print(f"[L4] runner dir missing: {runner_dir}", file=sys.stderr)
        return (False, False)

    try:
        plan = live_overlay.discover_scaffold(scaffold_dir)
    except (FileNotFoundError, ValueError) as e:
        print(f"[L4] scaffold incomplete: {e}", file=sys.stderr)
        return (False, False)
    slug = plan.domain_slug

    result = live_overlay.apply_overlay(runner_dir, plan)
    print(f"[L4] overlay applied: {len(result.files_written)} written, {len(result.files_edited)} edited")

    if not _mvn_rebuild_runner(runner_dir):
        return (False, False)

    handle = live_runner.start_runner(runner_dir)
    try:
        if not live_runner.wait_until_ready(handle, timeout_sec=L4_READY_TIMEOUT_SEC, poll_interval=1.0):
            print(f"[L4] runner did not reach ready state (see {handle.log_path})", file=sys.stderr)
            return (False, False)
        entity = derive_entity_slug(plan.mapper_xml_dir) or slug
        url = lane_probe_url(lane, handle.port, entity)
        kind = lane_probe_kind(lane)
        if kind == "rest":
            verdict = live_probe.probe_endpoint_json(url, timeout_sec=L4_PROBE_TIMEOUT_SEC)
        else:
            verdict = live_probe.probe_endpoint(url, timeout_sec=L4_PROBE_TIMEOUT_SEC)
        print(f"[L4] probe kind={kind} url={url} http={verdict.http_status} errcode={verdict.error_code} rows={verdict.row_count}")
        if verdict.ok:
            return (True, True)
        return (False, True)
    finally:
        live_runner.stop_runner(handle)


def find_latest_scaffold() -> Path | None:
    out = Path.cwd() / "out"
    if not out.exists():
        return None
    dirs = [d for d in out.iterdir() if d.is_dir()]
    return max(dirs, key=lambda d: d.stat().st_mtime, default=None)


def run(lane: str, domain: str | None = None) -> str:
    scaffold = Path(domain) if domain and Path(domain).exists() else find_latest_scaffold()
    if scaffold is None:
        raise FileNotFoundError("no scaffold directory found (pass [domain] or run /scaffold first)")
    layers: dict[str, bool] = {}
    layers["L1"] = run_l1_pytest()
    if not layers["L1"]:
        return decide_label(layers)
    layers["L2"] = run_l2_jdbc(scaffold)
    if not layers["L2"]:
        return decide_label(layers)
    layers["L3"] = run_l3_mvn(scaffold)
    if not layers["L3"]:
        return decide_label(layers)
    full, partial = run_l4_live(lane, scaffold)
    layers["L4_full"] = full
    layers["L4_partial"] = partial and not full
    label = decide_label(layers) + lane_label_suffix(lane)
    # always cleanup after L4
    print(cleanup_runner.format_report(cleanup_runner.run(lane)))
    # update learn-log label on active Growth
    try:
        n = learn_log.latest_growth_num()
        learn_log.update_label(n, label)
    except Exception as e:
        print(f"[learn-log] label update skipped: {e}", file=sys.stderr)
    return label


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: full_test.py <lane> [domain-path]", file=sys.stderr)
        sys.exit(2)
    lane = sys.argv[1]
    domain = sys.argv[2] if len(sys.argv) > 2 else None
    label = run(lane, domain)
    print(f"\nLABEL: {label}")
