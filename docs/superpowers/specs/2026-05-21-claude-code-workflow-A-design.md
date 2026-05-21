# Claude Code 워크플로우 보강 — A안 설계 (슬래시 명령 4개)

> **작성**: 2026-05-21
> **범위**: `business-fullstack-creater/.claude/` 만 변경. sibling 4개 레포(rdb-skill/ddl/mybatis/nexacro)는 안정성 보존을 위해 손대지 않는다.
> **모드**: A → B → (C는 v0.7 마켓플레이스 단계로 보류). 본 문서는 A 안만.

---

## 1. 동기 & 진단

### 1.1 사용자 의도 (verbatim, CLAUDE.md에서 인용)

> "반복되는 데이터를 효율적으로 관리하고 싶어서 andrej-karpathy의 지식 관리 방식을 적용하고 싶었다. ... 사용자가 요청하는 업무(도메인), 요소(entity)를 지식으로 쌓아서 결국 풍부한 Seeds를 만들어서 완성도 높은 결과물(war)를 제공하고 싶었다."

이 의도는 **복리식 축적**이 깨지지 않는 한에서만 유효하다 (CLAUDE.md 핵심 원칙).

### 1.2 현재 셋업 진단

| 레포 | `.claude/` 자산 | 일관성 |
|---|---|---|
| rdb-skill (S1) | skill + commands 4 + 14 preset | 가장 완성 |
| rdb-ddl (S2) | skill + command 1 + 3 dialect 템플릿 | plugin.json 없음 |
| rdb-mybatis (S3) | plugin.json + skill + command + 4 lane 템플릿 | OK |
| rdb-nexacro (S4) | plugin.json + skill + command + 7 패턴 | OK |
| **biz-fullstack** (오케스트레이터) | **command 1 (`/scaffold`) + 60줄 ad-hoc allowlist** | **자동화 명령 부족** |

### 1.3 갭 (A안이 해결하는 4개)

1. **운영 절차의 슬래시 명령 부재** — CLAUDE.md "체크리스트 / 풀테스트 4계층 / cleanup" 모두 사람이 매번 읽고 수동 실행
2. **풀테스트 4계층 자동화 부재** — Layer 4 라이브 WAS는 매번 수동 Stop-Process / git restore / Remove-Item
3. **환류 hook 부재** — commit 후 learn-log 1줄 추가 누락이 사람 기억에 의존
4. **settings.local.json 노이즈** — 60줄 일회성 allowlist

> B안 영역(subagent 분리, plugin.json 일관 배포, hooks) 및 C안 영역(진실원천 통합)은 본 문서 범위 외.

---

## 2. A안 결정

`business-fullstack-creater/.claude/commands/` 에 슬래시 명령 4개를 추가하여 CLAUDE.md 절차의 **자동 실행 진입점**을 제공한다.

**비목표**:
- 새 추상화 도입 (CLAUDE.md 절차의 자동화일 뿐)
- sibling 레포 변경 (안정성 보존)
- subagent / hook / plugin.json 정비 (B/C 영역)

**범위 차단**:
- 본 안에서 명령이 호출하는 Python/Powershell 로직은 **기존 스크립트의 조합**만 사용. 새 모듈 작성 금지.
- 새로 만드는 것은 `.md` 명령 정의 + 얇은 wrapper 스크립트(필요 시 `scripts/` 하위) 만.

---

## 3. 명령 4개 상세

### 3.1 `/growth-start <name>`

**목적**: Growth-N 시작 시 매번 반복되는 4가지(번호 부여 / TaskCreate / learn-log §6 행 추가 / 화면 안내)를 1줄로.

**인자**:
- `<name>` (필수, 한국어 가능, 예: `"vanilla lane 라이브 검증 확장"`)

**동작**:
1. `learn-log.md` §6 마지막 행에서 가장 큰 Growth 번호 N 추출 → `Growth-(N+1)` 부여
2. §6 표 마지막에 1줄 추가: `| Growth-{N+1} | {YYYY-MM-DD} | {name} (in_progress) |`
3. TaskCreate 호출: `subject = "Growth-{N+1}: {name}"`, `status = in_progress`
4. 출력: `Growth-{N+1} started (task #X). learn-log §6 placeholder 추가됨.`

**실패 모드**:
- `<name>` 없음 → 입력 프롬프트
- learn-log.md 없음 / §6 헤더 못 찾음 → 명시적 에러 (silent fallback 금지)
- 이미 동일 Growth 번호 행 존재 → 중복 경고

### 3.2 `/full-test <lane> [domain]`

**목적**: CLAUDE.md "풀테스트 검증 절차" 4계층을 자동 실행 + 자동 라벨링.

**인자**:
- `<lane>` (필수): `jakarta` | `javax` | `vanilla` | `nexacro`
- `[domain]` (선택, 기본 = `out/` 하위 최근 scaffold 디렉토리)

**동작 (계층별)**:

