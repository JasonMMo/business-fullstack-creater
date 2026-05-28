# CLAUDE.md — business-fullstack-creater

## 프로젝트 성격

이 프로젝트는 **계속 성장하는 프로젝트**다. 일회성 스캐폴드 도구가 아니라, 사용 횟수에 비례해 자산이 누적되어야 한다.

## 핵심 운영 원칙 — 복리식 축적 (6축)

새 도메인을 다루거나 기존 도메인을 다시 만질 때마다, 다음 6축에서 **살을 붙이며 깊이를 더해간다**:

| 축 | 누적 위치 |
|---|---|
| **skill** (Stage 1) | `andrej-karpathy-rdb-skill/.claude/skills/karpathy-rdb/presets/*.seed.md` + `protocols/` + `wiki-template/` |
| **ddl** (Stage 2) | `andrej-karpathy-rdb-ddl/catalogs/preset-catalog.yaml` + dialect 어댑터 |
| **mybatis** (Stage 3) | `andrej-karpathy-rdb-mybatis/templates/<lane>/` + lane (nexacro/vanilla/jakarta/javax) |
| **nexacro** (Stage 4+5) | `andrej-karpathy-rdb-nexacro/patterns/` + UI overlay |
| **creater** (Orchestrator) | `.claude/commands/` + `scripts/workflow/` |
| **customer** (6th, Growth-63) | `profiles/<slug>.yaml` — 고객 고유 관습(패키지/URL/JDBC/lane/ui)을 한 장으로 묶어 `/scaffold --customer-profile <name>` 으로 Stage 1–5 전체에 일관 적용 |

> 활동 뷰(현재 트랩 카운트·미해결 환류·검증 상태)는 `learn-log.md` §0/§1 참조.

**원칙 위반 신호**: "이번만 임시로", "다음에 정리하자", "한 번만 쓸 코드인데" — 이 표현이 떠오르면 **반드시 멈추고 catalog/template/preset 등록부터 찾는다**.

## 작업 시 체크리스트

1. 다룬 도메인 지식이 catalog/preset/seed에 환류되었는가?
2. 새로 발견한 구현 패턴이 어댑터/템플릿으로 등록되었는가?
3. `learn-log.md` 에 1줄 기록되었는가?

> 자동 실행: Growth 시작 `/growth-start <name>`. Growth 종료 환류 `/contribute-back`.

## 풀테스트 (4계층)

"풀테스트", "전체 검증", "E2E 검증" 요청 = **4계층 모두 PASS** 가 그린. 절차·라벨링·러너 매트릭스·cleanup 명령은 skill 로 분리:

- 4계층 절차 + 라벨링 — `.claude/skills/full-test-protocol/SKILL.md`
- lane × runner 매트릭스 + 컨텍스트 경로 컨벤션 — `.claude/skills/runner-matrix/SKILL.md`
- L4 종료 cleanup 명령 — `.claude/skills/runner-cleanup/SKILL.md`

> 자동 실행: `/full-test <lane> [domain]`. cleanup 자동 포함.

## 왜 이 원칙이 중요한가

사용자 의도 verbatim:
> "andrej-karpathy의 지식 관리 방식을 적용 ... 사용자가 요청하는 업무(도메인), 요소(entity)를 지식으로 쌓아서 결국 풍부한 Seeds 를 만들어 완성도 높은 결과물(war)를 제공"

복리식 축적이 깨지면 이 프로젝트는 그저 또 하나의 코드 제너레이터가 된다.

## 참조

- 활동 원장: `learn-log.md` (최근 10 Growth + §0/§1/§4/§5 현재 상태)
- 옛 Growth: `wiki/learn-log-archive-*.md`
- 정렬 리뷰: `docs/superpowers/specs/2026-05-15-karpathy-alignment-review.md`
