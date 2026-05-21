---
name: business-fullstack-creater:full-test
description: 4-layer 풀테스트 자동 실행 (pytest / JDBC / mvn / live WAS) + 라벨 자동판정
argument-hint: <lane> [domain] [--json]
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
