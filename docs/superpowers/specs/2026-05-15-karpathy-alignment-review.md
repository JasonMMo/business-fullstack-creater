# Karpathy 정렬 리뷰 — business-fullstack-creater 4단계 파이프라인

**작성일**: 2026-05-15
**대상 플러그인**: andrej-karpathy-rdb-skill (v0.1.1), andrej-karpathy-rdb-ddl (v0.1.2), andrej-karpathy-rdb-mybatis (v0.1.4)
**목적**: 사용자 의도와 현재 구현의 정렬 상태 평가, 갭 식별, 단/중/장기 전략 결정

---

## 1. 사용자 의도 (verbatim)

> "내가 궁극적으로 원한 것은 반복되는 데이터를 효율적으로 관리하고 싶어서 andrej-karpathy의 지식 관리 방식을 적용하고 싶었다. 업무(도메인)도 결국 특정한 목적의 데이터의 묶음이니까 andrej-karpathy의 지식 관리 방식을 적용하면 효율적이겠다는 생각이 들었다. 사용자가 요청하는 업무(도메인), 요소(entity)를 지식으로 쌓아서 결국 풍부한 Seeds를 만들어서 완성도 높은 결과물(war)를 제공하고 싶었다."

**5개 평가 키워드**:
1. **반복 데이터 효율 관리** — 같은 정보를 두 번 정의하지 않는가?
2. **도메인·엔티티 지식 누적** — 한 번 만든 entity가 다음 프로젝트에서 살아 있는가?
3. **풍부한 Seeds** — 새 프로젝트 시작 시 출발점이 진짜로 더 풍부해졌는가?
4. **완성도 높은 WAR** — 최종 산출물 품질 향상에 직접 기여하는가?
5. **Karpathy 정신** — LLM이 지식 컴파일러, 파일 기반, 복리식 축적 유지하는가?

---

## 2. Karpathy 원본 3계층 아키텍처 요약

출처: `needs/Plugin참조/1. Plan - andrej-karpathy-rdb-skill 구현.md`

| 계층 | 역할 |
|---|---|
| **Raw Sources** | 불변 원본 — 사용자 메모, 회의록, 문서 등 |
| **The Wiki** | LLM이 생성·관리하는 markdown — frontmatter + `[[wikilink]]` 크로스레퍼런스 |
| **Schema (CLAUDE.md)** | wiki 작성 규칙, 노드 타입, 갱신 정책 |

**핵심 철학**:
- **LLM = 지식 컴파일러**: 사람이 직접 문서를 쓰는 것이 아니라 LLM이 raw → wiki로 컴파일·갱신
- **복리식 축적 (compounding)**: 질의응답으로 얻은 인사이트를 다시 wiki에 반영 → 검색이 아닌 '추론' 가능한 지식 베이스
- **파일 기반**: 벡터 DB 없이 local markdown만 사용
- 출처: `docs/superpowers/specs/2026-05-13-andrej-karpathy-rdb-skill-design.md` 섹션 1.2

---

## 3. 3개 플러그인 진단표

| 플러그인 | 입력 | 출력 | 누적 메커니즘 | 단방향? | 사용자 확장 |
|---|---|---|---|---|---|
| **rdb-skill** (Stage 1) | Raw 요구사항 (`/ingest` 프롬프트 또는 파일) + 5개 정적 preset | `wiki/` (domains/entities/concepts/rules/false-beliefs) + `_blueprint.yaml` | 단일 프로젝트 wiki: ✅ / preset 갱신 회수 루프: ❌ | 부분 단방향 (preset → wiki만) | preset 파일 수동 편집 가능 |
| **rdb-ddl** (Stage 2) | `wiki/_blueprint.yaml` | `db/migrations/V###__*.sql`, `seed/*.sql`, JPA Entity, `ddl-report.md` | 없음 | ✅ 완전 단방향 | `scripts/preset_catalog.py` Python 코드 직접 수정 |
| **rdb-mybatis** (Stage 3) | `_blueprint.yaml` + DDL + (옵션)seed | `backend/` (controller/service/mapper/domain Java + MyBatis XML + `endpoints.json`) | 없음 | ✅ 완전 단방향 | 없음 (계약 소비만) |

**일관성**: blueprint.yaml 계약(`version: 1`)이 Stage 1→2→3 사이 안정적이며, `endpoints.json v0.1.4+`는 Stage 4 핸드오프 계약으로 버저닝됨.

---

## 4. 갭 정리

### 갭 1 — 프로젝트에서 배운 entity/rule이 preset으로 역류하지 않음

- **현황**: `protocols/02-ingest.md`는 `_log.md`에 작업 이력 1줄만 기록. 새로 발견된 entity/rule은 wiki에 들어가지만 `presets/<도메인>.seed.md`에는 반영 경로 없음
- **결과**: 5개 preset(고객/주문/재고/인사/재무관리)은 플러그인 레포에 고정. 사용자가 10번째 프로젝트에서도 첫 프로젝트와 동일한 출발점에서 시작
- **Karpathy 정신과의 충돌**: "복리식 축적" 핵심이 단일 프로젝트 안에만 갇혀 있음
- **현재 명시적 보류**: `2026-05-13-andrej-karpathy-rdb-skill-design.md` 섹션 9에 "프리셋 마켓플레이스/커뮤니티 공유"가 v2 이후로 유보

### 갭 2 — preset_catalog.py 하드코딩, 사용자 확장 불가

