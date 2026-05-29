"""4-layer full-test orchestrator with auto-labeling.
# Growth-83

Layer responsibilities (delegated to existing scripts/CLIs):
  L1: pytest in 4 sibling repos
  L2: HSQLDB schema-apply + seed-insert smoke
  L3: mvn -q package on Stage 3+5 scaffold output
  L4: live WAS overlay + endpoint POST verification

This module does NOT reimplement those layers — it orchestrates and labels.
"""
from __future__ import annotations
import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


def _mvn_cmd() -> str:
    """Resolve `mvn` to an absolute path. On Windows, subprocess cannot resolve
    `.cmd` shims via PATH without shell=True, so look up `mvn.cmd` explicitly."""
    return shutil.which("mvn") or shutil.which("mvn.cmd") or "mvn"

# Support both `python -m scripts.workflow.full_test` (package import)
# and `python scripts/workflow/full_test.py` (direct script invocation).
try:
    from .lane_runner_map import (
        resolve_runner, lane_label_suffix, lane_probe_kind, lane_probe_url,
        lane_supports_crud, lane_crud_kind,
    )
    from . import (
        learn_log, cleanup_runner, live_overlay, live_runner, live_probe,
        live_crud, live_crud_nexacro, jdbc_smoke,
    )
except ImportError:
    _root = str(Path(__file__).resolve().parents[2])
    if _root not in sys.path:
        sys.path.insert(0, _root)
    from scripts.workflow.lane_runner_map import (
        resolve_runner, lane_label_suffix, lane_probe_kind, lane_probe_url,
        lane_supports_crud, lane_crud_kind,
    )
    from scripts.workflow import (
        learn_log, cleanup_runner, live_overlay, live_runner, live_probe,
        live_crud, live_crud_nexacro, jdbc_smoke,
    )

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


def recovery_hint(layers: dict[str, bool], lane: str, scaffold: Path | None) -> str | None:
    """Return one-line next-step command for the layer that failed.

    R3 (서비스 리뷰 2026-05-26): 사용자가 풀테스트 실패 후 다음에 무엇을 할지
    추측하지 않아도 되도록, 실패한 레이어에 맞춰 진단 명령 1줄 제시.
    None = 모든 레이어 그린 (힌트 불필요).
    """
    if layers.get("L1") is False:
        return "Next: `pytest -q` (4 sibling repo 중 실패한 곳에서 -v 로 재실행)"
    if not layers.get("L2"):
        return "Next: `set HSQLDB_JAR=<path>` 확인 후 `python scripts/workflow/jdbc_smoke.py`"
    if not layers.get("L3"):
        loc = scaffold or "."
        return f"Next: `mvn -X package -DskipTests` in `{loc}` (-q 출력 부족 시 -X 로 verbose)"
    if not (layers.get("L4_full") or layers.get("L4_partial")):
        runner = runner_path_for(lane) if lane else None
        return (
            f"Next: runner 로그 확인 `Get-Content {runner}/was.log -Tail 60`"
            if runner else
            "Next: runner 로그(was.log) 마지막 60 줄 확인"
        )
    if layers.get("L4_partial") and not layers.get("L4_full"):
        return "Next: probe URL 직접 호출 (context-path `/uiadapter` 포함) — http_status/errcode/rows 확인"
    return None


def run_l1_pytest() -> bool:
    """Run pytest in each sibling repo. FAIL if no repos ran (silent-pass guard)."""
    ok = True
    ran = 0
    for repo in SIBLING_REPOS:
        if not repo.exists():
            print(f"[L1] skip (not found): {repo}", file=sys.stderr)
            continue
        p = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=repo, capture_output=True, text=True,
        )
        print(f"[L1] {repo.name}: rc={p.returncode}")
        ran += 1
        if p.returncode != 0:
            print(p.stdout[-1000:], file=sys.stderr)
            ok = False
    if ran == 0:
        print(f"[L1] FAIL: no sibling repos found (checked {len(SIBLING_REPOS)}) — L1 cannot silently pass", file=sys.stderr)
        return False
    return ok


def run_l2_jdbc(scaffold_dir: Path) -> bool:
    """Apply schema+data to in-memory HSQLDB. Missing jar → SKIP (warn, PASS)."""
    schema, data = jdbc_smoke.discover_sql(scaffold_dir)
    if schema is None or data is None:
        print(f"[L2] no schema/data under {scaffold_dir} (checked 3-mybatis/resources and 2-ddl)", file=sys.stderr)
        return False
    result = jdbc_smoke.run_smoke(schema, data)
    if result.skipped:
        print(f"[L2] SKIPPED: {result.reason}", file=sys.stderr)
        return True
    if result.stdout:
        print(result.stdout.strip())
    if not result.ok:
        print(f"[L2] FAIL: {result.reason}", file=sys.stderr)
        if result.stderr:
            print(result.stderr.strip()[-800:], file=sys.stderr)
        return False
    return True


