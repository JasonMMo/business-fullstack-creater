---
name: full-test-protocol
description: 풀테스트·전체검증·E2E검증 요청 시 반드시 따라야 하는 4계층 검증 절차와 4단계 라벨링 규칙. CLAUDE.md "풀테스트 검증 절차"의 상세 정의.
---

# 풀테스트 4계층 검증 절차

"풀테스트", "전체 검증", "E2E 검증" 같은 요청이 오면 **반드시 다음 4계층을 모두** 통과해야 완료로 본다. 어느 한 계층이라도 빠지면 풀테스트가 아니다.

> 자동 실행: `/full-test <lane> [domain]`. cleanup 자동 포함.

## 4계층 표

| # | 계층 | 검증 방법 | 빠지면 못 잡는 것 |
|---|---|---|---|
| 1 | **단위 (pytest)** | 각 레포 `pytest` 그린. sibling repo 0 개 발견 시 silent True 금지 — **FAIL** 처리(Growth-37) | 로직 회귀, worktree/sandbox 갭 |
| 2 | **JDBC 스모크** | dialect별 (a) schema apply, (b) seed insert, (c) FK/CHECK 위반 시도, (d) **도메인 invariant** 검증(예: 재무 double-entry, 주문 합계, audit 무결성) — HSQLDB 인-메모리. `HSQLDB_JAR` env 부재 시 **SKIP=PASS**(Growth-37) | dialect 컨트랙트(HSQLDB IDENTITY 0-base 트랩) + 도메인 규칙 위반 |
| 3 | **Maven 빌드** | Stage 3+5 산출물이 실제 `mvn -q package` 통과. pom 탐색은 `5-overlay/pom.xml` → `3-mybatis/pom.xml` → root 순(Growth-38) — Stage 3-only scaffold 도 빌드 가능 | annotation/패키지/Jakarta vs javax import 깨짐 |
| 4 | **라이브 WAS 스모크** | runner 위에서 기동 → endpoint **lane-aware** 호출(nexacro 는 POST envelope, jakarta/javax/vanilla 는 GET JSON) → **HTTP 200 + ErrorCode=0(또는 JSON list) + 기대 dataset 행수** 동시 확인. `/full-test <lane>` 의 L4 단계가 `live_overlay`+`live_runner`+`live_probe` 로 자동 수행(Growth-35~38). 잘못된 lane 은 진입 즉시 `ValueError`, post-ready 바인드 지연 자동 retry | lane × MyBatis × NexacroResult 직렬화 스택 깨짐, 컨테이너 응답 수준 dialect 영향(예: ID=0 payload 노출) |

## 4단계 라벨링 규칙

- 4계층 모두 PASS → **"풀테스트 그린"**
- 4 부분실패 (WAS는 떴으나 응답 깨짐/행수 불일치) → **"라이브 WAS 부분검증"** — 절대 그린 아님
- 1~3 PASS / 4 미실행 → **"JDBC + 빌드까지만 검증"**
- 1~2 PASS / 3 미실행 → **"JDBC 까지만 검증"**

## 재실행 트리거

새 도메인 / dialect / lane / shell / runner 버전 변경 시 4계층 전체.

## 연관 skill

- 러너 선택·매트릭스 — [[runner-matrix]]
- L4 종료 후 cleanup 명령 — [[runner-cleanup]]
