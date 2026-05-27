# business-fullstack-creater

> 업무 한 줄(`고객관리 업무 개발환경 만들어줘`)을 입력하면 nexacroN + Spring Boot + RDB 3-tier 프로젝트를 산출하는 **5-stage 코드 생성 오케스트레이터**.

| | |
|---|---|
| **상태** | 4 lane (vanilla / javax / jakarta / nexacro) × 14 도메인 풀테스트 그린 |
| **누적** | 도메인 14 · 프런트 패턴 11 · backend lane 4 · dialect 3 · UI overlay 2 |
| **트랩 가드** | `/diagnose` 가 6개 cross-layer 회귀 가드 정적 검사 (G-47/48/50a/50b/58/61) |
| **테스트** | 440 그린 (workflow 281 + non-workflow 159) |

상세 가이드는 [`docs/USER-GUIDE.md`](docs/USER-GUIDE.md) (95K) — 본 문서는 진입용 개략입니다.

---

## 1. 무엇을 만드는가

5-stage 파이프라인이 sibling repo 4개를 차례로 호출합니다:

```
Stage 1  rdb-skill     자연어 → _blueprint.yaml
Stage 2  rdb-ddl       blueprint → DDL/seed (postgres/hsqldb/mysql)
Stage 3  rdb-mybatis   DB → Java 백엔드 + endpoints.json (4 lane)
Stage 4  rdb-nexacro   endpoints → XFDL form/dataset (nexacro lane 전용)
Stage 5  overlay       runner 골격 위에 Stage 2-4 산출물 덮어쓰기 → war
```

산출물:
- `out/<도메인>/` — schema.sql · mapper.xml · Controller.java · Service.java · XFDL form
- `scaffold-report.md` — stage별 PASS/SKIP/FAIL 라벨
- `~/.karpathy-rdb/catalog/<도메인>/` — 글로벌 카탈로그 누적 (복리식)

## 2. 핵심 원칙 — 5축 복리식 축적

사용 횟수에 비례해 자산이 누적되는 **성장형 프로젝트**입니다. 새 도메인을 다루거나 기존 도메인을 다시 만질 때마다 5축에 살을 붙입니다:

| 축 | 누적 위치 |
|---|---|
| **skill** (Stage 1) | `andrej-karpathy-rdb-skill/.claude/skills/karpathy-rdb/presets/*.seed.md` |
| **ddl** (Stage 2) | `andrej-karpathy-rdb-ddl/catalogs/preset-catalog.yaml` |
| **mybatis** (Stage 3) | `andrej-karpathy-rdb-mybatis/templates/<lane>/` |
| **nexacro** (Stage 4+5) | `andrej-karpathy-rdb-nexacro/patterns/` |
| **creater** (Orchestrator) | `business-fullstack-creater/.claude/commands/` + `scripts/workflow/` |

`learn-log.md` §0 Layer Ownership Card 가 현재 누적 상태 — 트랩 카운트, 미해결 환류, 검증 마일스톤이 표 한 장에 모입니다.

원칙 위반 신호: *"이번만 임시로"* / *"다음에 정리하자"* — 떠오르면 멈추고 catalog / template / preset 에 환류부터 합니다. 자세한 운영 원칙은 [`CLAUDE.md`](CLAUDE.md).

## 3. Quick Start

```powershell
# 0. 환경 점검 (sibling repo + INDEX.md + runner + JDK + 6 cross-layer guards)
python -m scripts.workflow.diagnose

# 1. 도메인 후보 표시 (14개)
python -m scripts.workflow.list_domains

# 2. 도메인 생성 — 한글 도메인 + ASCII slug/package 분리 필수 (Growth-51 트랩)
python scripts/scaffold_cli.py `
  --domain 고객관리 --slug customer --package com.example.customer `
  --lane jakarta --dialect hsqldb `
  --out ./out/customer --wiki-mode preset --preset 고객관리

# 3. 4계층 풀테스트 (L1 pytest + L2 JDBC + L3 Maven + L4 live WAS HTTP 200)
python -m scripts.workflow.full_test jakarta out/customer

