# CLAUDE.md — business-fullstack-creater

## 프로젝트 성격

이 프로젝트는 **계속 성장하는 프로젝트**다. 일회성 스캐폴드 도구가 아니라, 사용 횟수에 비례해 자산이 누적되어야 한다.

## 핵심 운영 원칙 — 도메인 깊이의 복리식 축적

새 도메인을 다루거나 기존 도메인을 다시 만질 때마다, 다음 3개 축에서 **살을 붙이며 깊이를 더해가야 한다**:

| 축 | 누적 위치 | 깊이의 의미 |
|---|---|---|
| **Backend (Stage 2)** | `andrej-karpathy-rdb-ddl/catalogs/preset-catalog.yaml`, dialect 어댑터(postgres/hsqldb/mysql) | 더 많은 entity·관계·dialect별 인덱스/제약 |
| **Middle (Stage 3)** | `andrej-karpathy-rdb-mybatis/templates/<lane>/`, lane(nexacro/vanilla/jakarta/javax) | 더 풍부한 service 분기·매퍼·lane별 어댑터 변형 |
| **Frontend (Stage 4+5)** | `andrej-karpathy-rdb-nexacro/patterns/`, UI overlay(nexacro/react) | 더 다양한 화면 패턴(D2/F1/C1...)·overlay 어댑터 |

## 작업 시 체크리스트

도메인/엔티티/구현 방식이 등장하는 작업을 할 때 항상 자문:

1. **이번에 다룬 도메인 지식이 catalog/preset/seed에 환류되었는가?**
   - 아니면 다음 프로젝트는 같은 출발점에서 시작하게 됨
2. **새로 발견한 구현 패턴(backend dialect, middle lane, ui overlay)이 어댑터/템플릿으로 등록되었는가?**
   - 아니면 일회성 코드로 휘발됨
3. **wiki/learn-log.md (또는 동등 위치)에 1줄 기록되었는가?**
   - 복리식 축적의 단위 행위

**원칙 위반 신호**: "이번만 임시로", "다음에 정리하자", "한 번만 쓸 코드인데" — 이 표현이 떠오르면 **반드시 멈추고 catalog/template/preset에 등록할 방법을 먼저 찾는다**.

## 풀테스트 검증 절차 (mandatory)

"풀테스트", "전체 검증", "E2E 검증" 같은 요청이 오면 **반드시 다음 4계층을 모두** 통과해야 완료로 본다. 어느 한 계층이라도 빠지면 풀테스트가 아니다.

| # | 계층 | 검증 방법 | 빠지면 못 잡는 것 |
|---|---|---|---|
| 1 | **단위 (pytest)** | 각 레포 `pytest` 그린 | 로직 회귀 |
| 2 | **JDBC 스모크** | dialect별 (a) schema apply, (b) seed insert, (c) FK/CHECK 위반 시도, (d) **도메인 invariant** 검증(예: 재무 double-entry, 주문 합계, audit 무결성) — HSQLDB 인-메모리로 충분 | dialect 컨트랙트(HSQLDB IDENTITY 0-base 트랩 §3.11) + 도메인 규칙 위반 |
| 3 | **Maven 빌드** | Stage 3+5 산출물이 실제 `mvn -q package` 통과 | annotation/패키지/Jakarta vs javax import 깨짐 |
| 4 | **라이브 WAS 스모크** | runner 위에서 기동 → endpoint POST → **HTTP 200 + ErrorCode=0 + 기대 dataset 행수** 동시 확인 (절차: USER-GUIDE §3.12, 검증 후 `git restore` + java 프로세스 정지 필수) | lane × MyBatis × NexacroResult 직렬화 스택 깨짐, 컨테이너 응답 수준 dialect 영향(예: ID=0 payload 노출) |

**판정 규칙 (4단계 라벨링):**
- 4계층 모두 PASS → **"풀테스트 그린"**
- 4 부분실패 (WAS는 떴으나 응답 깨짐/행수 불일치) → **"라이브 WAS 부분검증"** — 절대 그린 아님
- 1~3 PASS / 4 미실행 → **"JDBC + 빌드까지만 검증"**
- 1~2 PASS / 3 미실행 → **"JDBC 까지만 검증"**

**재실행 트리거:** 새 도메인 / dialect / lane / shell / runner 버전 변경 시 4계층 전체.

**라이브 WAS 검증대 (lane × runner):**

| lane | 디폴트 러너 | 상태 |
|---|---|---|
| jakarta | `nexacroN-fullstack/samples/runners/boot-jdk17-jakarta` | ✅ 검증됨 (Growth-28) |
| vanilla | TBD | ⚠️ **검증대 부재** — 이 lane은 현재 계층 1~3 까지만 검증 가능 |
| javax | TBD | ⚠️ **검증대 부재** — 이 lane은 현재 계층 1~3 까지만 검증 가능 |

vanilla/javax lane 산출물에 대해서는 "JDBC + 빌드까지만 검증" 라벨이 영구 한계 — 러너 추가(Growth-30)되면 그 시점에 위 표를 갱신한다.

**필수 cleanup 명령 (계층 4 종료 시):**

```powershell
# 1. java 프로세스 정지 (PID 누락 방지 위해 jdk-17 path 매칭으로 찾기)
Get-Process java -EA SilentlyContinue | Where-Object { $_.Path -like "*jdk-17*" } | Stop-Process -Force
# 2. runner 원복 (예: jakarta)
git -C D:\AI\workspace\nexacroN-fullstack restore samples/runners/boot-jdk17-jakarta/
# 3. 오버레이 생성 파일 제거 (§3.12 참조)
```

## 왜 이 원칙이 중요한가

사용자 의도 verbatim:
> "반복되는 데이터를 효율적으로 관리하고 싶어서 andrej-karpathy의 지식 관리 방식을 적용하고 싶었다. ... 사용자가 요청하는 업무(도메인), 요소(entity)를 지식으로 쌓아서 결국 풍부한 Seeds를 만들어서 완성도 높은 결과물(war)를 제공하고 싶었다."

복리식 축적이 깨지면 이 프로젝트는 그저 또 하나의 코드 제너레이터가 된다. 매 작업마다 **카탈로그·템플릿·시드가 살이 붙는다**는 점을 산출물의 일부로 본다.

## 참조

- 정렬 리뷰: `docs/superpowers/specs/2026-05-15-karpathy-alignment-review.md`
- 실행 플랜: `C:\Users\mo\.claude\plans\delightful-swimming-hanrahan.md`
