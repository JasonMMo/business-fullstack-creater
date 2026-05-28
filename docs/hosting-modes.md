# Hosting Modes — Self-Host vs SaaS (M4 Decision)

> **결정 일자**: 2026-05-28 (Growth-73)
> **마일스톤**: G1 M4 (Hosting modes 재평가)
> **결정자**: 사용자(프로젝트 오너) + Claude Opus 4.7

## 1. 결정

**M4 결론 — self-host 단일 모드를 v1.0 으로 확정한다. SaaS 는 진입 보류.**

M1(Web Form) · M2(Status Board) · M3(Ops Pack) · M5(Target Project Overlay) 가 모두 닫힌 시점에서 G1 비전문 사용자 3 페르소나(CEO · 업무담당자 · IT담당자) 의 needs 가 **self-host 만으로 충족**되는 것이 확인되었기 때문이다.

SaaS 는 v2.0 단계에서 **누적 자산(profile · catalog · meta) 의 multi-tenant 격리 모델** 이 자연 발생할 때 다시 평가한다.

## 2. 현 시점 self-host 자산 (M3 Ops Pack 기준)

`scripts/emit_ops_pack.py` (Growth-71) 가 scaffold 출력으로부터 emit 하는 4 산출물:

| 파일 | 역할 |
|---|---|
| `Dockerfile` | multi-stage 빌드(`maven:3.9-eclipse-temurin-17 AS builder` → `tomcat:10.1`/`9.0` (war) 또는 `eclipse-temurin:17-jre` (jar)) — IT담당자 로컬에 Maven/JDK 설치 불필요 |
| `docker-compose.yml` | app 컨테이너 + dialect 별 DB(`postgres:16-alpine` / `mysql:8.0` / hsqldb embedded) + healthcheck + volume 영속 |
| `.env.example` | `APP_PORT=8080` + `${SLUG_UPPER}_DB_{HOST,PORT,NAME,USER,PASS}` 블록 — Vault/secret manager 바인딩 자리 |
| `DEPLOY-SOP.md` | 한국어 8-절 runbook (사전준비 → 압축해제 → 환경변수 → 컨테이너기동 → 헬스체크 → SSO → 트러블슈팅 → 백업/Vault) |

**G-71 가드**가 4 산출물 + multi-stage 빌더 패턴을 정적 회귀로 보호한다.

## 3. 3 페르소나 자가검토 — self-host 가 충분한 이유

### CEO 페르소나
**Needs**: 6-axis 누적 자산을 한눈에 본다 (status board).
**Self-host 충족 경로**: M2 Growth-72 `status_board.py` + `docs/index.html` portal. 로컬 브라우저에서 `file://docs/index.html` 열기만으로 동작. SaaS 가 추가하는 가치: 0(외부 노출 의무 없음 — 회사 내부 자산).

### 업무담당자 페르소나
**Needs**: 도메인 1개 정의 → preview → zip 다운로드 (30분 내).
**Self-host 충족 경로**: M1 Growth-69 `web/` FastAPI 레이어. `python -m web` 로 로컬 1-port 노출. SaaS 가 추가하는 가치: 0(scaffold 산출물에 비밀 데이터 없음, 로컬 실행이 더 빠름).

### IT담당자 페르소나
**Needs**: dev 환경 없이 scaffold 산출물 → 운영 배포 (1시간 내).
**Self-host 충족 경로**: M3 Growth-71 Ops Pack. `docker compose up -d` 한 줄로 완결. SaaS 가 추가하는 가치: **마이너스** — 회사 내부 DB · SSO · 망분리 환경에서 외부 SaaS 가 DB 자격증명을 잡을 수 없음.

## 4. SaaS 를 진입 보류한 이유 (현 시점)

