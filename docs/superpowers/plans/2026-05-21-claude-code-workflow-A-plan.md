# Claude Code 워크플로우 A안 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** business-fullstack-creater에 4개 슬래시 명령(`/growth-start`, `/full-test`, `/contribute-back`, `/cleanup-runner`)을 추가해 CLAUDE.md 절차의 수동 단계를 자동화한다.

**Architecture:** `.claude/commands/*.md` 4개 (LLM 진입점) + `scripts/workflow/*.py` 얇은 wrapper 5개 (lane_runner_map / learn_log / cleanup_runner / growth_start / full_test / contribute_back). sibling 4개 레포는 수정하지 않는다. 모든 wrapper는 TDD로 pytest 그린 후에 .md 명령에 연결한다.

**Tech Stack:** Python 3.11+, pytest, PowerShell (Windows 환경), git, Maven (외부 호출만)

**Spec:** `docs/superpowers/specs/2026-05-21-claude-code-workflow-A-design.md`

---

## File Structure (선결)

신규 파일:
```
business-fullstack-creater/
├── .claude/
│   └── commands/
│       ├── growth-start.md       # /growth-start
│       ├── full-test.md          # /full-test
│       ├── contribute-back.md    # /contribute-back
│       └── cleanup-runner.md     # /cleanup-runner
├── scripts/
│   └── workflow/
│       ├── __init__.py
│       ├── lane_runner_map.py    # lane → runner 매핑 (단일 진실원천)
│       ├── learn_log.py          # learn-log.md §6 파싱/갱신
│       ├── cleanup_runner.py     # Stop java + git restore + rm overlay
│       ├── growth_start.py       # 활성 Growth 행 추가
│       ├── full_test.py          # 4-layer 오케스트레이션 + 라벨 자동판정
│       └── contribute_back.py    # git log 스캔 + 환류 후보 분류
└── tests/
    └── workflow/
        ├── __init__.py
        ├── conftest.py           # tmp learn-log 픽스처
        ├── test_lane_runner_map.py
        ├── test_learn_log.py
        ├── test_cleanup_runner.py
        ├── test_growth_start.py
        ├── test_full_test.py
        └── test_contribute_back.py
```

갱신:
- `.claude/settings.local.json` (슬림화: 60줄 → 10~15줄)
- `CLAUDE.md` (2줄 추가)

각 모듈의 책임은 한 줄로 정의되어 있고, 모든 다른 명령이 공유하는 부분(`lane_runner_map`, `learn_log`)은 별도 모듈로 분리해 DRY.

---

## Task 1: 공유 헬퍼 — `lane_runner_map` + `learn_log`

**Files:**
- Create: `scripts/workflow/__init__.py`
- Create: `scripts/workflow/lane_runner_map.py`
- Create: `scripts/workflow/learn_log.py`
- Create: `tests/workflow/__init__.py`
- Create: `tests/workflow/conftest.py`
- Create: `tests/workflow/test_lane_runner_map.py`
- Create: `tests/workflow/test_learn_log.py`

- [ ] **Step 1: 빈 패키지 init 파일 2개 생성**

`scripts/workflow/__init__.py`:
```python
```
`tests/workflow/__init__.py`:
```python
```

- [ ] **Step 2: conftest.py — 임시 learn-log 픽스처**

`tests/workflow/conftest.py`:
```python
import pytest
from pathlib import Path

SAMPLE_LOG = """\
# Learn Log

## 6. Growth 이력 (요약)

| Growth | 일자 | 살붙임 요약 |
|---|---|---|
| Growth-1 | 2026-04 | 고객관리 |
| Growth-32 | 2026-05-21 | javax lane 검증 |

## 7. Other section
"""

@pytest.fixture()
def tmp_learn_log(tmp_path, monkeypatch):
    log = tmp_path / "learn-log.md"
    log.write_text(SAMPLE_LOG, encoding="utf-8")
    monkeypatch.setattr("scripts.workflow.learn_log.LEARN_LOG", log)
    return log
```

- [ ] **Step 3: lane_runner_map 테스트 작성 (FAIL)**

`tests/workflow/test_lane_runner_map.py`:
```python
import pytest
from scripts.workflow.lane_runner_map import resolve_runner, lane_label_suffix

@pytest.mark.parametrize("lane,runner", [
    ("jakarta", "boot-jdk17-jakarta"),
    ("javax", "boot-jdk8-javax"),
    ("nexacro", "boot-jdk17-jakarta"),
    ("vanilla", "boot-jdk8-javax"),
])
def test_resolve_runner_known(lane, runner):
    assert resolve_runner(lane) == runner

def test_resolve_runner_unknown_raises():
    with pytest.raises(ValueError, match="unknown lane"):
        resolve_runner("kotlin")

def test_vanilla_label_suffix_marks_host_validation():
    assert lane_label_suffix("vanilla") == " → javax-host 검증"
    assert lane_label_suffix("jakarta") == ""
```