- **현황**: `D:\AI\workspace\andrej-karpathy-rdb-ddl\scripts\preset_catalog.py`의 `PRESETS` 7줄 딕셔너리. 사용자가 새 도메인 추가 시 Python 코드 편집 필요
- **결과**: 도메인 카탈로그가 코드와 결합되어 비개발자/시간 부족 사용자가 손대기 어려움
- **영향 범위**: Stage 2의 seed 데이터 생성 시 도메인↔엔티티 매핑에 사용

### 갭 3 — 동일 entity 정보 중복 생성

- **현황**: Stage 2가 JPA Entity (`templates/entity.java.j2`) 생성, Stage 3이 NexacroBase 상속 POJO (`templates/domain/entity.java.j2`) 생성
- **결과**: 같은 도메인 정보에서 두 종류의 Java 파일이 만들어지고, 어느 쪽도 다음 프로젝트에서 재사용되지 않음
- **참고**: 이번 정렬 작업에서는 재사용 메커니즘(catalog)을 먼저 만들고, 중복 자체 해결은 v0.3 이후로

---

## 5. 잘 된 점 (보존할 것)

- **blueprint.yaml 계약의 안정성**: Stage 1→2→3 모든 핸드오프가 단일 YAML 스키마 기반, `version: 1` 안정
- **Stage 2/3 일관성**: `references/blueprint-input-contract.md`(Stage 3)와 `references/ddl-spec.md`(Stage 2)가 동일 필드 집합 참조
- **endpoints.json 계약 버저닝**: Stage 3→4 핸드오프가 `v0.1.4+`로 명시화 (`output-layout.md:17`)
- **wiki 노드 영속성**: 프로젝트 디렉터리 내 markdown으로 영구 저장 (벡터 DB 의존 없음 — Karpathy 원칙 충실)
- **Subagent-Driven Development 규율**: 각 단계가 spec → plan → 구현 → 검증 → 릴리스 태그 사이클을 완주

---

## 6. 결정 사항

| 항목 | 결정 | 근거 |
|---|---|---|
| **단기 (A — Quick Win)** | ✅ 즉시 진행 | learn-log.md + preset YAML 외부화. v0.1.x 호환, 사용자 즉시 체감 |
| **중기 (B — v0.2.x)** | ✅ 진행 | 글로벌 카탈로그 + `/contribute` + blueprint `extends`. 진짜 양방향 누적 실현 |
| **장기 (C — 보류)** | 🔶 ToDo 기록 | 메타 추출/유사 도메인 추천/마켓플레이스. 실 프로젝트 3개 누적 후 재평가 |
| **갭 3 (Stage 2/3 entity 중복)** | 🔶 v0.3+ 보류 | 카탈로그 인프라 먼저, 중복 통합은 그 다음 |

**작업 위치**: Stage 1(rdb-skill) + Stage 2(rdb-ddl) 두 레포 동시.
**실행 모드**: Auto + Milestone Gate 자체 리뷰 (5축 점수표).

---

## 7. 장기 로드맵 (C차원, 실 프로젝트 3개 이상 누적 후 재평가)

### 7.1 메타 지식 추출
- 위치: `andrej-karpathy-rdb-skill/scripts/meta_extract.py` (신규)
- 입력: 복수 프로젝트의 `wiki/learn-log.md`
- 출력: `~/.karpathy-rdb/catalog/meta/<도메인>_meta.md` — 공통 패턴, 반복 등장 entity, false-belief 경향
- LLM이 새 프로젝트 init 시 이 메타 파일을 컨텍스트로 활용 ("이 도메인에서 자주 누락되는 entity: ...")

### 7.2 유사 도메인 추천
- 위치: `protocols/01-init.md` Phase 1 Q2 강화
- 메커니즘: 사용자 입력 도메인명과 카탈로그 frontmatter를 LLM 컨텍스트에 올려 키워드 매칭으로 가장 가까운 seed 3개 자동 제안
- 벡터 DB 사용 금지 (Karpathy 원칙 유지)

### 7.3 팀 공유 / 마켓플레이스
- `catalogs/preset-catalog.yaml`을 별도 git 리포로 분리
- `plugin.json`에 `catalog_remote: <URL>` 필드 추가로 원격 카탈로그 지정
- PR 기반 카탈로그 기여 워크플로우

**진입 조건**: 실 프로젝트 3개 이상에서 `learn-log.md` 누적 데이터가 의미 있는 패턴을 보일 때.

---

## 8. 위험 요약

| 위험 | 완화책 |
|---|---|
| 하위 호환성 | `version: 1` 유지, `extends`는 선택적 필드, 카탈로그 미발견 시 명시적 에러 |
| preset 품질 저하 | `/contribute`에서 "범용성 확인" 질문 강제, 자동 머지 금지 |
| Over-engineering | Phase 1만으로 사용자 의도 80% 달성 가능 — Phase 2 진행 전 실 사용 피드백 권장 |
| 멀티프로젝트 컨텍스트 한계 | 메타 추출은 명시적 명령으로만, LLM이 모든 wiki 동시 보지 않음 |
| 카탈로그 충돌 | 로컬 `catalogs/` > 글로벌 `~/.karpathy-rdb/catalog/` 우선순위 명시 |

---

## 9. 참조

- 사용자 의도 원문: `D:\AI\workspace\business-fullstack-creater\needs\business-fullstack-creater 플러그인 요구기능.md`
- Stage 1 설계: `docs/superpowers/specs/2026-05-13-andrej-karpathy-rdb-skill-design.md`
- Stage 2 설계: `docs/superpowers/specs/2026-05-13-andrej-karpathy-rdb-ddl-design.md`
- Stage 3 설계: `docs/superpowers/specs/2026-05-13-stage3-mybatis-uiadapter-codegen-design.md`
- 실행 플랜: `C:\Users\mo\.claude\plans\delightful-swimming-hanrahan.md`