def _find_pom(scaffold_dir: Path) -> Path | None:
    """Locate the buildable pom under scaffold. Order: 5-overlay → 3-mybatis → root.

    Stage 3-only scaffolds (no overlay step run yet) still have 3-mybatis/pom.xml;
    root pom.xml is the legacy fixture layout.
    """
    for rel in ("5-overlay/pom.xml", "3-mybatis/pom.xml", "pom.xml"):
        p = scaffold_dir / rel
        if p.exists():
            return p
    return None


def run_l3_mvn(scaffold_dir: Path) -> bool:
    pom = _find_pom(scaffold_dir)
    if pom is None:
        # Stage 3 (rdb-mybatis) does not emit pom.xml for nexacro lane — the
        # runner overlay (L4) supplies its own pom. Treat as SKIP=PASS, matching
        # the L2 HSQLDB_JAR-absent convention (Growth-37).
        print(f"[L3] SKIP: no pom.xml under {scaffold_dir} (runner provides pom at L4)", file=sys.stderr)
        return True
    p = subprocess.run([_mvn_cmd(), "-q", "package", "-DskipTests"],
                       cwd=pom.parent, capture_output=True, text=True, timeout=600)
    print(f"[L3] mvn rc={p.returncode} (pom={pom})")
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
        [_mvn_cmd(), "-q", "package", "-DskipTests"],
        cwd=runner_dir, capture_output=True, text=True, timeout=timeout_sec,
    )
    print(f"[L4] mvn rebuild runner rc={p.returncode}")
    if p.returncode != 0:
        print((p.stdout or "")[-800:], file=sys.stderr)
    return p.returncode == 0


