---
title: andrej-karpathy-rdb-skill Plugin 설계 문서
date: 2026-05-13
status: draft
owner: business-fullstack-creater
related:
  - "[[business-fullstack-creater 플러그인 요구기능]]"
  - "[[1. Plan - andrej-karpathy-rdb-skill 구현]]"
  - "[[2. Backend - DB 스키마(DDL) 생성하기]]"
parent_pipeline: business-fullstack-creater (1단계 Plan)
next_stage: DDL 생성 Plugin (2단계 Backend)
---

# andrej-karpathy-rdb-skill 설계

## 1. 배경 및 위치

### 1.1 전체 파이프라인 내 위치

`business-fullstack-creater`는 "고객관리 업무 개발환경 만들어줘" 한 마디로 NexacroN + Spring Boot + PostgreSQL 3-tier war 파일을 산출하는 메타 플러그인이다. 4단계 파이프라인으로 구성:

| 단계 | 작업 | Plugin |
| :-: | :-- | :-- |
| 1 | **Plan — 업무 프로세스·도메인·엔티티 정의** | **`andrej-karpathy-rdb-skill` (본 문서)** |
| 2 | Backend — DB 스키마(DDL) 생성 | 별도 Plugin (ToDo) |
| 3 | Middle — Spring Boot 어플리케이션 구축 | `/nexacro-fullstack-starter` |
| 4 | Frontend — Nexacro Project 생성 | `/nexacro-claude-skills` |

본 플러그인은 **1단계의 산출물을 2단계 입력으로 결정론적으로 전달**하는 책임을 진다.

### 1.2 영감

Andrej Karpathy의 LLM Wiki 패턴 — markdown + frontmatter, no vector DB, no RAG. 참조 구현은 `Benboerba620/karpathy-claude-wiki`. 본 플러그인은 그 철학을 RDB **비즈니스–도메인–엔티티** 컨텍스트에 이식한다.

### 1.3 재활용 vs 신규 구현 판단

| 그대로 차용 | 신규 정의 |
| :-- | :-- |
| 5계층 변화율 디렉터리 구조 | `entity = DB 테이블` 매핑 규약 |
| `_schema.md` / `_protocols.md` / `_log.md` 메타파일 | `concepts = ER 관계·비즈니스 규칙` 모델링 |
| frontmatter + `[[wikilink]]` 크로스레퍼런스 | **출력 manifest** (`_blueprint.yaml`, 2단계 입력) |
| Phase 1~6 설치 프로토콜 골격 | `domains/` 신규 디렉터리 (비즈니스 도메인 계층) |
| "domain rename" 매핑 패턴 | Marketplace plugin 패키징 |
| Rule lifecycle (`observation → pattern → RULE`) | 비즈니스 도메인 프리셋(고객/주문/인사 등) + 동적 확장 |

## 2. 사용자 결정 사항 (Locked-in)

브레인스토밍 단계에서 사용자가 확정한 핵심 결정:

| # | 결정 항목 | 선택 | 함의 |
| :-: | :-- | :-- | :-- |
| D1 | **산출물 형태** | Markdown wiki + manifest 겸용 | wiki는 사람이 큐레이션, manifest는 2단계 자동 입력 |
| D2 | **UX 형태** | Slash command + Skill | `/karpathy-rdb ...` 명령 + 자동 발동 description |
| D3 | **입력 방식** | 하이브리드 | 자유 프롬프트 + `raw/` 파일 모두 지원 |
| D4 | **도메인 처리** | 프리셋 + 동적 확장 | 고객/주문/재고/인사/재무/패션관리 등 \_seed 템플릿 제공, 그 외는 일반 처리 |
| D5 | **패키징** | Marketplace plugin | 별도 repo `andrej-karpathy-rdb-skill`로 분리, `/plugin install`로 의존성 추가 |
| D6 | **워크플로우** | 3단 분리 | `init` / `ingest` / `compile` 명령으로 중간 검토·수정 지점 확보 |
| D7 | **언어** | 한국어 기본 | 설명/주석/프롬프트 한국어. 식별자(스키마명·테이블명)는 영문 |
| D8 | **manifest 포맷** | YAML | `_blueprint.yaml` — 사람 친화 + 2단계 파서 친화 |
| D9 | **컴파일 모델** | Wiki-first (LLM 컴파일) | wiki(md)가 진실의 근원, manifest는 `/compile`로 생성되는 산출물 — drift 불가 |

## 3. 아키텍처 개요

### 3.1 데이터 흐름