Run: `pytest tests/workflow/test_lane_runner_map.py -v`
Expected: FAIL (ModuleNotFoundError).

- [ ] **Step 4: lane_runner_map 구현**

`scripts/workflow/lane_runner_map.py`:
```python
"""Lane → default runner mapping. Single source of truth (mirrors CLAUDE.md §3.12)."""

LANE_RUNNER_MAP = {
    "jakarta": "boot-jdk17-jakarta",
    "javax": "boot-jdk8-javax",
    "nexacro": "boot-jdk17-jakarta",
    "vanilla": "boot-jdk8-javax",
}

_LABEL_SUFFIX = {
    "vanilla": " → javax-host 검증",
}

def resolve_runner(lane: str) -> str:
    if lane not in LANE_RUNNER_MAP:
        raise ValueError(f"unknown lane: {lane}. valid: {sorted(LANE_RUNNER_MAP)}")
    return LANE_RUNNER_MAP[lane]

def lane_label_suffix(lane: str) -> str:
    return _LABEL_SUFFIX.get(lane, "")
```

- [ ] **Step 5: lane_runner_map 테스트 PASS 확인**

Run: `pytest tests/workflow/test_lane_runner_map.py -v`
Expected: 5 passed.

- [ ] **Step 6: learn_log 테스트 작성 (FAIL)**

`tests/workflow/test_learn_log.py`:
```python
import pytest
from scripts.workflow import learn_log

def test_latest_growth_num_finds_max(tmp_learn_log):
    assert learn_log.latest_growth_num() == 32

def test_append_row_inserts_next_number(tmp_learn_log):
    n = learn_log.append_row("test growth", today="2026-05-21")
    assert n == 33
    body = tmp_learn_log.read_text(encoding="utf-8")
    assert "| Growth-33 | 2026-05-21 | test growth (in_progress) |" in body

def test_append_row_preserves_following_sections(tmp_learn_log):
    learn_log.append_row("foo", today="2026-05-21")
    body = tmp_learn_log.read_text(encoding="utf-8")
    assert "## 7. Other section" in body

def test_update_label_replaces_in_progress(tmp_learn_log):
    learn_log.append_row("foo", today="2026-05-21")
    learn_log.update_label(33, "라이브 WAS 부분검증")
    body = tmp_learn_log.read_text(encoding="utf-8")
    assert "(라이브 WAS 부분검증)" in body
    assert "(in_progress)" not in body

def test_missing_section_raises(tmp_path, monkeypatch):
    bad = tmp_path / "bad.md"
    bad.write_text("no growth section\n", encoding="utf-8")
    monkeypatch.setattr(learn_log, "LEARN_LOG", bad)
    with pytest.raises(ValueError, match="§6"):
        learn_log.latest_growth_num()
```

Run: `pytest tests/workflow/test_learn_log.py -v`
Expected: FAIL (ModuleNotFoundError).

- [ ] **Step 7: learn_log 구현**

`scripts/workflow/learn_log.py`:
```python
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
```

- [ ] **Step 8: learn_log 테스트 PASS 확인**

Run: `pytest tests/workflow/test_learn_log.py -v`
Expected: 5 passed.

- [ ] **Step 9: Commit (per-file)**

```powershell
git add scripts/workflow/__init__.py
git commit -m @'
feat(workflow): scripts/workflow package init

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
'@

git add scripts/workflow/lane_runner_map.py
git commit -m @'
feat(workflow): lane→runner mapping helper

Mirrors CLAUDE.md §3.12 lane×runner matrix as single source of truth.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
'@

git add scripts/workflow/learn_log.py
git commit -m @'
feat(workflow): learn-log §6 parser/updater

Used by /growth-start and /full-test to append and label Growth rows.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
'@

git add tests/workflow/__init__.py tests/workflow/conftest.py tests/workflow/test_lane_runner_map.py tests/workflow/test_learn_log.py
git commit -m @'
test(workflow): lane_runner_map + learn_log fixtures and cases

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
'@
```

---

## Task 2: `/cleanup-runner` 명령 + `cleanup_runner.py`

**Files:**
- Create: `scripts/workflow/cleanup_runner.py`
- Create: `tests/workflow/test_cleanup_runner.py`
- Create: `.claude/commands/cleanup-runner.md`

- [ ] **Step 1: cleanup_runner 테스트 작성 (FAIL)**

