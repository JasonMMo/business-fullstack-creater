"""diagnose.py — Pre-flight checks before /full-test (Growth-52, 2026-05-26).

R3 recovery_hint 가 실패 *후* 다음 명령을 안내한다면, 이 스크립트는 실패 *전* 환경
조건을 확인한다. 5축 레이어 repo / preset 카탈로그 / nexacroN runner 디렉터리 /
JDK 가용성을 빠르게 점검하고 각 항목에 ✓/!/✗ + 회복 명령 1줄을 제공한다.

설계 원칙:
- 비싼 빌드(mvn/pytest) 호출 금지 — 파일/PATH 존재만 본다.
- 실패 시 R3 와 동일 형식 hint(다음 명령 1줄)를 보여준다.
- exit 0: 모든 critical PASS. exit 1: 하나라도 FAIL. WARN 은 통과.

CLI:
    python scripts/workflow/diagnose.py            # 사람용 표
    python scripts/workflow/diagnose.py --json     # 구조화 출력
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


# Resolve workspace root from this file's location (scripts/workflow/diagnose.py).
CREATER_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = CREATER_ROOT.parent

LAYER_REPOS = {
    "skill": "andrej-karpathy-rdb-skill",
    "ddl": "andrej-karpathy-rdb-ddl",
    "mybatis": "andrej-karpathy-rdb-mybatis",
    "nexacro": "andrej-karpathy-rdb-nexacro",
    "runners": "nexacroN-fullstack",
}

EXPECTED_RUNNERS = ("boot-jdk17-jakarta", "boot-jdk8-javax")


@dataclass
class Check:
    name: str
    status: str  # "PASS" | "WARN" | "FAIL"
    detail: str = ""
    hint: str = ""


def check_layer_repos(workspace: Path = WORKSPACE) -> list[Check]:
    out: list[Check] = []
    for axis, dirname in LAYER_REPOS.items():
        p = workspace / dirname
        if p.exists():
            out.append(Check(f"layer/{axis}", "PASS", str(p)))
        else:
            out.append(
                Check(
                    f"layer/{axis}",
                    "FAIL",
                    f"not found: {p}",
                    hint=f"clone {dirname} sibling to business-fullstack-creater/",
                )
            )
    return out


def check_preset_catalog(workspace: Path = WORKSPACE) -> Check:
    idx = (
        workspace
        / "andrej-karpathy-rdb-skill"
        / ".claude"
        / "skills"
        / "karpathy-rdb"
        / "presets"
        / "INDEX.md"
    )
    if not idx.exists():
        return Check(
            "preset-catalog",
            "FAIL",
            f"not found: {idx}",
            hint="check rdb-skill repo health (presets/INDEX.md missing)",
        )
    text = idx.read_text(encoding="utf-8")
    count = sum(
        1
        for ln in text.splitlines()
        if ln.startswith("## ") and not ln[3:].strip().startswith("매칭")
    )
    if count < 10:
        return Check(
            "preset-catalog",
            "WARN",
            f"only {count} domains parsed",
            hint="run /list-domains to inspect catalog",
        )
    return Check("preset-catalog", "PASS", f"{count} domains")


def check_learn_log(creater_root: Path = CREATER_ROOT) -> Check:
    log = creater_root / "learn-log.md"
    if not log.exists():
        return Check(
            "learn-log",
            "FAIL",
            "learn-log.md missing",
            hint="git status — file may be deleted accidentally",
        )
    text = log.read_text(encoding="utf-8")
    if "## 0. Layer Ownership Card" not in text:
        return Check(
            "learn-log",
            "WARN",
            "§0 Layer Ownership Card not found",
            hint="Phase A alignment regressed — restore §0 5축 표",
        )
    return Check("learn-log", "PASS", "§0 present")


def check_runners(workspace: Path = WORKSPACE) -> list[Check]:
    runners_root = workspace / "nexacroN-fullstack" / "samples" / "runners"
    if not runners_root.exists():
        return [
            Check(
                "runner/root",
                "FAIL",
                f"not found: {runners_root}",
                hint="nexacroN-fullstack repo missing or moved",
            )
        ]
    out: list[Check] = []
    for name in EXPECTED_RUNNERS:
        p = runners_root / name
        if not p.exists():
            out.append(
                Check(
                    f"runner/{name}",
                    "FAIL",
                    "runner directory missing",
                    hint="nexacroN-fullstack repo incomplete",
                )
            )
            continue
        # Detect stale generated overlay — com/example dir indicates leftover scaffold.
        com_example = p / "src" / "main" / "java" / "com" / "example"
        if com_example.exists():
            out.append(
                Check(
                    f"runner/{name}",
                    "WARN",
                    "stale generated overlay (com/example present)",
                    hint=f"python scripts/workflow/cleanup_runner.py {name}",
                )
            )
        else:
            out.append(Check(f"runner/{name}", "PASS", "clean"))
    return out


def check_cross_layer_coherence(
    *, workspace: Path = WORKSPACE, creater_root: Path = CREATER_ROOT
) -> Check:
    """Static regression guards for known cross-layer break traps (Growth-53).

    learn-log §4 트랩 이력에서 도출. 각 sub-check 는 grep-level 정적 검증이라
    빠르고 fresh scaffold 없이 회귀 감지. 새 트랩 발견 시 §4 등재 후 sub-check
    추가가 다음 Growth 단계.

    Guards (8건):
      - G-47 (T-NexacroUiaPkg-javax): mybatis controller/service-impl 템플릿이
        `{{ uia_namespace }}` parametrize — `.jakarta.core.` 하드코딩 회귀 차단
      - G-50a (T-Probe-CtxPath-Missing, runner-side): nexacroN samples/runners/
        `application.yml` 들이 `context-path: /uiadapter` 일관 유지
      - G-50b (T-Probe-CtxPath-Missing, dispatcher-side): `lane_runner_map.py`
        REST 분기가 `/uiadapter/api/` prefix 유지
      - G-48 (T-Probe-LaneRunner-Mismatch): `full_test.py:run_l4_live` 가
        `discover_scaffold_lane` 호출 + `scaffold_lane=` dispatch wiring 유지
      - G-58 (T-Stage4-VanillaReject): `scaffold_orchestrator._run_stage4` 가
        vanilla lane 자동 skip 유지 — `args.lane == "vanilla"` 분기 +
        `stage4-skipped-vanilla` 마커가 사라지면 vanilla `/scaffold` 가
        Stage 4 의 N002 unsupported version 거부로 다시 깨짐
      - G-61 (T-Web-CatalogSlugMismatch): `web_index._default_source_resolver` 가
        `discover_scaffold(..., domain_slug=None)` 호출 유지 — 한글 catalog
        서브디렉터리명을 ASCII Java slug 로 오용하면 Controller/Service preview
        가 silent placeholder 폴백
      - G-62 (Growth-63 Customer Profile axis): `scaffold_cli.py` 가 6번째 축
        loader (`load_customer_profile`) + `--customer-profile` 플래그 + `version: 1`
        강제 + `customer_profile=` 전달을 유지. 한 줄이라도 회귀하면 profile 이
        조용히 무시되어 2번째 도메인 자동 적용이 깨진다.
      - G-63 (Growth-65 Customer Profile version-pin): `scaffold_cli.py:load_customer_profile`
        의 `version != 1` 조건 분기가 유지 — 제거 시 `version: 2` 이상 프로파일이
        조용히 수락되어 미래 스키마 변경과 혼용되는 silent-corruption 트랩.
      - G-69 (Growth-69 Web-axis subprocess invariant): web layer 가 6-axis 누적을
        우회하지 않는다 — `web/adapters/scaffold_runner.py` 가 반드시 `subprocess.run`
        으로 `scripts/scaffold_cli.py` 를 호출하고 `web/routes/domain.py` 가
        `scaffold_runner.run` 을 호출. 직접 import/재구현하면 customer-profile, lane,
        preset 등 모든 축의 누적 효과가 web 경로에서 깨진다.
      - G-70 (Growth-70 target_project extractor contract): `scripts/extract_target_profile.py`
        가 v1 customer profile 만 emit 한다 — `build_profile()` 결과에 `version: 1` +
        `customer.slug` 가 박혀있고 `dump_profile()` 헤더가 Growth-70 을 명시.
        회귀하면 추출된 profile 이 `load_customer_profile` 의 G-62/G-63 가드를 통과
        못해 M5 입력단이 깨지면서 6번째 축이 우회된다.
    """
    failures: list[str] = []

    # G-47: mybatis 두 템플릿이 {{ uia_namespace }} 사용
    mybatis_tpl = (
        workspace
        / "andrej-karpathy-rdb-mybatis"
        / ".claude"
        / "skills"
        / "karpathy-rdb-mybatis"
        / "templates"
    )
    for tpl_rel in (
        "controller/controller.java.j2",
        "service/service-impl.java.j2",
    ):
        tpl_path = mybatis_tpl / tpl_rel
        if not tpl_path.exists():
            failures.append(f"G-47 guard: missing {tpl_rel}")
            continue
        text = tpl_path.read_text(encoding="utf-8")
        if "{{ uia_namespace }}" not in text:
            failures.append(f"G-47 regression: {tpl_rel} lost uia_namespace parametrization")

    # G-50a: 모든 runner application.yml 에 context-path: /uiadapter
    runners_root = workspace / "nexacroN-fullstack" / "samples" / "runners"
    if runners_root.exists():
        ymls = sorted(runners_root.glob("*/src/main/resources/application.yml"))
        if not ymls:
            failures.append("G-50a guard: no runner application.yml found")
        else:
            missing = [
                yml.parents[3].name
                for yml in ymls
                if "context-path: /uiadapter" not in yml.read_text(encoding="utf-8")
            ]
            if missing:
                failures.append(
                    f"G-50a regression: runner(s) missing /uiadapter context-path: {', '.join(missing)}"
                )

    # G-50b: lane_runner_map.py REST 분기가 /uiadapter/api/ 유지
    lrm = creater_root / "scripts" / "workflow" / "lane_runner_map.py"
    if not lrm.exists():
        failures.append("G-50b guard: lane_runner_map.py missing")
    else:
        text = lrm.read_text(encoding="utf-8")
        if "/uiadapter/api/" not in text:
            failures.append(
                "G-50b regression: lane_runner_map.py lost /uiadapter/api/ prefix"
            )

    # G-48: full_test.py 가 discover_scaffold_lane 호출 + scaffold_lane= dispatch
    ft = creater_root / "scripts" / "workflow" / "full_test.py"
    if not ft.exists():
        failures.append("G-48 guard: full_test.py missing")
    else:
        text = ft.read_text(encoding="utf-8")
        if "discover_scaffold_lane" not in text or "scaffold_lane=" not in text:
            failures.append(
                "G-48 regression: full_test.py lost discover_scaffold_lane wiring"
            )

    # G-58: scaffold_orchestrator._run_stage4 vanilla lane auto-skip 유지
    orch = creater_root / "scripts" / "scaffold_orchestrator.py"
    if not orch.exists():
        failures.append("G-58 guard: scaffold_orchestrator.py missing")
    else:
        text = orch.read_text(encoding="utf-8")
        if (
            'args.lane == "vanilla"' not in text
            or "stage4-skipped-vanilla" not in text
        ):
            failures.append(
                "G-58 regression: scaffold_orchestrator.py lost vanilla Stage 4 skip gate"
            )

    # G-61: web_index._default_source_resolver 가 domain_slug=None 전달 유지
    wi = creater_root / "scripts" / "workflow" / "web_index.py"
    if not wi.exists():
        failures.append("G-61 guard: web_index.py missing")
    else:
        text = wi.read_text(encoding="utf-8")
        if "domain_slug=None" not in text or "domain_slug=entry.domain" in text:
            failures.append(
                "G-61 regression: web_index._default_source_resolver lost domain_slug=None"
            )

    # G-62: scaffold_cli.py customer-profile (6th axis) loader + flag + version
    # enforcement + ScaffoldArgs forwarding all intact.
    cli = creater_root / "scripts" / "scaffold_cli.py"
    if not cli.exists():
        failures.append("G-62 guard: scaffold_cli.py missing")
    else:
        text = cli.read_text(encoding="utf-8")
        missing_markers = [
            m
            for m in (
                "def load_customer_profile(",
                '"--customer-profile"',
                'expected 1',
                "customer_profile=",
            )
            if m not in text
        ]
        if missing_markers:
            failures.append(
                "G-62 regression: scaffold_cli.py customer-profile wiring lost "
                f"({', '.join(missing_markers)})"
            )

    # G-63: scaffold_cli.py load_customer_profile 의 version != 1 조건 분기 유지
    if not cli.exists():
        failures.append("G-63 guard: scaffold_cli.py missing")
    else:
        text = cli.read_text(encoding="utf-8")
        if "version != 1" not in text:
            failures.append(
                "G-63 regression: scaffold_cli.py load_customer_profile lost version != 1 pin"
            )

    # G-69: web/adapters/scaffold_runner.py 가 subprocess.run 으로 scaffold_cli.py
    # 호출 + web/routes/domain.py 가 scaffold_runner.run 사용. web 경로에서
    # 6-axis 누적 우회를 차단.
    runner = creater_root / "web" / "adapters" / "scaffold_runner.py"
    if not runner.exists():
        failures.append("G-69 guard: web/adapters/scaffold_runner.py missing")
    else:
        text = runner.read_text(encoding="utf-8")
        runner_markers = [
            m
            for m in (
                "subprocess.run",
                "scaffold_cli",
                "scaffold_cli_path",
                "def run(",
            )
            if m not in text
        ]
        if runner_markers:
            failures.append(
                "G-69 regression: scaffold_runner.py lost subprocess pipeline "
                f"({', '.join(runner_markers)})"
            )

    domain_route = creater_root / "web" / "routes" / "domain.py"
    if not domain_route.exists():
        failures.append("G-69 guard: web/routes/domain.py missing")
    else:
        text = domain_route.read_text(encoding="utf-8")
        if "scaffold_runner.run" not in text:
            failures.append(
                "G-69 regression: web/routes/domain.py lost scaffold_runner.run call"
            )

    # G-70: extract_target_profile.py emits v1 customer profile (M5 Slice C).
    # build_profile() must stamp `"version": 1` + `"slug"` and dump_profile()
    # header must reference Growth-70. Regression breaks the M5 input path
    # because emitted YAML would fail load_customer_profile's G-62/G-63 pin.
    extractor = creater_root / "scripts" / "extract_target_profile.py"
    if not extractor.exists():
        failures.append("G-70 guard: scripts/extract_target_profile.py missing")
    else:
        text = extractor.read_text(encoding="utf-8")
        extractor_markers = [
            m
            for m in (
                "def build_profile(",
                '"version": 1',
                '"slug": slug',
                "Growth-70",
            )
            if m not in text
        ]
        if extractor_markers:
            failures.append(
                "G-70 regression: extract_target_profile.py lost v1 emission contract "
                f"({', '.join(extractor_markers)})"
            )

    if failures:
        return Check(
            "cross-layer-coherence",
            "FAIL",
            "; ".join(failures),
            hint="learn-log §4 트랩 회귀 — 해당 Growth commit (G-47/48/50/58/61/62/63/69/70) 추적 후 복원",
        )
    return Check(
        "cross-layer-coherence",
        "PASS",
        "10 trap guards intact (G-47/48/50a/50b/58/61/62/63/69/70)",
    )


def check_jdk() -> Check:
    java = shutil.which("java")
    if not java:
        return Check(
            "jdk",
            "FAIL",
            "java not on PATH",
            hint="install JDK17 and set JAVA_HOME",
        )
    try:
        r = subprocess.run(
            [java, "-version"], capture_output=True, text=True, timeout=10
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        return Check("jdk", "FAIL", f"java -version failed: {e}", hint="check JAVA_HOME")
    ver_line = (r.stderr or r.stdout).splitlines()[0:1]
    ver = ver_line[0] if ver_line else "(unknown)"
    if "17." in ver or '"17' in ver:
        return Check("jdk", "PASS", ver)
    return Check(
        "jdk",
        "WARN",
        f"{ver} (JDK17 preferred for runners)",
        hint="set JAVA_HOME to a JDK17 install for L3/L4 builds",
    )


def run_all_checks(
    *, workspace: Path | None = None, creater_root: Path | None = None
) -> list[Check]:
    # Resolve at call time so monkeypatch on module-level constants works.
    ws = workspace if workspace is not None else WORKSPACE
    cr = creater_root if creater_root is not None else CREATER_ROOT
    checks: list[Check] = []
    checks.extend(check_layer_repos(ws))
    checks.append(check_preset_catalog(ws))
    checks.append(check_learn_log(cr))
    checks.extend(check_runners(ws))
    checks.append(check_cross_layer_coherence(workspace=ws, creater_root=cr))
    checks.append(check_jdk())
    return checks


def format_table(checks: list[Check]) -> str:
    if not checks:
        return "(no checks ran)"
    icons = {"PASS": "OK ", "WARN": "!  ", "FAIL": "X  "}
    name_w = max(len(c.name) for c in checks)
    lines = ["Pre-flight diagnose:"]
    for c in checks:
        icon = icons.get(c.status, "?  ")
        lines.append(f"  {icon} {c.name:<{name_w}}  {c.detail}")
        if c.hint:
            lines.append(f"    -> {c.hint}")
    fails = sum(1 for c in checks if c.status == "FAIL")
    warns = sum(1 for c in checks if c.status == "WARN")
    lines.append("")
    if fails:
        lines.append(
            f"{fails} FAIL, {warns} WARN — fix critical issues before /full-test"
        )
    elif warns:
        lines.append(
            f"{len(checks) - warns} PASS, {warns} WARN — /full-test should run"
        )
    else:
        lines.append(f"All {len(checks)} checks PASS — ready for /full-test")
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="diagnose.py",
        description="Pre-flight environment checks before /full-test",
    )
    p.add_argument("--json", action="store_true", help="JSON output instead of table")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    checks = run_all_checks()
    if args.json:
        sys.stdout.write(
            json.dumps([asdict(c) for c in checks], ensure_ascii=False, indent=2)
        )
        sys.stdout.write("\n")
    else:
        print(format_table(checks))
    return 1 if any(c.status == "FAIL" for c in checks) else 0


if __name__ == "__main__":
    sys.exit(main())