def run_l4_live(
    lane: str,
    scaffold_dir: Path,
    layers: dict[str, bool] | None = None,
) -> tuple[bool, bool]:
    """Apply overlay → rebuild → start runner → probe → stop. Returns (full_pass, partial_pass).

    full_pass requires HTTP 200 + ErrorCode=0 + row_count>=1.
    partial_pass means runner reached ready state — verdict short of full.

    Growth-40: if `layers` is provided and the lane supports REST CRUD, an additional
    CRUD round-trip (insert + verify +1 + delete + verify back-to-baseline) is run.
    Result is written to layers["L4_crud"] (bool) and layers["L4_crud_reason"] (str).
    This does NOT affect the (full, partial) return values — CRUD is an enrichment,
    not a gate, so existing callers/labels are unaffected.
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
        # Growth-48 (T-Probe-LaneRunner-Mismatch): wire-protocol follows the
        # scaffold's own lane (what Stage 3 emitted), not the runner lane the
        # user picked. Fall back to runner `lane` when the report is missing.
        scaffold_lane = live_overlay.discover_scaffold_lane(scaffold_dir)
        if scaffold_lane and scaffold_lane != lane:
            print(f"[L4] scaffold_lane={scaffold_lane} differs from runner lane={lane} — probe/CRUD dispatch follows scaffold")
        url = lane_probe_url(lane, handle.port, entity, scaffold_lane=scaffold_lane)
        kind = lane_probe_kind(lane, scaffold_lane=scaffold_lane)
        if kind == "rest":
            verdict = live_probe.probe_endpoint_json(url, timeout_sec=L4_PROBE_TIMEOUT_SEC)
        else:
            verdict = live_probe.probe_endpoint(url, timeout_sec=L4_PROBE_TIMEOUT_SEC)
        print(f"[L4] probe kind={kind} url={url} http={verdict.http_status} errcode={verdict.error_code} rows={verdict.row_count}")
        full = verdict.ok

        # Growth-40/42: CRUD enrichment — dispatched by lane_crud_kind:
        #   rest      → live_crud.crud_roundtrip_rest        (jakarta/javax/vanilla)
        #   envelope  → live_crud_nexacro.crud_roundtrip_envelope (nexacro)
        if layers is not None and full and lane_supports_crud(lane, scaffold_lane=scaffold_lane):
            template = live_crud.build_insert_template(plan.data_sql, entity)
            if template is None:
                layers["L4_crud"] = False
                layers["L4_crud_reason"] = (
                    f"no MERGE template found for entity={entity} in {plan.data_sql}"
                )
                print(f"[L4] CRUD skipped — {layers['L4_crud_reason']}", file=sys.stderr)
            else:
                insert_row, pk_value = template
                ckind = lane_crud_kind(lane, scaffold_lane=scaffold_lane)
                if ckind == "rest":
                    crud = live_crud.crud_roundtrip_rest(
                        url, insert_row=insert_row, pk_column="id", pk_value=pk_value,
                        timeout_sec=L4_PROBE_TIMEOUT_SEC,
                    )
                else:  # envelope
                    save_url = live_crud_nexacro.nexacro_save_url(handle.port, entity)
                    dataset_id = live_crud_nexacro.nexacro_dataset_id(entity)
                    crud = live_crud_nexacro.crud_roundtrip_envelope(
                        select_url=url, save_url=save_url, dataset_id=dataset_id,
                        insert_row=insert_row, pk_column="id", pk_value=pk_value,
                        timeout_sec=L4_PROBE_TIMEOUT_SEC,
                    )
                layers["L4_crud"] = crud.ok
                layers["L4_crud_reason"] = crud.reason
                layers["L4_crud_kind"] = ckind
                print(
                    f"[L4] CRUD kind={ckind} ok={crud.ok} baseline={crud.baseline_count} "
                    f"+1={crud.after_insert_count} final={crud.after_delete_count} "
                    f"reason={crud.reason!r}"
                )

        if full:
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


@dataclass
class FullTestResult:
    """Structured outcome of run() — `str(result)` returns the label for legacy callers."""
    label: str
    layers: dict[str, bool] = field(default_factory=dict)
    lane: str = ""
    scaffold: Path | None = None
    next_hint: str | None = None

    def __str__(self) -> str:
        return self.label

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "lane": self.lane,
            "scaffold": str(self.scaffold) if self.scaffold is not None else None,
            "layers": dict(self.layers),
            "next_hint": self.next_hint,
        }


def _finalize(layers: dict[str, bool], lane: str, scaffold: Path | None) -> FullTestResult:
    return FullTestResult(
        label=decide_label(layers) + lane_label_suffix(lane),
        layers=layers,
        lane=lane,
        scaffold=scaffold,
        next_hint=recovery_hint(layers, lane, scaffold),
    )


def run(lane: str, domain: str | None = None) -> FullTestResult:
    # Fail fast on bad lane — don't burn L1/L2/L3 only to crash inside L4
    resolve_runner(lane)
    scaffold = Path(domain) if domain and Path(domain).exists() else find_latest_scaffold()
    if scaffold is None:
        raise FileNotFoundError("no scaffold directory found (pass [domain] or run /scaffold first)")
    layers: dict[str, bool] = {}
    layers["L1"] = run_l1_pytest()
    if not layers["L1"]:
        return _finalize(layers, lane, scaffold)
    layers["L2"] = run_l2_jdbc(scaffold)
    if not layers["L2"]:
        return _finalize(layers, lane, scaffold)
    layers["L3"] = run_l3_mvn(scaffold)
    if not layers["L3"]:
        return _finalize(layers, lane, scaffold)
    full, partial = run_l4_live(lane, scaffold, layers=layers)
    layers["L4_full"] = full
    layers["L4_partial"] = partial and not full
    result = _finalize(layers, lane, scaffold)
    # always cleanup after L4
    print(cleanup_runner.format_report(cleanup_runner.run(lane)), file=sys.stderr)
    # update learn-log label on active Growth
    if not os.environ.get("FULLTEST_NO_LEARNLOG"):
        try:
            n = learn_log.latest_growth_num()
            learn_log.update_label(n, result.label)
        except Exception as e:
            print(f"[learn-log] label update skipped: {e}", file=sys.stderr)
    return result


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="full_test.py", description="4-layer full-test orchestrator")
    p.add_argument("lane", help="jakarta | javax | vanilla | nexacro")
    p.add_argument("domain", nargs="?", default=None, help="scaffold dir (default: latest under ./out)")
    p.add_argument("--json", action="store_true", help="emit structured JSON to stdout (human text → stderr)")
    return p


def main(argv: list[str] | None = None) -> int:
    """CLI entry. Returns 0 on '풀테스트 그린', non-zero otherwise — CI can branch on rc."""
    args = _build_parser().parse_args(argv)
    if args.json:
        # Re-route per-layer prints to stderr so stdout stays JSON-only
        import builtins
        orig_print = builtins.print
        def _stderr_print(*a, **kw):
            kw.setdefault("file", sys.stderr)
            orig_print(*a, **kw)
        builtins.print = _stderr_print
        try:
            result = run(args.lane, args.domain)
        finally:
            builtins.print = orig_print
        sys.stdout.write(json.dumps(result.to_dict(), ensure_ascii=False))
        sys.stdout.write("\n")
    else:
        result = run(args.lane, args.domain)
        print(f"\nLABEL: {result.label}")
        if result.next_hint:
            print(result.next_hint)
    return 0 if result.layers.get("L4_full") else 1


if __name__ == "__main__":
    sys.exit(main())