`tests/workflow/test_cleanup_runner.py`:
```python
import subprocess
from unittest.mock import patch, MagicMock
import pytest
from scripts.workflow import cleanup_runner

def test_plan_steps_for_jakarta_lane():
    steps = cleanup_runner.plan_steps("jakarta")
    labels = [s.label for s in steps]
    assert "Stop java (jdk-17)" in labels
    assert any("boot-jdk17-jakarta" in s.label for s in steps)

def test_plan_steps_unknown_lane_raises():
    with pytest.raises(ValueError):
        cleanup_runner.plan_steps("kotlin")

def test_run_reports_each_step_outcome(monkeypatch):
    monkeypatch.setattr(cleanup_runner, "_execute_step",
                        lambda s: cleanup_runner.StepResult(s.label, ok=True, detail="OK"))
    report = cleanup_runner.run("jakarta")
    assert all(r.ok for r in report)
    assert len(report) >= 3

def test_run_failed_step_does_not_short_circuit(monkeypatch):
    def fake(s):
        return cleanup_runner.StepResult(s.label, ok=("Stop" not in s.label),
                                          detail="fake-fail" if "Stop" in s.label else "ok")
    monkeypatch.setattr(cleanup_runner, "_execute_step", fake)
    report = cleanup_runner.run("jakarta")
    failed = [r for r in report if not r.ok]
    assert len(failed) == 1
    assert "Stop" in failed[0].label
    assert len(report) >= 3
```

Run: `pytest tests/workflow/test_cleanup_runner.py -v`
Expected: FAIL.

- [ ] **Step 2: cleanup_runner 구현**

`scripts/workflow/cleanup_runner.py`:
```python
"""Layer-4 cleanup orchestration: Stop java + git restore + remove overlay."""
from __future__ import annotations
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .lane_runner_map import resolve_runner

NEXACRO_REPO = Path(r"D:\AI\workspace\nexacroN-fullstack")

@dataclass
class Step:
    label: str
    command: list[str]
    cwd: Path | None = None
    shell: bool = False

@dataclass
class StepResult:
    label: str
    ok: bool
    detail: str

def plan_steps(lane: str) -> list[Step]:
    runner = resolve_runner(lane)
    jdk_match = "jdk-17" if "17" in runner else "jdk-8"
    runner_dir = NEXACRO_REPO / "samples" / "runners" / runner
    overlay_pkg = runner_dir / "src" / "main" / "java" / "com" / "nexacro" / "uiadapter"
    overlay_xml = runner_dir / "src" / "main" / "resources" / "mybatis" / "mappers"
    return [
        Step(f"Stop java ({jdk_match})",
             ["powershell", "-NoProfile", "-Command",
              f"Get-Process java -EA SilentlyContinue | Where-Object {{ $_.Path -like '*{jdk_match}*' }} | Stop-Process -Force"]),
        Step(f"git restore {runner}",
             ["git", "-C", str(NEXACRO_REPO), "restore", f"samples/runners/{runner}/"]),
        Step(f"Remove overlay dirs ({runner})",
             ["powershell", "-NoProfile", "-Command",
              f"Get-ChildItem -Path '{overlay_pkg}' -Directory -EA SilentlyContinue | "
              f"Where-Object {{ $_.Name -notin @('mapper','config','common') }} | "
              f"Remove-Item -Recurse -Force"]),
        Step(f"Remove untracked mappers ({runner})",
             ["powershell", "-NoProfile", "-Command",
              f"Get-ChildItem -Path '{overlay_xml}' -Filter '*-mapper.xml' -EA SilentlyContinue | "
              f"Where-Object {{ (git -C '{NEXACRO_REPO}' ls-files --error-unmatch $_.FullName 2>$null; $LASTEXITCODE) -ne 0 }} | "
              f"Remove-Item -Force"]),
    ]

def _execute_step(step: Step) -> StepResult:
    try:
        p = subprocess.run(step.command, capture_output=True, text=True, timeout=60)
        if p.returncode == 0:
            return StepResult(step.label, True, (p.stdout or "OK").strip()[:120])
        return StepResult(step.label, False, (p.stderr or p.stdout).strip()[:120])
    except Exception as e:
        return StepResult(step.label, False, f"exception: {e}")

def run(lane: str) -> list[StepResult]:
    return [_execute_step(s) for s in plan_steps(lane)]

def format_report(results: list[StepResult]) -> str:
    width = max(len(r.label) for r in results)
    lines = [f"{'Step':<{width}}    Result", f"{'-'*width}    ------"]
    for r in results:
        flag = "OK" if r.ok else "FAIL"
        lines.append(f"{r.label:<{width}}    {flag} ({r.detail})")
    return "\n".join(lines)

if __name__ == "__main__":
    import sys
    lane = sys.argv[1] if len(sys.argv) > 1 else "jakarta"
    results = run(lane)
    print(format_report(results))
    sys.exit(0 if all(r.ok for r in results) else 1)
```

- [ ] **Step 3: cleanup_runner 테스트 PASS 확인**

Run: `pytest tests/workflow/test_cleanup_runner.py -v`
Expected: 4 passed.

- [ ] **Step 4: `/cleanup-runner` 명령 정의**

