# AGENTS.md — business-fullstack-creater

> Repo-level guidance for any AI coding agent (Codex, Gemini, Cursor, etc.).
> Claude Code reads this **and** [CLAUDE.md](./CLAUDE.md); other agents should treat this as the canonical instruction file.

## 프로젝트 성격

이 프로젝트는 **계속 성장하는 프로젝트**다. 일회성 스캐폴드 도구가 아니라, 사용 횟수에 비례해 자산이 누적되어야 한다.

업무 한 줄을 받아 `nexacro + SpringBoot + RDB` 3-tier 산출물을 만드는 harness 이며, 6축에 살을 붙여가며 깊이가 누적된다.

## 핵심 운영 원칙 — 복리식 축적 (6축)

| 축 | 누적 위치 |
|---|---|
| **skill** (Stage 1) | `andrej-karpathy-rdb-skill/.claude/skills/karpathy-rdb/presets/*.seed.md` |
| **ddl** (Stage 2) | `andrej-karpathy-rdb-ddl/catalogs/preset-catalog.yaml` + dialect 어댑터 |
| **mybatis** (Stage 3) | `andrej-karpathy-rdb-mybatis/templates/<lane>/` + lane(jakarta/javax/nexacro/vanilla) |
| **nexacro** (Stage 4+5) | `andrej-karpathy-rdb-nexacro/patterns/` + UI overlay |
| **creater** (Orchestrator) | `.claude/commands/` + `scripts/workflow/` |
| **customer** (6th, Growth-63) | `profiles/<slug>.yaml` — 고객 고유 관습을 한 장으로 묶음 |

**원칙 위반 신호**: "이번만 임시로", "다음에 정리하자", "한 번만 쓸 코드인데" — 이 표현이 떠오르면 catalog/template/preset 등록부터 찾는다.

## Project Goal G1 (CTO 결정, 2026-05-28)

비전문 사용자(CEO·업무담당자·IT담당자) 3 페르소나가 Claude Code/dev 환경 없이 자기 needs 를 충족하는 harness 를 제공한다. 6-axis 복리 누적은 깨지지 않는다.

마일스톤 (M1 → M2 → M3 → M4 순):
- **M1**: User Web Form (도메인 정의 → preview → zip 다운로드 30분 내)
- **M3**: Ops Pack (docker-compose + vault 후크 + 배포 SOP)
- **M2**: Exec Status Board (Growth-55 portal 확장; 누적 자산 시각화)
- **M4**: Hosting modes (self-host 단일 모드 v1.0 확정 — Growth-73, 2026-05-28; SaaS 는 v2.0 진입 조건 4건 모두 충족 시 재평가. 결정 근거 → `docs/hosting-modes.md`)

병행: **M5** target_project overlay (기존 SpringBoot 프로젝트 → profile 자동 추출).

## 작업 시 체크리스트

1. 다룬 도메인 지식이 catalog/preset/seed 에 환류되었는가?
2. 새 구현 패턴이 어댑터/템플릿으로 등록되었는가?
3. `learn-log.md` 에 1줄 기록되었는가?

자동: `/growth-start <name>` 시작, `/contribute-back` 종료.

## 풀테스트 (4계층)

"풀테스트" / "전체 검증" / "E2E 검증" 요청 = **4계층 모두 PASS** 가 그린.

| Layer | 동작 | PASS 기준 |
|---|---|---|
| L1 pytest | 4 sibling repo `pytest -q` | 모든 repo rc=0 |
| L2 JDBC | HSQLDB schema+seed smoke | 의도된 violation 외 0 error |
| L3 mvn | `mvn -q package -DskipTests` | BUILD SUCCESS |
| L4 live | lane 디폴트 runner overlay → REST/Nexacro POST | HTTP 200 + ErrorCode=0 + 기대 행수 |

자동 실행: `/full-test <lane> [domain]`.

## Cross-layer Coherence Guards

`scripts/workflow/diagnose.py` 가 12개 회귀 가드 점검: G-47/48/50a/50b/58/61/62/63/69/70/71/72. 새 cross-layer 결합이 생기면 G-73+ 로 추가.

**G-69 (Growth-69 Web-axis subprocess invariant)**: `web/` 가 `scripts/scaffold_cli.py` 를 subprocess 로 호출하는 형태를 유지해야 한다. web 경로에서 scaffold 로직을 재구현하면 6-axis 누적(skill/ddl/mybatis/nexacro/creater/customer) 이 web 사용자에게만 우회되어 깨진다.

**G-70 (Growth-70 target_project extractor contract)**: `scripts/extract_target_profile.py` 가 v1 customer profile (`version: 1` + `customer.slug` + Growth-70 헤더) 만 emit 해야 한다. 회귀하면 추출된 profile 이 `load_customer_profile` 의 G-62/G-63 pin 을 통과 못해 M5 (target_project overlay) 입력단이 깨지면서 6번째 축 자동 적용이 무력화된다.

**G-71 (Growth-71 Ops Pack emitter contract)**: `scripts/emit_ops_pack.py` 가 4 산출물 (Dockerfile / docker-compose.yml / .env.example / DEPLOY-SOP.md) 을 모두 emit 하고 multi-stage Docker 빌더 (`maven:3.9-eclipse-temurin-17 AS builder`) 패턴을 유지해야 한다. 회귀하면 IT-담당자 페르소나의 "dev 환경 없이 1시간 배포" 시나리오 (M3 Ops Pack 수락 기준) 가 깨진다.

**G-72 (Growth-72 Status Board emitter contract)**: `scripts/workflow/status_board.py` 가 `compute()` + `render_status_section()` + `STATUS_BOARD_CSS` + `extract_trap_guards_count()` 4 계약을 유지해야 한다. 회귀하면 CEO 페르소나의 "축적된 자산 한눈에 보기" (M2 Exec Status Board 수락 기준) 가 깨지고 portal 의 status 섹션이 비어버린다.

## Git Commit Rules

- **파일당 별도 커밋** — `git add -A` / `git add .` 금지.
- 커밋 메시지 끝에 `Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>` (Codex/Gemini 등은 자기 모델명 사용).
- HEREDOC 으로 메시지 작성 (멀티라인 안전).
- `--no-verify` / `--no-gpg-sign` 금지.
- master 푸시는 사용자가 수동.

## 컨벤션

- **G-51**: 모든 파일/디렉터리명은 ASCII slug. 한글 파일명 금지.
- **G-67**: profile YAML 의 `${ENV_VAR}` 는 round-trip 시 보존 (text-patch, not yaml lib).
- 풀테스트 산출물(`docs/scaffolds/`, `out/`) 은 `.gitignore` 대상.

## 참조

- 활동 원장: `learn-log.md` (최근 Growth + §0/§1/§4/§5)
- 옛 Growth: `wiki/learn-log-archive-*.md`
- profile schema: `profiles/_README.md`
- Claude Code 전용 지침: `CLAUDE.md`