1. **6-axis 누적 자산은 회사 고유 자산이다** — `profiles/<customer>.yaml` 의 `${ENV_VAR}` 시크릿, `~/.karpathy-rdb/catalog/<도메인>/` 의 도메인 지식, `learn-log.md` 의 트랩 이력. 외부 SaaS 로 이동 시 다중 고객 격리(multi-tenant)·암호화 키 분리·감사 로그가 즉시 필요 — v1.0 범위 초과.
2. **타깃 사용자 환경은 enterprise on-prem 우세** — 한국 IT 환경 특성상 nexacro 사용 기업은 망분리 + DB on-prem 비중 압도적. SaaS 가 닿을 수 없는 곳.
3. **dev 환경 0 + 1시간 배포** 라는 G1 acceptance 는 SaaS 의 강점인 "설치 자체 회피" 가 아니라 **Ops Pack 의 단순 실행** 으로 이미 충족된다 — SaaS 의 차별화 가치가 작다.
4. **operational cost** — SaaS 운영자(=프로젝트 메인테이너) 가 24/7 가동 의무, SLA, billing, abuse 대응을 짊어진다. v1.0 단독 메인테이너 캐파시티 초과.

## 5. SaaS 진입 재평가 조건 (entry conditions for v2.0)

다음 4 조건이 **모두** 충족될 때 M4 의 SaaS 분기를 재개한다:

1. **누적 자산 격리 모델** — `profiles/` 가 단일 디렉터리에서 namespaced(`profiles/<tenant>/<customer>.yaml`) 로 자연 진화 + `customer.tenant_id` 필드 등재 + multi-tenant 가드(G-7x) 1건 이상.
2. **외부 수요 증거** — self-host 사용자 ≥ 3 조직 + "SaaS 였으면 좋겠다" 요청 ≥ 1건. 추측이 아닌 실제 사용자 발언.
3. **운영 캐파시티** — 24/7 on-call 가능한 2인+ 운영팀 또는 managed cloud(Render/Fly.io/AWS App Runner) 자동화로 단독 운영 가능 증명.
4. **SaaS 차별화 가치** — self-host 대비 SaaS 만 가능한 기능(예: cross-org 도메인 catalog 공유, federated meta-extract) 1건 이상 식별.

위 4 조건 미충족 시 M4 결정은 self-host 단일 유지. **시간 기반 재평가 금지** — "1년 뒤 재논의" 같은 막연한 트리거는 의도 드리프트 위험.

## 6. v1.0 self-host 출시 게이트 (남은 작업)

M4 결정이 self-host 로 굳어졌으므로, v1.0 출시 전 보강할 self-host 표면만 명시한다(이번 M4 범위 밖, 후속 Growth):

- **M3 Slice b**: `scaffold_orchestrator` 가 Stage 5 PASS 직후 `emit_ops_pack.py` 자동 호출 (사용자가 명시 명령 없이도 ops/ 산출물 같이 받음)
- **M3 Slice c**: `web/routes/ops.py` 가 ops pack 을 zip 에 포함시켜 `/domain/<run_id>/download` 응답에 동봉
- **M3 Slice d**: Vault Agent template 후크 (`.env.example` → Vault sidecar 패턴) — IT담당자 자체 키 관리 환경 지원
- **M3 Slice e**: SSO 바인딩(Keycloak/OIDC sidecar) — enterprise on-prem 표준 패턴
- **M5 Slice C-b**: Gradle 입력 지원 (`build.gradle(.kts)` → profile 추출) — extract_target_profile.py 확장

위 5 슬라이스는 self-host 모드 안에서의 깊이 보강 — SaaS 분기로 가지 않는다.

## 7. 결정이 6-axis 누적에 미치는 영향

**없다**. 본 결정은 정책 결정 — `scripts/` · `andrej-karpathy-rdb-*/` · `profiles/` 어디에도 코드 변경 없음.

- skill 축: 무손상
- ddl 축: 무손상
- mybatis 축: 무손상
- nexacro 축: 무손상
- creater 축: 무손상 (M3 Slice b–e 는 후속 Growth)
- customer 축: 무손상

self-host 가 단일 모드라는 것은 **6 축이 동일하게 자라되, runtime 노출 표면이 사용자의 인프라 안에 머문다** 는 의미일 뿐이다.

## 8. 참조

- M3 Ops Pack 구현: `scripts/emit_ops_pack.py` (Growth-71)
- G-71 가드: `scripts/workflow/diagnose.py` `check_cross_layer_coherence`
- G1 페르소나 정의: `AGENTS.md` §"Project Goal G1"
- 누적 자산 가시화: `scripts/workflow/status_board.py` (Growth-72, M2)
- profile 스키마: `profiles/_README.md` (Growth-63 v1)