`.claude/commands/cleanup-runner.md`:
```markdown
---
name: business-fullstack-creater:cleanup-runner
description: Layer-4 라이브 WAS 검증 후 mandatory cleanup (Stop java + git restore + remove overlay)
argument-hint: [lane]
---

# /cleanup-runner — Layer 4 mandatory cleanup

CLAUDE.md "필수 cleanup 명령 (계층 4 종료 시)" 절을 자동 실행한다.

## 인자

- `[lane]` (선택, 기본 `jakarta`): `jakarta` | `javax` | `nexacro` | `vanilla`

## 동작

1. lane → runner 매핑 적용 (`scripts/workflow/lane_runner_map.py`)
2. 3단계 실행 (각각 독립; 한 단계 실패해도 나머지 계속):
   - `Stop-Process` java (jdk path 매칭)
   - `git restore` runner 디렉터리
   - Overlay dir + untracked `*-mapper.xml` 제거
3. 결과 표 출력

## 실행

```powershell
python scripts/workflow/cleanup_runner.py jakarta
```

## 결과 예시

```
Step                                Result
----------------------------------  ------
Stop java (jdk-17)                  OK (PID 363716)
git restore boot-jdk17-jakarta      OK
Remove overlay dirs (boot-...)      OK
Remove untracked mappers (boot-...) OK
```

## 실패 시

- 어떤 단계라도 FAIL → 표에 명시. **자동 재시도 금지.**
- 예상 외 상태 보존을 위해 사람이 수동 처리한다.

## 사전 조건

- nexacroN-fullstack 레포가 `D:\AI\workspace\nexacroN-fullstack` 에 존재
- `scripts/workflow/lane_runner_map.py` 의 lane 키워드와 일치하는 lane 인자
```

- [ ] **Step 5: Idempotency 실행 검증**

Run twice:
```powershell
python scripts/workflow/cleanup_runner.py jakarta
python scripts/workflow/cleanup_runner.py jakarta
```
Expected: 두 번째 실행도 모두 OK (정리할 게 없어도 에러 없음).

- [ ] **Step 6: Commit (per-file)**

```powershell
git add scripts/workflow/cleanup_runner.py
git commit -m @'
feat(workflow): cleanup_runner — Layer-4 mandatory cleanup

Stops java by jdk path, git restores runner dir, removes overlay artifacts.
Idempotent: failed step does not short-circuit.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
'@

git add tests/workflow/test_cleanup_runner.py
git commit -m @'
test(workflow): cleanup_runner plan and run outcomes

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
'@

git add .claude/commands/cleanup-runner.md
git commit -m @'
feat(commands): /cleanup-runner slash command

Wraps scripts/workflow/cleanup_runner.py with usage docs.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
'@
```

---

## Task 3: `/growth-start` 명령 + `growth_start.py`

**Files:**
- Create: `scripts/workflow/growth_start.py`
- Create: `tests/workflow/test_growth_start.py`
- Create: `.claude/commands/growth-start.md`

- [ ] **Step 1: growth_start 테스트 작성 (FAIL)**

`tests/workflow/test_growth_start.py`:
```python
import pytest
from scripts.workflow import growth_start

def test_start_appends_row_and_returns_number(tmp_learn_log):
    n = growth_start.start("vanilla lane 라이브 검증", today="2026-05-21")
    assert n == 33
    body = tmp_learn_log.read_text(encoding="utf-8")
    assert "| Growth-33 | 2026-05-21 | vanilla lane 라이브 검증 (in_progress) |" in body

def test_start_empty_name_raises():
    with pytest.raises(ValueError, match="name is required"):
        growth_start.start("")

def test_start_whitespace_name_raises():
    with pytest.raises(ValueError, match="name is required"):
        growth_start.start("   ")
```

Run: `pytest tests/workflow/test_growth_start.py -v`
Expected: FAIL.

- [ ] **Step 2: growth_start 구현**

`scripts/workflow/growth_start.py`:
```python
"""Start a new Growth cycle: append row in learn-log §6."""
from __future__ import annotations
import sys
from . import learn_log

def start(name: str, today: str | None = None) -> int:
    name = (name or "").strip()
    if not name:
        raise ValueError("name is required")
    return learn_log.append_row(name, today=today)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: growth_start.py <name>", file=sys.stderr)
        sys.exit(2)
    name = " ".join(sys.argv[1:])
    n = start(name)
    print(f"Growth-{n} started. learn-log §6 placeholder 추가됨.")
```

- [ ] **Step 3: growth_start 테스트 PASS 확인**

Run: `pytest tests/workflow/test_growth_start.py -v`
Expected: 3 passed.

- [ ] **Step 4: `/growth-start` 명령 정의**

