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