| Layer | 동작 | PASS 기준 | FAIL 시 |
|---|---|---|---|
| **L1 pytest** | sibling 4개 레포(`rdb-skill`, `rdb-ddl`, `rdb-mybatis`, `rdb-nexacro`)에서 `pytest` 병렬 실행 | 모든 레포 exit 0 | 라벨 진행 정지, 보고 후 종료 |
| **L2 JDBC smoke** | HSQLDB 인-메모리: schema apply + seed insert + FK violation 시도 | 의도된 violation 외 0 error | L2 라벨로 종료 |
| **L3 mvn package** | 도메인 scaffold 산출물에서 `mvn -q package` | BUILD SUCCESS | L3 라벨로 종료 |
| **L4 live WAS** | lane 디폴트 runner(아래 표) 위에 overlay → 기동 → endpoint POST → HTTP 200 + ErrorCode=0 + 기대 행수 | 3개 모두 충족 | 부분검증 라벨, **`/cleanup-runner` 자동 호출** |

**lane → runner 매핑** (CLAUDE.md "라이브 WAS 검증대" 표 인용):
| lane | 디폴트 runner |
|---|---|
| jakarta | `boot-jdk17-jakarta` |
| javax | `boot-jdk8-javax` |
| nexacro | (jakarta lane 으로 라우팅) |
| vanilla | `boot-jdk8-javax` (host로 임포트, "vanilla → javax-host 검증" 라벨) |

**라벨 자동 판정**:
- 4계층 모두 PASS → `"풀테스트 그린"`
- L4 부분 (서버는 떴으나 응답 깨짐/행수 불일치) → `"라이브 WAS 부분검증"`
- L4 미실행 / 실패 → `"JDBC + 빌드까지만 검증"`
- L3 미실행 → `"JDBC 까지만 검증"`

**결과 환류**:
- 라벨을 learn-log.md §6 의 활성 Growth 행에 자동 append (`(in_progress)` → 라벨로 치환)
- gap 발견 시(예: 새 Jackson 의존성 문제) §5 에 1줄 추가 제안 (사용자 confirm 후)

**실패 모드**:
- L4 종료 시 cleanup 실패 → 명시적 경고, 사람이 수동 정리하도록 안내
- runner 디렉토리 더티 (이전 cleanup 실패 잔재) → 시작 전 차단, `/cleanup-runner` 실행 권유

### 3.3 `/contribute-back`

**목적**: Growth 종료 시 환류 누락 방지. CLAUDE.md "복리식 축적 체크리스트" 자동화.

**인자**: 없음 (활성 Growth 자동 감지)

**동작**:
1. 5개 레포에서 `git log --since="<활성 Growth 시작일>" --name-only` 수집 (활성 Growth 행의 날짜 기준; 감지 실패 시 최근 7일)
2. 패턴별 분류:
   - `**/presets/*.seed.md`, `**/catalogs/*.yaml` → catalog 환류 (S1)
   - `**/templates/*/*.j2` → 템플릿 (S2/S3/S4)
   - `**/patterns/*/manifest.yaml` → frontend pattern (S4)
   - `**/scripts/dialect*.py` → dialect 어댑터 (S2)
3. 각 변경 카테고리를 learn-log §2~§5 어디에 1줄 환류해야 하는지 후보 위치 제시
4. 인터랙티브 체크리스트 (Y/N/skip):
   - "이 entity 변경, preset-catalog.yaml 반영됨? (Y/N)"
   - "이 dialect 트랩, §4 환류됨? (Y/N)"
   - "이 codegen 결함, §5 task 등록됨? (Y/N)"
5. 미환류 1건이라도 있으면 명시적 경고 + 환류 위치 안내 (exit 0 이지만 stderr 경고 — Growth 행 라벨에 `(환류 미완)` 자동 부착)

**실패 모드**:
- git 에 변경 없음 → "환류 대상 없음" 출력 후 정상 종료
- 활성 Growth 감지 실패 (§6 마지막 행이 라벨로 끝나지 않음) → 경고만, 진행

### 3.4 `/cleanup-runner [lane]`

**목적**: Layer 4 종료 시 mandatory cleanup. CLAUDE.md "필수 cleanup 명령" 자동화.

**인자**:
- `[lane]` (선택, 기본 = 가장 최근 `/full-test` 가 쓴 lane. 추적 못하면 모든 runner 시도)

**동작**:
1. `Stop-Process` java 프로세스 — `jdk-17` path 먼저, 안 잡히면 `jdk-8`, 그래도 안 잡히면 모든 java (사용자 확인)
2. `git -C nexacroN-fullstack restore samples/runners/<runner>/` (lane → runner 매핑 사용)
3. Overlay 파일 제거:
   - `samples/runners/<runner>/src/main/java/com/nexacro/uiadapter/<domain>/` 전체
   - `samples/runners/<runner>/src/main/resources/mybatis/mappers/<entity>-mapper.xml` (untracked)
4. 결과를 표로 출력:
   ```
   Step                          Result
   --------------------------    ------
   Stop java (jdk-17)            OK (PID 363716)
   git restore <runner>          OK
   Remove overlay dir            OK (4 files)
   Remove untracked mappers      OK (4 files)
   ```