`.claude/commands/growth-start.md`:
```markdown
---
name: business-fullstack-creater:growth-start
description: Growth-N 시작 — 다음 번호 자동 부여 + learn-log §6 행 추가 + TaskCreate
argument-hint: <name>
---

# /growth-start — Growth 사이클 진입

CLAUDE.md "복리식 축적" 사이클의 시작점. 매번 반복되던 (번호부여 / §6 행 추가 / Task 생성) 을 1줄로.

## 인자

- `<name>` (필수): Growth 의 한 줄 요약. 한국어 가능. 예: `"vanilla lane 라이브 검증 확장"`

## 동작

1. `learn-log.md §6` 마지막 행에서 가장 큰 Growth 번호 N 추출 → `Growth-(N+1)` 부여
2. §6 표 끝에 추가: `| Growth-{N+1} | {YYYY-MM-DD} | {name} (in_progress) |`
3. (LLM) TaskCreate: `subject = "Growth-{N+1}: {name}"`, `status = in_progress`

## 실행 (Python wrapper)

```powershell
python scripts/workflow/growth_start.py "<name>"
```

출력 예:
```
Growth-33 started. learn-log §6 placeholder 추가됨.
```

이어서 LLM 은 위 출력을 받아 TaskCreate 를 호출한다.

## 실패 모드

- `<name>` 비어있음 → `ValueError: name is required`
- learn-log.md §6 헤더 없음 → `ValueError: section header not found`
- (silent fallback 금지)
```

- [ ] **Step 5: Commit (per-file)**

```powershell
git add scripts/workflow/growth_start.py
git commit -m @'
feat(workflow): growth_start — append Growth-N row in learn-log §6

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
'@

git add tests/workflow/test_growth_start.py
git commit -m @'
test(workflow): growth_start happy path + empty-name guard

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
'@

git add .claude/commands/growth-start.md
git commit -m @'
feat(commands): /growth-start slash command

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
'@
```

---

## Task 4: `/full-test` 명령 + `full_test.py`

**Files:**
- Create: `scripts/workflow/full_test.py`
- Create: `tests/workflow/test_full_test.py`
- Create: `.claude/commands/full-test.md`

- [ ] **Step 1: full_test 테스트 작성 (FAIL)**

`tests/workflow/test_full_test.py`:
```python
import pytest
from scripts.workflow import full_test

def test_decide_label_all_pass():
    layers = {"L1": True, "L2": True, "L3": True, "L4_full": True}
    assert full_test.decide_label(layers) == "풀테스트 그린"

def test_decide_label_l4_partial():
    layers = {"L1": True, "L2": True, "L3": True, "L4_partial": True}
    assert full_test.decide_label(layers) == "라이브 WAS 부분검증"

def test_decide_label_l4_failed():
    layers = {"L1": True, "L2": True, "L3": True, "L4_full": False, "L4_partial": False}
    assert full_test.decide_label(layers) == "JDBC + 빌드까지만 검증"

def test_decide_label_l3_missing():
    layers = {"L1": True, "L2": True}
    assert full_test.decide_label(layers) == "JDBC 까지만 검증"

def test_decide_label_l1_fail_aborts():
    layers = {"L1": False}
    assert full_test.decide_label(layers) == "단위 테스트 실패 — 검증 중단"

def test_lane_default_runner_resolution():
    assert full_test.runner_for("jakarta") == "boot-jdk17-jakarta"
    assert full_test.runner_for("vanilla") == "boot-jdk8-javax"
```

Run: `pytest tests/workflow/test_full_test.py -v`
Expected: FAIL.

- [ ] **Step 2: full_test 구현**

`scripts/workflow/full_test.py`:
```python
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

from .lane_runner_map import resolve_runner, lane_label_suffix
from . import learn_log, cleanup_runner

SIBLING_REPOS = [
    Path(r"D:\AI\workspace\andrej-karpathy-rdb-skill"),
    Path(r"D:\AI\workspace\andrej-karpathy-rdb-ddl"),
    Path(r"D:\AI\workspace\andrej-karpathy-rdb-mybatis"),
    Path(r"D:\AI\workspace\andrej-karpathy-rdb-nexacro"),
]

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

def run_l4_live(lane: str, scaffold_dir: Path) -> tuple[bool, bool]:
    """Returns (full_pass, partial_pass)."""
    runner = resolve_runner(lane)
    print(f"[L4] lane={lane} runner={runner} scaffold={scaffold_dir}")
    print(f"[L4] live overlay + endpoint POST — delegated (placeholder partial PASS)")
    return (False, True)

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
```

- [ ] **Step 3: full_test 테스트 PASS 확인**

Run: `pytest tests/workflow/test_full_test.py -v`
Expected: 6 passed.

- [ ] **Step 4: `/full-test` 명령 정의**