# 4. 정적 포털 재생성 (14 도메인 tile + L1 preview + L2 zip + L3 snippet)
python -m scripts.workflow.web_index
```

Claude Code 안에서는 동일 흐름이 슬래시 커맨드로 노출:
```
/orient → /diagnose → /list-domains → /scaffold <도메인> → /full-test <lane> <도메인>
```

## 4. lane × dialect × overlay 매트릭스

| lane | runner | 검증 상태 | UI overlay 기본값 |
|---|---|---|---|
| **nexacro** | `boot-jdk17-jakarta` | ✅ Growth-42 (envelope CRUD) | nexacro |
| **jakarta** | `boot-jdk17-jakarta` | ✅ Growth-28 / Growth-31 | nexacro |
| **javax** | `boot-jdk8-javax` | ✅ Growth-49 (3-fix 누적) | nexacro |
| **vanilla** | (runner 없음 — javax-host) | ✅ Growth-50 (첫 REST 종단검증) | react (Growth-59 lane-aware default) |

`--ui` 미지정 시 lane 의도대로 자동 선택. dialect 는 `--dialect {postgres,hsqldb,mysql}`.

## 5. 자산 노출형 하네스 — 4-point 체인

새 사용자가 클론 직후 "여기서 무엇부터 만지면 되는지" 한 화면에 파악하도록 4 지점에서 누적 자산을 노출:

| 지점 | 명령 | 노출하는 자산 |
|---|---|---|
| **진입** | `/orient` | USER-GUIDE 한 줄 정의 + Layer Ownership Card + 최근 Growth |
| **사전** | `/diagnose` | 5축 sibling repo + INDEX.md + runner + JDK + 6 회귀 가드 |
| **실행** | `/full-test` | 4계층 PASS/FAIL + lane × runner 매트릭스 |
| **사후** | `recovery_hint` | 실패 layer 별 다음 명령 1줄 |

추가로 `/web-build` (Growth-55) 가 `docs/index.html` 정적 포털을 생성 — 외부 사용자가 클론 없이 14 도메인 자산(DDL/Mapper/Controller/Service preview + L2 zip + L3 copy-paste snippet)을 브라우저에서 둘러봅니다.

## 6. 풀테스트 4계층

`/full-test <lane> <scaffold>` 호출 시:

| 계층 | 검증 | 라벨 |
|---|---|---|
| **L1** | sibling repo 4개 pytest rc=0 | unit-green |
| **L2** | HSQLDB schema + seed JDBC 실행 OK | jdbc-green |
| **L3** | `mvn package` rc=0 | build-green |
| **L4** | 라이브 WAS HTTP 200 + ErrorCode=0 + rows≥1 (+ envelope/REST CRUD round-trip) | live-green |

L1-L4 모두 PASS = **풀테스트 그린**. cleanup 자동 포함 (Growth-54 의 `cleanup_runner` 픽스 후).

## 7. 디렉터리

```
.claude/commands/        9 slash command
scripts/workflow/        full_test · live_* · lane_runner_map · web_index · diagnose · orient · ...
scripts/scaffold_cli.py  CLI 진입점
scripts/scaffold_orchestrator.py  Stage 1→5 오케스트레이션
docs/USER-GUIDE.md       통합 가이드 (95K)
docs/index.html          정적 portal 진입
learn-log.md             활동 원장 (§0 누적 상태, §4 트랩, §6 Growth 이력)
tests/                   workflow 281 + 기타 159 = 440 그린
```

## 8. 참고

- **운영 원칙**: [`CLAUDE.md`](CLAUDE.md) — 변하지 않는 5축 복리식 축적 원칙
- **활동 원장**: [`learn-log.md`](learn-log.md) — Growth 누적 / 트랩 / 회귀 가드
- **통합 가이드**: [`docs/USER-GUIDE.md`](docs/USER-GUIDE.md) — Quick Start + Stage reference + 트러블슈팅
- **정적 portal**: `docs/index.html` (브라우저로 열기)
- **옛 Growth**: `wiki/learn-log-archive-*.md`
