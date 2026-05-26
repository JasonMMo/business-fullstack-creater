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