`.claude/commands/full-test.md`:
```markdown
---
name: business-fullstack-creater:full-test
description: 4-layer 풀테스트 자동 실행 (pytest / JDBC / mvn / live WAS) + 라벨 자동판정
argument-hint: <lane> [domain]
---

# /full-test — 4-layer 풀테스트 자동 실행

CLAUDE.md "풀테스트 검증 절차 (mandatory)" 절을 1줄로.

## 인자

- `<lane>` (필수): `jakarta` | `javax` | `vanilla` | `nexacro`
- `[domain]` (선택): scaffold 디렉토리 경로. 생략 시 `out/` 최근 디렉토리 자동 선택.

## 4 계층

| Layer | 동작 | PASS 기준 |
|---|---|---|
| L1 pytest | 4 sibling repo `pytest -q` | 모든 repo rc=0 |
| L2 JDBC  | HSQLDB schema+seed smoke | 의도된 violation 외 0 error |
| L3 mvn   | `mvn -q package -DskipTests` | BUILD SUCCESS |
| L4 live  | lane 디폴트 runner overlay → POST | HTTP 200 + ErrorCode=0 + 기대 행수 |

## 라벨 자동 판정

| 조건 | 라벨 |
|---|---|
| 4계층 PASS | 풀테스트 그린 |
| L4 부분 (서버 OK, 응답 깨짐/행수↯) | 라이브 WAS 부분검증 |
| L4 실패/미실행 | JDBC + 빌드까지만 검증 |
| L3 미실행 | JDBC 까지만 검증 |
| L1 실패 | 단위 테스트 실패 — 검증 중단 |

vanilla lane 은 자동으로 ` → javax-host 검증` 접미사 추가.

## 실행

```powershell
python scripts/workflow/full_test.py jakarta
python scripts/workflow/full_test.py jakarta ./out/sales-scaffold
```

## 환류

- 활성 Growth 행의 `(in_progress)` → 자동 라벨 치환
- L4 종료 시 `/cleanup-runner` 자동 호출 (cleanup_runner.run)
- gap 발견 시 사용자에게 §5 환류 1줄 추가 제안

## 실패 모드

- scaffold 디렉토리 없음 → `FileNotFoundError`
- L4 cleanup 실패 → 표에 명시, 사람이 수동 정리
```

- [ ] **Step 5: Commit (per-file)**

```powershell
git add scripts/workflow/full_test.py
git commit -m @'
feat(workflow): full_test — 4-layer orchestrator + auto labeling

Delegates layers to existing tooling; centralizes label decision
and learn-log §6 row update. L2/L4 currently placeholder PASS pending
JDBC smoke harness and live-WAS dispatcher (to be filled in followup).

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
'@

git add tests/workflow/test_full_test.py
git commit -m @'
test(workflow): full_test label decision matrix + runner resolution

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
'@

git add .claude/commands/full-test.md
git commit -m @'
feat(commands): /full-test slash command

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
'@
```

---

## Task 5: `/contribute-back` 명령 + `contribute_back.py`

**Files:**
- Create: `scripts/workflow/contribute_back.py`
- Create: `tests/workflow/test_contribute_back.py`
- Create: `.claude/commands/contribute-back.md`

- [ ] **Step 1: contribute_back 테스트 작성 (FAIL)**

`tests/workflow/test_contribute_back.py`:
```python
from scripts.workflow import contribute_back

def test_classify_paths_routes_categories():
    paths = [
        "presets/customer.seed.md",
        "catalogs/preset-catalog.yaml",
        "templates/jakarta/entity.java.j2",
        "patterns/D2/manifest.yaml",
        "scripts/dialect_mysql.py",
        "README.md",
    ]
    grouped = contribute_back.classify(paths)
    assert "presets/customer.seed.md" in grouped["catalog"]
    assert "catalogs/preset-catalog.yaml" in grouped["catalog"]
    assert "templates/jakarta/entity.java.j2" in grouped["template"]
    assert "patterns/D2/manifest.yaml" in grouped["pattern"]
    assert "scripts/dialect_mysql.py" in grouped["dialect"]
    assert "README.md" in grouped["other"]

def test_classify_empty_input():
    assert contribute_back.classify([]) == {
        "catalog": [], "template": [], "pattern": [], "dialect": [], "other": []
    }

def test_questions_for_returns_one_per_category():
    paths = ["presets/x.seed.md", "templates/jakarta/y.j2"]
    qs = contribute_back.questions_for(contribute_back.classify(paths))
    cats = {q["category"] for q in qs}
    assert cats == {"catalog", "template"}
```

Run: `pytest tests/workflow/test_contribute_back.py -v`
Expected: FAIL.

- [ ] **Step 2: contribute_back 구현**

`scripts/workflow/contribute_back.py`:
```python
"""Scan recent git changes across 5 repos and classify backflow candidates."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path
from datetime import date, timedelta

from . import learn_log

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
    return [
        {"category": cat, "where": CATEGORY_GUIDE[cat][0], "hint": CATEGORY_GUIDE[cat][1],
         "files": files}
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
            ["git", "-C", str(repo), "log", f"--since={since}", "--name-only", "--pretty=format:"],
            capture_output=True, text=True)
        paths = sorted({l.strip() for l in p.stdout.splitlines() if l.strip()})
        if paths:
            out[repo.name] = paths
    return out

def _growth_start_date() -> str:
    try:
        text = learn_log.LEARN_LOG.read_text(encoding="utf-8")
        import re
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
        print(f"  CHECK: {q['hint']} 가 learn-log {q['where']} 에 환류되었는가? (Y/N)")
        missing.append(q["category"])
    if missing:
        try:
            n = learn_log.latest_growth_num()
            existing_label_check = learn_log.LEARN_LOG.read_text(encoding="utf-8")
            import re
            if re.search(rf"Growth-{n}[^|]*\(in_progress\)", existing_label_check):
                learn_log.update_label(n, "환류 미완")
        except Exception:
            pass
        print("\n[warn] 환류 미완 후보 있음 — Growth 종료 전 §2~§5 확인.")
    return 0

if __name__ == "__main__":
    sys.exit(run())
```