```
[사용자] ─/karpathy-rdb init─▶ [도메인 선택 & 디렉터리 scaffold]
            │
            ▼
        ┌─────────────────────────────────────────┐
        │ wiki/  ← 진실의 근원 (Karpathy 5계층)   │
        │  ├ _schema.md / _protocols.md / _log.md │
        │  ├ raw/        (요구사항 원본)           │
        │  ├ sources/    (요구사항 압축)           │
        │  ├ domains/    (비즈니스 도메인) ⭐신규  │
        │  ├ entities/   (DB 테이블 단위) ⭐재정의 │
        │  ├ concepts/   (ER 관계·비즈니스 규칙)   │
        │  ├ decisions/  (스키마 결정·tradeoff)    │
        │  └ rules.md / false-beliefs.md           │
        └─────────────────────────────────────────┘
            │
   ┌────────┴────────┐
   ▼                 ▼
/karpathy-rdb     /karpathy-rdb
   ingest           compile
(원본/프롬프트       (wiki → _blueprint.yaml
 → wiki 채움)        + 정합성 검증)
                     │
                     ▼
              [_blueprint.yaml] ─▶ 2단계 Plugin (DDL 생성)
```

### 3.2 변화율 5계층 (재정의)

| 계층 | 우리 매핑 | 변화율 |
| :-- | :-- | :-- |
| raw/ | 원본 요구사항 명세, 회의록, 레거시 DDL | 불변 |
| sources/ | LLM이 압축한 요구사항 요약 (1 source = 1 page) | 드물게 |
| **domains/** | 비즈니스 도메인 페이지 (고객관리·주문관리 등) — 소속 entities 링크 | 주/월 |
| **entities/** | DB 테이블 단위 page — frontmatter에 PK/FK/columns 정의 | 주/월 |
| **concepts/** | ER 관계 (1:1, 1:N, N:M), 비즈니스 규칙 | 주/월 |
| explorations/ | 설계 질문에 대한 결론 (e.g., "주소 테이블 분리 여부") | 쿼리당 |
| decisions/ | 스키마 결정 로그 (정규화 vs 역정규화, 인덱스 전략) | 분기 |
| rules.md / false-beliefs.md | 검증된 비즈니스 규칙 / 반증된 통념 | 분기 |

## 4. 컴포넌트 상세

### 4.1 Plugin 패키징 구조 (별도 repo)

```
andrej-karpathy-rdb-skill/                  ← marketplace plugin repo
├── plugin.json                              ← plugin metadata
├── README.md                                ← English 사용자 가이드
├── README.ko.md                             ← 한국어 사용자 가이드 ⭐기본
├── INSTALL-FOR-AI.md                        ← AI agent용 설치 protocol
├── .claude/
│   ├── commands/
│   │   ├── karpathy-rdb-init.md             ← /karpathy-rdb init
│   │   ├── karpathy-rdb-ingest.md           ← /karpathy-rdb ingest
│   │   └── karpathy-rdb-compile.md          ← /karpathy-rdb compile
│   └── skills/
│       └── karpathy-rdb/
│           ├── SKILL.md                     ← skill index + auto-trigger
│           ├── wiki-template/               ← Phase 2에서 복사할 wiki/ 골격
│           │   ├── _schema.md
│           │   ├── _protocols.md
│           │   ├── _log.md
│           │   ├── domains/_template/
│           │   ├── entities/_template/
│           │   ├── concepts/_template/
│           │   └── ... (sources, decisions, explorations, comparisons)
│           ├── presets/                     ← 도메인 프리셋
│           │   ├── 고객관리.seed.md
│           │   ├── 주문관리.seed.md
│           │   ├── 재고관리.seed.md
│           │   ├── 인사관리.seed.md
│           │   ├── 재무관리.seed.md
│           │   └── README.md                ← 새 프리셋 추가 가이드
│           ├── protocols/
│           │   ├── 01-init.md               ← Phase 1~6 install protocol
│           │   ├── 02-ingest.md             ← raw→sources→entities 변환 규칙
│           │   └── 03-compile.md            ← wiki→_blueprint.yaml + 검증 규칙
│           └── references/
│               ├── frontmatter-schema.md    ← entity/concept frontmatter 표준
│               └── blueprint-spec.md        ← _blueprint.yaml 스키마 명세 (2단계 계약)
└── scripts/                                  ← 선택적, 사람용 CLI
    ├── rdb_cli.py                            ← scan/lint/index (선택)
    └── rdb_index.py                          ← _index.json 빌드 + lint (선택)
```

### 4.2 SKILL.md (자동 발동 description)

```yaml
---
name: karpathy-rdb
description: |
  사용자가 비즈니스 업무(고객관리, 주문관리 등)의 DB 스키마/도메인 모델을 설계·
  정의하려 할 때 자동 발동. Karpathy LLM Wiki 패턴을 RDB에 적용하여 markdown 기반
  비즈니스–도메인–엔티티 문서와 _blueprint.yaml manifest를 산출. 2단계 DDL 생성
  플러그인에 입력으로 전달.
argument-hint: "[init|ingest|compile] [도메인명]"
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---
```

### 4.3 명령별 책임 매트릭스

| 명령 | 책임 | 입력 | 산출 | 멱등성 |
| :-- | :-- | :-- | :-- | :-: |
| `init` | wiki 골격 복사, 도메인 프리셋 선택, `_schema.md` 커스터마이즈 | 도메인명, 선택적 preset 키 | `wiki/` 디렉터리 + `_schema.md` 채움 | ❌ (이미 있으면 abort) |
| `ingest` | 자유 프롬프트/raw 파일 → `sources/` 압축 + `domains/`·`entities/`·`concepts/` 페이지 생성·갱신 | 프롬프트 텍스트 OR `wiki/raw/*.{md,pdf,txt}` | wiki 페이지들 + `_log.md` 1줄 추가 | ✅ (재실행 시 갱신) |
| `compile` | 모든 entity/concept frontmatter 스캔 → `_blueprint.yaml` 생성 + 정합성 검증 보고 | wiki 전체 | `_blueprint.yaml` + `compile-report.md` | ✅ (덮어쓰기) |

## 5. 디렉터리·파일 명세

### 5.1 실행 시점 wiki/ 구조 (사용자 프로젝트 내)

```
wiki/
├── _schema.md                          # 헌법 — 본 wiki의 도메인·규칙·용어 정의
├── _protocols.md                       # ingest/compile 프로토콜 전문 (LLM이 매번 읽음)
├── _log.md                             # 모든 ingest/compile 작업 로그 (1줄/이벤트)
├── _blueprint.yaml                     # ⭐ compile 산출물 (2단계 입력)
├── compile-report.md                   # ⭐ compile 검증 보고
├── raw/                                # 원본 요구사항 (불변)
│   └── 2026-05-13-고객관리-요구사항.md
├── sources/                            # 압축 요약 (1 source = 1 page)
│   └── 2026-05-13-고객관리-요구사항.md
├── domains/                            # ⭐신규 — 비즈니스 도메인 계층
│   └── 고객관리/
│       └── profile.md                  # 도메인 개요 + 소속 entities/concepts 링크
├── entities/                           # ⭐재정의 — DB 테이블 단위
│   └── customer/
│       └── profile.md                  # frontmatter에 PK/FK/columns 정의
├── concepts/                           # ⭐재정의 — ER 관계 + 비즈니스 규칙
│   └── customer-has-many-addresses.md
├── explorations/                       # 설계 질문 결론
├── decisions/                          # 스키마 결정 로그
├── comparisons/                        # 대안 비교
├── rules.md                            # 검증된 비즈니스 규칙
└── false-beliefs.md                    # 반증된 통념
```

### 5.2 `entities/<name>/profile.md` frontmatter 표준

```yaml
---
type: entity
name: customer                          # 식별자 (snake_case, 영문)
display: 고객                            # UI 표시명 (한국어)
domain: [고객관리]                       # 소속 도메인 (멀티 가능)
table: customer                          # 물리 테이블명
schema: crm                              # PostgreSQL 스키마 (선택)
status: draft                            # draft | reviewed | locked
columns:
  - { name: id,         type: bigserial,    pk: true,  null: false }
  - { name: name,       type: varchar(100), null: false }
  - { name: email,      type: varchar(255), null: false, unique: true }
  - { name: created_at, type: timestamptz,  null: false, default: now() }
indexes:
  - { name: ix_customer_email, columns: [email], unique: true }
constraints:
  - { name: ck_customer_email_format, check: "email ~ '^[^@]+@[^@]+$'" }
relations:
  - { kind: has_many, to: address, fk: customer_id, concept: "[[customer-has-many-addresses]]" }
sources: ["[[2026-05-13-고객관리-요구사항]]"]
decisions: []
---

# 고객 (customer)

## 의미
업무에서 추적하는 자연인/법인. 회원가입 또는 영업기회로부터 생성.

## 비즈니스 규칙
- 이메일은 유일 (자연 키 후보지만 PK는 surrogate)
- 탈퇴 시 soft delete (`deleted_at` 추가 검토 — [[decisions/소프트삭제-도입검토]])

## 관련
- 도메인: [[domains/고객관리]]
- 관계: [[customer-has-many-addresses]]
```

### 5.3 `concepts/<name>.md` frontmatter 표준

```yaml
---
type: concept
kind: relation                           # relation | rule | invariant | terminology
name: customer-has-many-addresses
cardinality: 1:N                         # 1:1 | 1:N | N:M | self
from: customer
to: address
fk_column: customer_id                   # FK 위치 (N 쪽)
on_delete: restrict                      # restrict | cascade | set_null
status: draft
---

# 고객 ↔ 주소 (1:N)
한 고객은 0개 이상의 주소를 가진다. 주소 단독 존재는 불가 (요구사항 §3.2).
```

### 5.4 `_blueprint.yaml` 스키마 (2단계와의 계약)

```yaml
version: 1
generated_at: 2026-05-13T11:30:00+09:00
project: 고객관리
domains:
  - name: 고객관리
    description: 고객 정보·접점 관리
    entities: [customer, address, contact_log]
entities:
  - name: customer
    table: customer
    schema: crm
    columns: [...]                       # entity profile.md의 columns 그대로
    indexes: [...]
    constraints: [...]
relations:
  - from: customer
    to: address
    cardinality: 1:N
    fk: { column: customer_id, on_delete: restrict }
business_rules:
  - id: BR-001
    text: 이메일은 유일하다
    enforced_by: [unique index ix_customer_email]
sources:
  - id: SRC-001
    file: raw/2026-05-13-고객관리-요구사항.md
validation:
  passed: true
  warnings: []
  errors: []
```

이 manifest가 2단계 DDL 생성 플러그인의 **공식 입력 인터페이스**가 된다.

## 6. 워크플로우 시나리오 + 검증 규칙

### 6.1 사용자 골든 패스 시나리오

```
$ /karpathy-rdb init 고객관리 --preset 고객관리

Phase 1: Clarify
  Q1: wiki 디렉터리 위치? (./wiki/)
  Q2: 추가로 적용할 도메인 프리셋? (생략 가능)
  Q3: 프로젝트 루트에 CLAUDE.md 있나? (없으면 생성)
  Q4: 시작 entity 1개? (customer)
Phase 2~6 자동 진행
✅ wiki/ 생성 완료. 다음: /karpathy-rdb ingest

$ /karpathy-rdb ingest
> (사용자 자유 입력) 고객은 이름·이메일·주소를 가지며, 이메일은 유일하다.
   주소는 여러 개 등록 가능하고 기본 주소 1개를 지정한다.

Plugin 처리:
1. sources/2026-05-13-대화ingest.md 생성 (압축 요약)
2. entities/customer/profile.md 갱신 (이메일 unique 반영)
3. entities/address/profile.md 신규 생성
4. concepts/customer-has-many-addresses.md 생성
5. concepts/address-default-flag.md 생성
6. _log.md 1줄 추가
✅ ingest 완료. 다음: /karpathy-rdb compile

$ /karpathy-rdb compile
1. 모든 entities/*/profile.md 스캔
2. 모든 concepts/*.md 스캔
3. 정합성 검증 (다음 절)
4. _blueprint.yaml 생성
5. compile-report.md 작성
✅ compile 완료. _blueprint.yaml을 2단계 DDL 생성 플러그인에 전달하세요.
```

### 6.2 Compile 검증 규칙

| 코드 | 항목 | 레벨 | 검증 내용 |
| :-: | :-- | :-: | :-- |
| V001 | PK 존재 | ERROR | 모든 entity는 단일/복합 PK 컬럼을 가져야 함 |
| V002 | FK 참조 무결성 | ERROR | `relations.fk_column`이 to-entity의 PK·UQ를 참조해야 함 |
| V003 | 컬럼 명명 규약 | WARN | snake_case, 예약어 회피 (PostgreSQL 키워드 list) |
| V004 | 타입 일관성 | WARN | FK 컬럼의 타입은 참조 PK 타입과 동일해야 함 |
| V005 | 순환 의존 | WARN | entity 간 FK 순환 — 허용하되 경고 (마이그레이션 순서 영향) |
| V006 | 고아 concept | WARN | concept이 참조하는 entity 미존재 |
| V007 | 도메인 미배정 | WARN | entity가 어떤 domain에도 속하지 않음 |
| V008 | 비즈니스 규칙 매핑 | INFO | `rules.md`의 RULE이 어느 entity·concept에 매핑됐는지 보고 |
| V009 | sources 누락 | INFO | entity가 어떤 source에서 유래했는지 미기록 |
| V010 | decisions 추적 | INFO | locked status entity는 `decisions:` 링크 1개 이상 권장 |

`compile-report.md`에는 ERROR/WARN/INFO 카운트 + 각 항목 상세 + 빠른 수정 제안 포함.

### 6.3 도메인 프리셋 (`presets/<도메인>.seed.md`)

각 프리셋은 그 도메인에서 80%의 프로젝트가 공유하는 골격을 제공:

| 프리셋 | 시드 entities | 시드 concepts |
| :-- | :-- | :-- |
| 고객관리 | customer, address, contact_log | customer↔address(1:N) |
| 주문관리 | order, order_item, payment | order↔order_item(1:N), order↔payment(1:1) |
| 재고관리 | product, sku, stock, warehouse | product↔sku(1:N), sku↔stock(1:N) |
| 인사관리 | employee, department, position | employee↔department(N:1), employee↔position(N:1) |
| 재무관리 | account, ledger_entry, fiscal_period | account↔ledger_entry(1:N) |

프리셋은 **수정 가능한 출발점**일 뿐, locked 컨벤션이 아님.

### 6.4 핸드오프 인터페이스 (2단계 계약)

2단계 DDL 생성 플러그인은 `_blueprint.yaml`만 보고 다음을 생성:
- PostgreSQL DDL (`CREATE SCHEMA`, `CREATE TABLE`, FK, INDEX, CHECK)
- 마이그레이션 순서 (FK 의존성 위상정렬)
- 정합성 테스트 SQL (V001~V005 재검증)
- 시드 데이터 스크립트 (선택)

`_blueprint.yaml`의 `version` 필드로 스키마 호환성 관리.

## 7. 사용자 가이드 골격 (README.ko.md)

본 design doc은 최종 사용자 가이드(`README.ko.md`)의 1차 원천이 된다. 사용자 가이드는 다음 흐름으로 구성:

1. **소개** — Karpathy 패턴, 왜 RDB에 적용하는가
2. **빠른 시작** — `/plugin install` → `/karpathy-rdb init` → `ingest` → `compile`
3. **5분 튜토리얼** — 고객관리 도메인 예시 (Section 6.1 골든 패스 기반)
4. **도메인 프리셋 카탈로그** — 표 형식 (Section 6.3)
5. **frontmatter 레퍼런스** — entity/concept 표준 (Section 5.2~5.3)
6. **`_blueprint.yaml` 스키마** — 2단계 핸드오프 계약 (Section 5.4)
7. **검증 코드 사전** — V001~V010 (Section 6.2)
8. **고급** — 새 프리셋 추가, CLI 스크립트, CI 통합

## 8. 미해결 가정 (Open Questions)

- **OQ1**: `_blueprint.yaml`의 `version`을 의미 버전(semver)으로 갈지, 정수 시퀀스로 갈지 → 일단 정수 시퀀스(`version: 1`)로 시작
- **OQ2**: 한 entity가 여러 domain에 속할 때 (예: 사용자 = 고객관리 + 인사관리), `_blueprint.yaml`의 `domains[].entities` 중복 허용? → 허용
- **OQ3**: 외부 LLM helper (원본 `ingest_helper.py` 같은 대용량 PDF 압축)는 v1 범위 외 — v2 검토
- **OQ4**: nexacro form / Spring controller 자동 생성에 필요한 메타데이터(라벨, 검색조건, 화면 권한)는 v2 또는 별도 `_uimanifest.yaml`로 분리 검토
- **OQ5**: `wiki/` 외부에서 entity를 참조하는 워크플로우 (모노레포 멀티 wiki) → v2

## 9. v1 범위 (Scope Lock)

### In Scope
- `init` / `ingest` / `compile` 3개 명령
- 한국어 프롬프트 + 영문 식별자
- 5개 도메인 프리셋 (고객/주문/재고/인사/재무)
- frontmatter 기반 entity/concept 정의
- `_blueprint.yaml` 생성 + V001~V010 검증
- Marketplace plugin 형태 패키징
- README.ko.md / INSTALL-FOR-AI.md 사용자 가이드

### Out of Scope (v2 이후)
- 외부 LLM helper (대용량 PDF 압축)
- UI metadata (`_uimanifest.yaml`)
- 멀티 wiki / 모노레포 지원
- DDL 직접 생성 (2단계 책임)
- 2단계 plugin과의 양방향 sync

## 변경 이력

- 2026-05-13: 초안 작성 — Section 1~9 전체 확정 (브레인스토밍 D1~D9 결정 반영)