**실패 모드**:
- 어떤 단계라도 FAIL → 표에 명시 + 사람이 수동 처리하도록 안내. **자동 재시도 금지** (예상 외 상태 보존).

---

## 4. 부가 변경 (필수)

### 4.1 `settings.local.json` 슬림화

현재 60줄 ad-hoc allowlist 를 다음 정책으로 정리:
- 일회성 명령(`Bash(cp ...)`, `PowerShell(특정 절대경로 ...)` 등) 삭제
- 유지: skill 호출 (`Skill(...)`), MCP tools, 일반 패턴 (`PowerShell(git *)`, `Bash(pytest *)`)
- 예상 결과: 60줄 → 10~15줄

### 4.2 `CLAUDE.md` 작은 갱신

4계층 풀테스트 표 옆에 1줄만 추가:
> 자동 실행: `/full-test <lane> [domain]`. cleanup 자동 포함.

체크리스트 절에도 1줄:
> Growth 시작: `/growth-start <name>`. 종료 환류: `/contribute-back`.

---

## 5. 산출물 위치

신규:
- `business-fullstack-creater/.claude/commands/growth-start.md`
- `business-fullstack-creater/.claude/commands/full-test.md`
- `business-fullstack-creater/.claude/commands/contribute-back.md`
- `business-fullstack-creater/.claude/commands/cleanup-runner.md`
- (필요 시) `scripts/workflow/__init__.py` + 얇은 wrapper 모듈 — 단, 새 로직 금지 (조합만)

갱신:
- `business-fullstack-creater/.claude/settings.local.json` (슬림화)
- `business-fullstack-creater/CLAUDE.md` (2줄 추가)

---

## 6. 검증 (의도가 깨지지 않는지)

### 6.1 5축 자체 리뷰 기준 (CLAUDE.md "사용자 의도 거울")

| 축 | A안 영향 |
|---|---|
| 반복 데이터 효율 관리 | (불변) — A안은 메타-자동화. 데이터 자체에 손대지 않음 |
| 도메인·엔티티 지식 누적 | **개선** — `/contribute-back` 이 환류 누락 차단 |
| 풍부한 Seeds | (불변) |
| 완성도 높은 WAR | **간접 개선** — `/full-test` 가 4계층 누락 차단 → 검증 깊이 일정 |
| Karpathy 정신 | **개선** — LLM이 지식 컴파일러로 더 깊이 활용됨 (수동 절차 → 의도 표현) |

### 6.2 회귀 방어

- sibling 4개 레포 0개 파일 변경
- 기존 `/scaffold` 명령 100% 보존
- 새 명령 실행 실패 시 silent corruption 금지 (모든 명령에 명시적 에러)

### 6.3 비목표 확인

- 새 추상화 도입 ❌ (단순 자동화)
- 외부 의존성 추가 ❌
- 새 데이터 형식 ❌

---

## 7. 단계별 실행 순서 (writing-plans 가 task 화)

| # | 작업 | 산출물 | DoD |
|---|---|---|---|
| 1 | `/cleanup-runner` 명령 (가장 단순) | `cleanup-runner.md` + 동작 검증 | 실제 한 번 실행하여 idempotent 확인 |
| 2 | `/growth-start` 명령 | `growth-start.md` + learn-log §6 갱신 검증 | dummy Growth 1회 생성/취소 |
| 3 | `/full-test` 명령 (가장 복잡) | `full-test.md` + lane×runner 라우팅 | jakarta lane 1회 실제 풀테스트 |
| 4 | `/contribute-back` 명령 | `contribute-back.md` + diff 분류 로직 | 현재 5개 레포 git 상태로 1회 dry-run |
| 5 | `settings.local.json` 슬림화 | 정리된 파일 | 60→10~15줄 |
| 6 | CLAUDE.md 갱신 (2줄) | diff | 풀테스트 표/체크리스트 절에 명령 안내 |
| 7 | 자체 5축 리뷰 + commit | review.md 또는 PR description | 각 축 점수 + 회귀 0건 확인 |

---

## 8. B안으로 가는 트리거 (참고)

A 안을 1~2 Growth 사이클 돌린 뒤 다음 신호가 보이면 B 안으로:
- `/full-test` 가 메인 컨텍스트를 많이 잡아먹음 (subagent 분리 필요)
- learn-log 환류 누락이 여전히 발생 (hook 필요)
- 5개 레포 plugin.json 일관성 요구 (배포 필요)

본 spec 은 A 안에 한정. B안은 별도 spec.

---

## 9. 장기 로드맵 메모 (실행 안 함)

- **B**: `live-was-validator` / `dialect-trap-hunter` / `learn-log-keeper` subagent 3개
- **C**: PostToolUse hook (commit → learn-log 검사), SessionStart hook (활성 Growth 표시), plugin.json 5개 레포 일관 배포 (Claude Code marketplace 호환)
- 진입 조건: A 안에서 명령 사용량 데이터 누적 (3 Growth 이상)