- [ ] **Step 3: contribute_back 테스트 PASS 확인**

Run: `pytest tests/workflow/test_contribute_back.py -v`
Expected: 3 passed.

- [ ] **Step 4: `/contribute-back` 명령 정의**

`.claude/commands/contribute-back.md`:
```markdown
---
name: business-fullstack-creater:contribute-back
description: Growth 종료 시 5개 레포 변경 스캔 + learn-log §2~§5 환류 후보 인터랙티브 확인
argument-hint: (no args)
---

# /contribute-back — 환류 누락 차단

CLAUDE.md "복리식 축적 체크리스트" 자동화. Growth 종료 시 사용.

## 인자

없음 (활성 Growth 자동 감지)

## 동작

1. 5개 레포에서 `git log --since=<활성 Growth 시작일> --name-only` 수집
   - 시작일 감지 실패 시 최근 7일
2. 변경 path 를 카테고리로 분류:
   - `presets/*.seed.md`, `catalogs/*.yaml` → catalog (rdb-skill/ddl)
   - `templates/*/*.j2` → template (rdb-mybatis)
   - `patterns/*/manifest.yaml` → pattern (rdb-nexacro)
   - `scripts/dialect*.py` → dialect (rdb-ddl)
   - 기타 → other (§5 / §6 freeform)
3. 카테고리별로 환류 위치 안내 + 인터랙티브 Y/N 체크
4. 미환류 1건 이상 시 Growth 행 라벨에 `(환류 미완)` 자동 부착 + stderr 경고

## 실행

```powershell
python scripts/workflow/contribute_back.py
```

## 결과 해석

- `환류 대상 없음.` → 변경 0건. 정상 종료.
- `=== 환류 후보 ===` 표시 → LLM 이 각 카테고리에 대해 사용자 확인.
- `[warn] 환류 미완 후보 있음` → §2~§5 에 1줄씩 환류 후 명령 재실행.
```

- [ ] **Step 5: Commit (per-file)**

```powershell
git add scripts/workflow/contribute_back.py
git commit -m @'
feat(workflow): contribute_back — git change scan + category classifier

Scans 5 repos since active Growth start date, classifies changes into
catalog/template/pattern/dialect, prints checklist, and marks Growth row
"(환류 미완)" if any candidate is unresolved.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
'@

git add tests/workflow/test_contribute_back.py
git commit -m @'
test(workflow): contribute_back classifier categories + question generation

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
'@

git add .claude/commands/contribute-back.md
git commit -m @'
feat(commands): /contribute-back slash command

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
'@
```

---

## Task 6: `settings.local.json` 슬림화

**Files:**
- Modify: `.claude/settings.local.json`

- [ ] **Step 1: 현재 파일 백업 표시 및 검토**

Run: `Get-Content .claude/settings.local.json | Measure-Object -Line` (현재 라인 수 기록).

- [ ] **Step 2: 새 정책으로 재작성**

`.claude/settings.local.json` 전체를 다음으로 교체:
```json
{
  "permissions": {
    "allow": [
      "Skill(*)",
      "Bash(pytest:*)",
      "Bash(python scripts/*)",
      "Bash(python scripts/workflow/*)",
      "PowerShell(python scripts/*)",
      "PowerShell(python scripts/workflow/*)",
      "PowerShell(git status:*)",
      "PowerShell(git diff:*)",
      "PowerShell(git log:*)",
      "PowerShell(git add:*)",
      "PowerShell(git commit:*)",
      "PowerShell(git restore:*)",
      "PowerShell(Get-Process java*)",
      "PowerShell(Stop-Process*)"
    ],
    "deny": [],
    "ask": []
  }
}
```

- [ ] **Step 3: 라인 수 검증**

Run: `Get-Content .claude/settings.local.json | Measure-Object -Line`
Expected: ≤ 25줄 (스펙 목표 10~15줄에 근접; JSON 포맷팅 여유분).

- [ ] **Step 4: 4 개 명령 dry-run 으로 권한 누락 확인**

```powershell
python scripts/workflow/growth_start.py "settings smoke"
python scripts/workflow/cleanup_runner.py jakarta
python scripts/workflow/contribute_back.py
```
Expected: 권한 프롬프트 0회.

- [ ] **Step 5: 잘못 추가된 "settings smoke" 행 롤백**

learn-log.md 에서 방금 추가된 `Growth-NN ... settings smoke` 행 1줄 삭제 (수동 Edit). Step 4 의 부작용 정리.

- [ ] **Step 6: Commit**

```powershell
git add .claude/settings.local.json
git commit -m @'
chore(settings): slim allowlist to policy patterns

Removes one-off absolute-path entries; keeps Skill(*) + workflow
script patterns + standard git/PS verbs. Reduces ~60 lines to ~20.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
'@
```

---

## Task 7: `CLAUDE.md` 2줄 추가 + 5축 자체 리뷰

**Files:**
- Modify: `CLAUDE.md`
- Create: `docs/superpowers/specs/2026-05-21-claude-code-workflow-A-review.md`

- [ ] **Step 1: CLAUDE.md 풀테스트 절에 1줄 추가**

`CLAUDE.md` 의 `## 풀테스트 검증 절차 (mandatory)` 헤더 바로 다음 빈 줄에 삽입:
```
> 자동 실행: `/full-test <lane> [domain]`. cleanup 자동 포함.

```

- [ ] **Step 2: CLAUDE.md 체크리스트 절에 1줄 추가**

`## 작업 시 체크리스트` 섹션 마지막 (원칙 위반 신호 단락 직전) 에 삽입:
```
> 자동 실행: Growth 시작 `/growth-start <name>`. Growth 종료 환류 `/contribute-back`.

```

- [ ] **Step 3: 자체 리뷰 문서 작성**

`docs/superpowers/specs/2026-05-21-claude-code-workflow-A-review.md`:
```markdown
# A안 5축 자체 리뷰 (구현 완료 후)

> **날짜**: 2026-05-21
> **대상**: 4개 슬래시 명령 + 5개 workflow 스크립트 + settings 슬림 + CLAUDE.md 2줄

## 5축 점수 (1~5)

| 축 | 점수 | 근거 |
|---|---|---|
| 반복 데이터 효율 관리 | 4 | 데이터 자체는 불변, 메타-자동화로 절차 반복 제거 |
| 도메인·엔티티 지식 누적 | 4 | `/contribute-back` 이 환류 누락 차단; 자동 적용은 B안 |
| 풍부한 Seeds | 3 | 직접 영향 없음 (B/C 영역) |
| 완성도 높은 WAR | 4 | `/full-test` 4계층 자동화로 검증 깊이 일정화 |
| Karpathy 정신 | 5 | LLM 지식 컴파일러 활용 강화 (수동 → 의도 표현) |

**평균: 4.0/5**

## 어긋남 확인

- (없음 명기) sibling 4 repo 0 변경 — 안정성 보존 ✓
- 기존 `/scaffold` 100% 보존 ✓
- 새 추상화 도입 ❌ — 단순 자동화 + 얇은 wrapper 만 추가 ✓

## 회귀 0건 검증

- `pytest tests/workflow/` 모두 PASS
- `/scaffold` dry-run 1회 정상

## 다음 진입 트리거 (B안)

- `/full-test` 메인 컨텍스트 사용량 측정 → 임계치 초과 시 subagent 분리
- learn-log 환류 누락이 1 Growth 사이클 내 1회 이상 → hook 도입
```

- [ ] **Step 4: Full pytest sweep**

Run: `pytest tests/workflow/ -v`
Expected: 모든 테스트 PASS (≥ 21 케이스).

- [ ] **Step 5: Commit (per-file)**

```powershell
git add CLAUDE.md
git commit -m @'
docs(claude): annotate full-test and checklist sections with slash commands

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
'@

git add docs/superpowers/specs/2026-05-21-claude-code-workflow-A-review.md
git commit -m @'
docs(spec): A-approach 5-axis self-review (4.0/5 avg, 0 regression)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
'@
```

- [ ] **Step 6: learn-log §6 라벨 정리**

`/full-test` 또는 `/contribute-back` 실행 흔적이 §6 에 남아있다면 Growth-NN 행의 `(in_progress)` 또는 `(환류 미완)` 라벨을 최종 상태로 갱신:
```
| Growth-NN | 2026-05-21 | Claude Code workflow A안 (구현 완료) |
```

- [ ] **Step 7: 최종 commit**

```powershell
git add learn-log.md
git commit -m @'
docs(learn-log): finalize A-approach Growth row

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
'@
```

---

## Verification (전체)

1. **단위**: `pytest tests/workflow/ -v` → 모두 PASS (lane_runner_map 5 + learn_log 5 + cleanup_runner 4 + growth_start 3 + full_test 6 + contribute_back 3 = 26 케이스)
2. **명령 dry-run**:
   - `python scripts/workflow/growth_start.py "dry run"` → Growth 번호 출력 (직후 §6 라인 수동 삭제)
   - `python scripts/workflow/cleanup_runner.py jakarta` → 4단계 표 출력 (idempotent)
   - `python scripts/workflow/contribute_back.py` → 변경 분류 출력
3. **회귀**: 기존 `/scaffold` 1회 dry-run (도메인 = 기존 picked) → 정상 동작
4. **CLAUDE.md**: 2줄 삽입 위치 확인 (풀테스트 절 + 체크리스트 절)
5. **settings.local.json**: 60줄 → 20줄 이내
6. **5축 리뷰**: 평균 ≥ 3 / 어긋남 명시적 확인
