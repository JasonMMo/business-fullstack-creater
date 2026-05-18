# business-fullstack-creater 사용자 가이드

> 업무별 fullstack 코드 생성 파이프라인. "고객관리 업무 개발환경 만들어줘." 한 마디로
> nexacroN + Spring Boot 3.5 + PostgreSQL 기반 3-tier 프로젝트를 war 형태로 만들어내는
> 4-stage 코드 생성 도구 모음입니다.

본 문서는 **Quick Start walkthrough** + **Stage별 reference** + **트러블슈팅**을
한 곳에 모은 통합 가이드입니다.

- 설계: [`docs/superpowers/specs/`](./superpowers/specs/)
- 플랜:  [`docs/superpowers/plans/`](./superpowers/plans/)
- 요구기능 원문: [`needs/business-fullstack-creater 플러그인 요구기능.md`](../needs/business-fullstack-creater%20%ED%94%8C%EB%9F%AC%EA%B7%B8%EC%9D%B8%20%EC%9A%94%EA%B5%AC%EA%B8%B0%EB%8A%A5.md)
- Stage 3↔4 핸드오프 계약: [`needs/Plugin참조/3. Middle+Frontend - Stage 3→4 nexacro 핸드오프 계약.md`](../needs/Plugin%EC%B0%B8%EC%A1%B0/3.%20Middle%2BFrontend%20-%20Stage%203%E2%86%924%20nexacro%20%ED%95%B8%EB%93%9C%EC%98%A4%ED%94%84%20%EA%B3%84%EC%95%BD.md)

---

## 1. 개요 (5분)

### 1.1 무엇을 만드는가 — 4-stage 파이프라인 한눈에

```
┌───────────────────┐    ┌────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│ Stage 1           │    │ Stage 2        │    │ Stage 3          │    │ Stage 4          │
│ rdb-skill         │ →  │ rdb-ddl        │ →  │ rdb-mybatis      │ →  │ rdb-nexacro      │
│ (Plan)            │    │ (Backend DB)   │    │ (Middle Java)    │    │ (Frontend xfdl)  │
└───────────────────┘    └────────────────┘    └──────────────────┘    └──────────────────┘
   wiki / 자연어            _blueprint.yaml         _blueprint.yaml         _blueprint.yaml
        ↓                         ↓               + db/migrations/             + endpoints.json
   _blueprint.yaml          db/migrations/         ↓                            ↓
                            entities/              backend/ (Java)              out/nxui/_form_/
                                                   endpoints.json               out/nxui/_datasets_/
                                                                                out/patches/
                                                                                ↓
                                                   ┌────────────────────────────┴─────┐
                                                   │ Stage 4'                          │
                                                   │ /nexacro-fullstack-starter        │
                                                   │ (외부 plugin, scaffold)            │
                                                   └────────────────────────────┬─────┘
                                                                                 ↓
                                                                         war (deployable)
```

| 순서 |        구분        |         산출물         |                   Plugin                    | 버전     |
| :-: | :--------------: | :-----------------: | :-----------------------------------------: | :----- |
|  1  |  Plan / 자연어 → DB | `_blueprint.yaml`   | `andrej-karpathy-rdb-skill`                 | v0.2.0 |
|  2  |  Blueprint → DDL | `db/migrations/`    | `andrej-karpathy-rdb-ddl`                   | v0.2.0 |
|  3  |  DB → Java 백엔드   | `backend/`, `endpoints.json` | `andrej-karpathy-rdb-mybatis`     | v0.1.4 |
|  4  |  Endpoints → 화면  | `out/nxui/...`      | `andrej-karpathy-rdb-nexacro`               | v0.1.0 |
|  4' | Spring + nx 골격   | scaffold            | `/nexacro-fullstack-starter` (외부)           | v0.8.2 |

> **v0.2.0 (2026-05-15) 변경점**: Karpathy 복리식 축적 메커니즘 도입.
> - Stage 1: `wiki/learn-log.md` 신규 + `/karpathy-rdb contribute <도메인>` 명령으로 프로젝트 지식을 글로벌 카탈로그(`~/.karpathy-rdb/catalog/`)로 역류
> - Stage 1: blueprint entity `extends:` 문법으로 글로벌 base entity 재사용
> - Stage 2: `catalogs/preset-catalog.yaml` 외부화 + 글로벌 카탈로그 자동 병합 (`PRESETS` 자동 확장)
> - 하위 호환 유지 (`version: 1` blueprint, 기존 호출부 무변경). 상세: [`docs/superpowers/specs/2026-05-15-karpathy-alignment-review.md`](./superpowers/specs/2026-05-15-karpathy-alignment-review.md)

> **v0.4 Phase E (2026-05-18) 변경점**: scaffold orchestrator 사용성 강화.
> - `scaffold_cli.py --dialect hsqldb` 추가 — Stage 2 까지 HSQLDB 방언으로 전파 (Spring Boot 임베디드 DB 즉시 부팅 가능)
> - Stage 2 가 생성한 seed SQL 을 Stage 3 의 `src/main/resources/data.sql` 로 **자동 wiring** (별도 cp 불필요)
> - `scaffold_cli.py --service-name <PascalCase>` 추가 — 도메인 1개 = nexacro Service 1개 모델 (이전: entity 마다 `SvcOrderItem`/`SvcPayment` 분리되어 typedefinition 후처리 필요). 미지정 시 `domain_slug` 에서 자동 PascalCase 도출
> - xfdl 폼이 단일 Service id 를 참조하도록 통일 (`SvcOrder::method`)
> - 하위 호환 유지 — 신규 플래그 모두 default 값. 상세: [`docs/superpowers/specs/2026-05-18-v0.4-phase-e-me-gate.md`](./superpowers/specs/2026-05-18-v0.4-phase-e-me-gate.md)

> **v0.4 Phase F (2026-05-18) 변경점**: Stage 5 target overlay 자동화.
> - `scaffold_cli.py --target-project <dir>` 추가 — 4 stage 생성 직후 `/nexacro-fullstack-starter` 산출 base scaffold 위로 자동 overlay (Java + resources/mybatis + xfdl + frameLogin dsSample row + typedefinition `<Services>` entry)
> - Java package 자동 rename: `com.example.<slug>` → `com.nexacro.uiadapter.<slug>` (`package`/`import`, MyBatis xml `namespace`/`type`/`resultType`/`parameterType`)
> - `frameLogin.xfdl` dsSample 컬럼 schema mismatch 시 menu 단계만 skip + 사용자에게 실 ColumnInfo / 필요 컬럼 목록 안내 (다른 단계는 계속)
> - 모든 수정 파일은 1회 `.bak` 백업 (idempotent — 재실행 시 row/Service 중복 추가 0)
> - 충돌 시 `--overlay-force` 없으면 RuntimeError + 어느 파일과 충돌하는지 listing (변경 시작 전에 fail-fast)
> - `--target-project` 미지정 시 Stage 5 skip (Phase D/E 하위 호환 100%). 상세: [`docs/superpowers/specs/2026-05-18-v0.4-phase-f-mf-gate.md`](./superpowers/specs/2026-05-18-v0.4-phase-f-mf-gate.md)

> **v0.4.2 보완 (2026-05-18)**: 패키지 prefix 외부화 + Korean 도메인 slug 안전망.
> - `--target-package-prefix <java.pkg>` 추가 (기본 `com.nexacro.uiadapter`). target 프로젝트가 다른 base package 를 쓰면 한 줄로 매핑.
> - source prefix 는 `--package` 에서 마지막 segment 를 제외한 전체로 자동 도출 (예: `--package com.foo.bar.shop` → source `com.foo.bar`, slug `shop`).
> - **slug 정확도 수정**: 이전엔 `derive_slug("주문관리")` → `"domain"` fallback 이 Stage 5 경로/`prefixid` 로 새어 들어가던 버그 → Stage 5 가 항상 `--package` 마지막 segment 를 overlay slug 로 사용.
> - Korean fallback 발동 시 stderr 경고 출력 (`WARN: derive_slug('주문관리') → 'domain' (non-ASCII fallback). Stage 5 overlay will use --package last segment ('order') as the actual domain slug.`).
> - 하위 호환 100% — 모든 신규 플래그 default 유지 시 v0.4.1 동작 동일.

### 1.2 사전 준비

**런타임:**
- Python 3.11+
- JDK 17 (Spring Boot 3.5 + jakarta lane)
- Maven 3.9+
- PostgreSQL 14+ *(또는 HSQLDB embedded — Stage 3 기본)*

**개발 도구:**
- Claude Code (slash command 실행용)
- nexacro N v24 라이선스 *(런타임에서 NexacroResult 직렬화 시 필요)*
- nexacro Studio *(xfdl 화면 미리보기 / project build 시)*

**선택 plugin:**
```
/plugin marketplace add JasonMMo/nexacro-claude-skills
/plugin install nexacro-fullstack-starter@nexacro-claude-skills
/plugin install nexacro-claude-skills@nexacro-claude-skills
```

**plugin 4종 설치 확인:**
```powershell
Test-Path D:\AI\workspace\andrej-karpathy-rdb-skill
Test-Path D:\AI\workspace\andrej-karpathy-rdb-ddl
Test-Path D:\AI\workspace\andrej-karpathy-rdb-mybatis
Test-Path D:\AI\workspace\andrej-karpathy-rdb-nexacro
```

---

## 2. Quick Start — 고객관리 시스템 만들기 (15분)

다음 walkthrough는 "고객관리 업무 개발환경 만들어줘." 시나리오를 4-stage 파이프라인으로
처음부터 끝까지 통과시켜 war 산출물 직전까지 가는 과정입니다. 기준 디렉터리는
`D:\AI\workspace\customer-mgmt`로 가정합니다.

### 2.1 작업 디렉터리 생성

```powershell
New-Item -ItemType Directory -Force D:\AI\workspace\customer-mgmt | Out-Null
cd D:\AI\workspace\customer-mgmt
```

### 2.2 Stage 1 — Blueprint 생성 (rdb-skill)

자연어 요구사항을 입력하면 도메인/엔티티/관계가 추출되어 `_blueprint.yaml`로 저장됩니다.

```
/karpathy-rdb init customer-management --preset 고객관리
/karpathy-rdb ingest 고객은 이메일이 unique 하고 여러 주소를 등록할 수 있다. 고객 등급은 일반/우수/VIP 셋 중 하나.
/karpathy-rdb compile
```

산출물:
```
wiki/
├── domains/
├── entities/
│   ├── customer.md
│   ├── customer_address.md
│   └── customer_grade.md
└── _blueprint.yaml          ← 다음 단계의 입력
```

**Blueprint 검증:** `_blueprint.yaml`의 모든 컬럼이 `nullable: true|false` 키를
가지는지 확인하세요. 과거 버전의 `null:` 키는 YAML null 리터럴과 충돌하여
NOT NULL이 누락되는 회귀가 있었습니다 (v0.1.1에서 수정됨).

### 2.3 Stage 2 — DDL 생성 (rdb-ddl)

Blueprint를 PostgreSQL DDL + Flyway migrations + JPA Entity로 컴파일합니다.

```
/rdb-ddl-compile ./wiki --out ./db --dialect postgres
```

산출물:
```
db/
├── migrations/
│   ├── V001__create_customer.sql
│   ├── V002__create_customer_address.sql
│   ├── V003__create_customer_grade.sql
│   └── V004__seed.sql
├── entities/
│   ├── Customer.java
│   ├── CustomerAddress.java
│   └── CustomerGrade.java
└── ddl-report.md
```

> HSQLDB embedded로 정합성만 확인하고 싶으면 `--dialect hsqldb`로 변경하세요.
> Stage 3가 기본으로 사용하는 in-memory DB와 동일합니다.

### 2.4 Stage 3 — Java 백엔드 (rdb-mybatis)

Blueprint + migrations로부터 Controller / Service / Mapper / MyBatis XML을 생성하고,
**Stage 4가 소비할 `endpoints.json`을 동시에 emit**합니다.

```bash
/karpathy-rdb-mybatis compile \
  --blueprint ./wiki/_blueprint.yaml \
  --ddl-dir   ./db/migrations \
  --out       ./backend
```

산출물:
```
backend/
├── src/main/java/com/nexacro/uiadapter/
│   ├── controller/CustomerController.java
│   ├── service/CustomerService.java
│   ├── service/impl/CustomerServiceImpl.java
│   ├── mapper/CustomerMapper.java
│   └── domain/Customer.java
├── src/main/resources/
│   ├── schema.sql
│   ├── data.sql
│   └── mybatis/mapper/CustomerMapper.xml
├── endpoints.json           ← Stage 4 입력
└── mybatis-report.md
```

**Endpoints 미리보기:**
```bash
cat ./backend/endpoints.json
```
각 entity는 최소 `select_datalist_map` + `save_datalist_map` 두 메서드를 가지며,
`http_path`는 `/uiadapter/<entity>/<method>` 패턴입니다.

### 2.5 Stage 4 — nexacro 화면 (rdb-nexacro)

Blueprint + endpoints.json으로 entity별 xfdl form, dsMenu seed, typedefinition patch를
생성합니다.

```bash
python D:\AI\workspace\andrej-karpathy-rdb-nexacro\scripts\form_gen.py compile `
  --blueprint .\wiki\_blueprint.yaml `
  --endpoints .\backend\endpoints.json `
  --service-name Customer `
  --out       .\frontend
```

> `--service-name` 은 nexacro Service id 와 URL slug 의 기준이 됩니다 (`SvcCustomer`,
> `/uiadapter/customer`). 미지정 시 blueprint 의 `service_pascal` → `"Default"` 순으로 fallback.
> 도메인 1개 = Service 1개 모델 (v0.4 Phase E).

산출물:
```
frontend/
├── nxui/_form_/customer.xfdl
├── nxui/_form_/customer_address.xfdl
├── nxui/_form_/customer_grade.xfdl
├── nxui/_datasets_/dsMenu.seed.xml
├── patches/typedefinition.patch.xml
└── docs/nexacro-report.md
```

폼 구조: 검색 패널(상단) + 편집 가능한 Grid(중단) + 액션 버튼(하단). PK 컬럼은
자동으로 `edittype="none"` 처리되며, `*_yn`으로 끝나는 char(1) 컬럼은 Y/N Combo로
렌더됩니다.

### 2.6 통합 — scaffold + overlay → war

마지막으로 외부 plugin `/nexacro-fullstack-starter`로 빈 프로젝트 골격을 만들고,
Stage 3 + Stage 4 산출물을 그 위에 overlay합니다.

> v0.4 Phase F 부터 위 1~4 stage **와** Stage 5 (target overlay) 가 `scripts/scaffold_cli.py`
> 1 회 호출로 묶입니다. 권장 경로는 **(A) 자동 overlay** — `--target-project` 한 줄 추가.
> 기존 수동 cp / `overlay.sh` 절차 **(B)** 는 fallback 으로 유지.

**(A) 권장 — 자동 overlay (v0.4 Phase F):**

```
# (1) Stage 4' — 빈 scaffold (이미 있으면 skip)
/nexacro-fullstack-starter --jdk 17 --framework spring-boot --name customer-mgmt-app
```

```powershell
# (2) 1~5 stage 한 번에 — Stage 5 가 ./customer-mgmt-app 위로 overlay
python scripts/scaffold_cli.py `
  --domain "고객관리" --wiki-mode preset --preset 고객관리 `
  --package com.example.customer --out ./customer-scaffold `
  --dialect hsqldb --service-name Customer `
  --target-project ./customer-mgmt-app
```

생성 후 자동으로:
- `customer-mgmt-app/src/main/java/com/nexacro/uiadapter/customer/**/*.java` 배치 (`com.example.customer` → `com.nexacro.uiadapter.customer` 자동 rename)
- `customer-mgmt-app/src/main/resources/{schema.sql, data.sql, mybatis/mapper/*.xml}` 배치 (xml `namespace`/`type`/`resultType`/`parameterType` 도 rename)
- `customer-mgmt-app/nxui/packageN/customer/*.xfdl` 배치
- `customer-mgmt-app/nxui/packageN/frame/frameLogin.xfdl` 의 `<Dataset id="dsSample">` 에 `BIZ_CUSTOMER` 그룹 + entity row 들 추가
- `customer-mgmt-app/nxui/packageN/typedefinition.xml` 의 `<Services>` 에 `<Service prefixid="customer" ...>` 한 줄 추가

```bash
# (3) 빌드 + 실행
cd customer-mgmt-app
mvn -q -DskipTests package
mvn spring-boot:run
```

> 충돌 시 `--overlay-force` 를 추가하세요 (기존 파일 `.bak` 백업 후 덮어쓰기). 기본은 fail-fast.
> idempotent — 동일 명령 재실행 시 menu row / Service entry 중복 추가 없음, `.bak` 도 한 번만 생김.
> `frameLogin.xfdl` 의 `dsSample` 컬럼이 본 도구가 요구하는 9개 (`level/groupId/menuId/menuNm/menuUrl/sortNo/upMenuId/useYn/auth`) 와 다르면 menu 단계만 skip + `scaffold-report.md` 에 실 ColumnInfo / 필요 컬럼 / missing 목록 출력 (Java/xfdl/typedef 단계는 계속).

**(B) Fallback — 수동 cp / overlay.sh (Phase F 이전 방식):**

`--target-project` 를 안 쓰거나 base scaffold 가 비표준 위치/구조일 때.

```
# (1) Stage 4' — 빈 scaffold (latest v0.8.2)
/nexacro-fullstack-starter --jdk 17 --framework spring-boot --name customer-mgmt-app
```

```bash
# (2) Stage 3 백엔드 overlay
cp -r ./backend/src/main/java/com/nexacro/uiadapter/. \
      ./customer-mgmt-app/src/main/java/com/nexacro/uiadapter/
cp -r ./backend/src/main/resources/mybatis/. \
      ./customer-mgmt-app/src/main/resources/mybatis/
cp ./backend/src/main/resources/schema.sql ./customer-mgmt-app/src/main/resources/
# data.sql 은 scaffold_cli.py 로 만들었으면 이미 src/main/resources/ 에 들어있음.
# form_gen 단독 실행 시에만 수동 cp:
[ -f ./backend/src/main/resources/data.sql ] && \
  cp ./backend/src/main/resources/data.sql ./customer-mgmt-app/src/main/resources/

# (3) Stage 4 프런트 overlay
bash D:/AI/workspace/andrej-karpathy-rdb-nexacro/scripts/overlay.sh \
     ./frontend ./customer-mgmt-app

# (4) typedefinition.xml 수동 patch — patches/typedefinition.patch.xml 의 <Service .../> 한 줄을 base 의 <Services> 에 삽입

# (5) 빌드 + 실행
cd customer-mgmt-app
mvn -q -DskipTests package
mvn spring-boot:run
```

> **scaffold_cli.py 사용 시 자동 처리되는 항목** (v0.4 Phase E + F):
> - Phase E: `--dialect hsqldb` → Stage 2 HSQLDB schema/seed
> - Phase E: Stage 2 seed → Stage 3 `data.sql` 자동 wiring
> - Phase E: `--service-name` → 단일 `SvcXxx` (per-entity Service 분리 X)
> - Phase F: `--target-project` → base scaffold 위로 자동 overlay + Java package rename + menu inject + typedef merge

브라우저에서 `http://localhost:8080/uiadapter/`가 응답하면 정상.
nexacro Studio로 `customer-mgmt-app/nxui/`를 열어 화면을 확인할 수 있습니다.

`POST /uiadapter/customer/select_datalist_map`을 호출하여 NexacroResult 직렬화가
성공하면 end-to-end 통과 (라이선스 설치 환경 필요).

---

## 3. Stage별 Reference

### 3.1 andrej-karpathy-rdb-skill v0.1.1 — Plan

**위치:** `D:\AI\workspace\andrej-karpathy-rdb-skill`

**역할:** 자연어 / 도메인 wiki를 받아 도메인-엔티티-컬럼-관계 그래프를
`_blueprint.yaml`로 정규화.

**Slash commands:**

| Command | 입력 | 동작 |
| :-- | :-- | :-- |
| `/karpathy-rdb init <name> --preset <preset>` | preset 키워드 | wiki scaffold 생성 |
| `/karpathy-rdb ingest <text>` 또는 `--file <path>` | 자연어 / markdown | 엔티티/속성/관계 추출하여 wiki에 추가 |
| `/karpathy-rdb compile` | wiki 디렉터리 | `_blueprint.yaml`로 컴파일 |

**입력 형식:** 자연어 또는 YAML frontmatter가 있는 markdown wiki

**출력 형식 (`_blueprint.yaml`):**
```yaml
version: 1
project: customer-management
domains:
  - name: customer
    entities: [customer, customer_address, customer_grade]
entities:
  - name: customer
    columns:
      - { name: customer_id, type: varchar(40), pk: true,  nullable: false }
      - { name: email,       type: varchar(255),           nullable: false, unique: true }
      - { name: grade_cd,    type: char(2),                nullable: false }
      - { name: vip_yn,      type: char(1),                nullable: false }
relations:
  - { from: customer_address, to: customer, type: many-to-one, on: customer_id }
validation:
  passed: true
```

**핵심 규칙:**
- 모든 컬럼은 `nullable: true|false` 키를 가져야 함 (`null:` 키는 deprecated)
- `validation.passed: true` 여야 후속 Stage가 진행 가능 (Stage 4의 N001)

---

### 3.2 andrej-karpathy-rdb-ddl v0.1.2 — Backend DB

**위치:** `D:\AI\workspace\andrej-karpathy-rdb-ddl`

**역할:** Blueprint를 SQL DDL + Flyway migrations + JPA Entity로 컴파일.

**Slash command:**
```
/rdb-ddl-compile <wiki_path> --out ./db --dialect postgres
```

| 옵션 | 값 | 설명 |
| :-- | :-- | :-- |
| `<wiki_path>` | required | Stage 1의 wiki 디렉터리 또는 `_blueprint.yaml` 직접 지정 |
| `--out` | required | 출력 디렉터리 (예: `./db`) |
| `--dialect` | `postgres` \| `hsqldb` | 기본 `postgres`. Stage 3 in-memory 검증용은 `hsqldb` |

**출력:**
```
<out>/
├── migrations/V001__create_*.sql, V002__..., V003__..., V004__seed.sql
├── entities/<Entity>.java                  (JPA @Entity)
└── ddl-report.md                           (생성 요약)
```

**Convention:**
- migration 파일명은 Flyway 호환: `V<순번>__<설명>.sql`
- `V004__seed.sql`은 Stage 1 blueprint에 `seed:` 블록이 있을 때만 생성
- HSQLDB 방언은 임베디드 in-memory 검증을 위한 것으로 PG의 모든 타입을 지원하지 않음

---

### 3.3 andrej-karpathy-rdb-mybatis v0.1.4 — Middle Java

**위치:** `D:\AI\workspace\andrej-karpathy-rdb-mybatis`

**역할:** Blueprint + DDL을 받아 nexacro uiadapter 패턴의 Controller / Service /
Mapper / MyBatis XML과 schema.sql을 emit. v0.1.4부터 **Stage 4용 endpoints.json도 함께 emit**.

**Slash command:**
```bash
/karpathy-rdb-mybatis compile \
  --blueprint <path>/_blueprint.yaml \
  --ddl-dir   <path>/db/migrations \
  --out       <path>/backend
```

| 옵션 | 설명 |
| :-- | :-- |
| `--blueprint` | Stage 1 산출 |
| `--ddl-dir` | Stage 2 산출의 `migrations/` 경로 |
| `--out` | 출력 backend 디렉터리 |
| `--skip-compile` | Java 컴파일 검증 생략 (CI 빠른 실행용) |
| `--dry-run` | 파일 emit만 하고 검증 단계 skip |

**출력 트리:**
```
<out>/
├── src/main/java/com/nexacro/uiadapter/
│   ├── controller/<Entity>Controller.java
│   ├── service/<Entity>Service.java
│   ├── service/impl/<Entity>ServiceImpl.java
│   ├── mapper/<Entity>Mapper.java
│   └── domain/<Entity>.java
├── src/main/resources/
│   ├── schema.sql
│   ├── data.sql                   (seed 있을 때만)
│   └── mybatis/mapper/<Entity>Mapper.xml
├── endpoints.json                 ← Stage 4 입력
└── mybatis-report.md
```

**endpoints.json 스키마:**
```json
{
  "version": 1,
  "context_path": "/uiadapter",
  "entities": [
    {
      "name": "customer",
      "endpoint_base": "/customer",
      "endpoints": [
        { "method": "select_datalist_map", "http_path": "/uiadapter/customer/select_datalist_map" },
        { "method": "save_datalist_map",   "http_path": "/uiadapter/customer/save_datalist_map" }
      ]
    }
  ]
}
```
- 각 entity는 `select_datalist_map` + `save_datalist_map` 두 메서드를 **반드시** 포함
- import는 jakarta lane (`com.nexacro.uiadapter.jakarta.core.*`) — JDK17 / Spring Boot 3 전용

---

### 3.4 andrej-karpathy-rdb-nexacro v0.1.0 — Frontend xfdl

**위치:** `D:\AI\workspace\andrej-karpathy-rdb-nexacro`

**역할:** Blueprint + endpoints.json으로 entity별 nexacro xfdl form 생성.
2-tier 레이아웃 (Search panel + editable Grid + action buttons).

**CLI:**
```bash
python scripts/form_gen.py compile \
  --blueprint <path>/_blueprint.yaml \
  --endpoints <path>/endpoints.json \
  --out       out/
```

**Flags:**

| Flag | 설명 |
| :-- | :-- |
| `--blueprint` | required. Stage 1 산출 |
| `--endpoints` | Stage 3 v0.1.4+ 산출 |
| `--infer-endpoints` | endpoints.json 없을 때 blueprint로부터 합성 (Stage 3 미실행 시) |
| `--out` | required. 출력 루트 |
| `--frame packageN\|minimal` | 프레임 스타일. 기본 `packageN` (MDI) |
| `--default-pattern D2\|F1\|C1` | entity 에 pattern frontmatter 없을 때 기본 폼 패턴 |
| `--service-name <PascalCase>` | nexacro Service id 기준 (`SvcXxx`) + URL slug (`/uiadapter/xxx`). 미지정 시 blueprint `service_pascal` → `"Default"` fallback. v0.4 Phase E. |
| `--strict` | type fallback 발생 시 실패 |
| `--force` | 기존 xfdl 덮어쓰기 (`<name>.xfdl.bak`로 백업 후) |

**출력:**
```
<out>/
├── nxui/_form_/<entity>.xfdl
├── nxui/_datasets_/dsMenu.seed.xml
├── patches/typedefinition.patch.xml
└── docs/nexacro-report.md
```

**Validators (실패 시 exit code 1, stderr에 `[N00X ...]` 출력):**

| ID | 체크 |
| :-- | :-- |
| N001 | blueprint version + `validation.passed: true` |
| N002 | endpoints.json shape (version, 필수 method) |
| N003 | blueprint ↔ endpoints entity 집합 일치 |
| N004 | 모든 entity가 PK 컬럼 ≥ 1 |
| N005 | 모든 entity가 검색 가능한 컬럼 ≥ 1 (PK 또는 NOT NULL) |
| N006 | emit된 모든 XML이 well-formed |
| N007 | overlay 충돌 가드 (`--force` 없이 기존 파일 덮어쓰기 시도) |

**Type 매핑 (요약):**

| PG 타입 | Dataset type | Grid edit | Search |
| :-- | :-- | :-- | :-- |
| `varchar(N)` | STRING (size=N) | Edit | Edit |
| `char(1) ... _yn` (non-pk) | STRING | Combo (Y/N) | Combo |
| `char(N)` | STRING (size=N) | Edit | Edit |
| `int`, `bigint` | INT | MaskEdit | Edit |
| `numeric(p,s)` | DECIMAL | MaskEdit | Edit |
| `date`, `timestamp` | DATE | Calendar | Calendar |
| `boolean` | STRING | Combo | Combo |
| PK 컬럼 (모든 타입) | (위 동일) | none (readonly) | (해당 없음) |

전체 매트릭스는 `references/type-mapping-matrix.md` 참조.

---

### 3.5 scaffold_cli.py v0.4 — orchestrator + Stage 5 overlay

**위치:** `D:\AI\workspace\business-fullstack-creater\scripts\scaffold_cli.py`

**역할:** Stage 1~4 한 번에 실행 후 (Phase F) Stage 5 target overlay 까지 자동 수행.

**Flags:**

| Flag | 기본 | 설명 |
| :-- | :-- | :-- |
| `--domain <name>` | required | 도메인 라벨 (e.g. `"고객관리"`) |
| `--wiki-mode preset\|wiki` | `preset` | wiki 입력 모드 |
| `--preset <name>` | — | `--wiki-mode preset` 필수 |
| `--wiki <path>` | — | `--wiki-mode wiki` 필수 |
| `--lane nexacro\|vanilla` | `nexacro` | Stage 3 lane |
| `--default-pattern D2\|F1\|C1` | — | Stage 4 entity 폼 패턴 fallback |
| `--package <java.pkg>` | required | Spring base package (e.g. `com.example.order`). Stage 5 overlay 시 `com.nexacro.uiadapter.<slug>` 로 자동 rename |
| `--out <dir>` | required | 출력 루트 (1-wiki / 2-ddl / 3-mybatis / 4-nexacro) |
| `--stop-after-stage 1..5` | `5` | Stage 5 까지 실행 |
| `--dialect postgres\|hsqldb` | `postgres` | Stage 2 SQL 방언 (Phase E) |
| `--service-name <PascalCase>` | `domain_slug` PascalCase | 단일 Service id (Phase E) |
| `--target-project <dir>` | — | **Phase F.** Stage 5 overlay 대상 (`/nexacro-fullstack-starter` 산출 root). 미지정 시 Stage 5 skip |
| `--overlay-force` | `false` | **Phase F.** Stage 5 가 기존 파일 덮어쓰기 허용 (`.bak` 자동 생성). 기본은 충돌 시 fail-fast |
| `--target-package-prefix <java.pkg>` | `com.nexacro.uiadapter` | **v0.4.2.** Stage 5 가 Java/MyBatis XML 을 rewrite 할 target 패키지 prefix. source prefix 는 `--package` 마지막 segment 를 제외한 전체로 자동 도출 |

**Stage 5 overlay 동작 요약:**

1. **Java overlay + package rename** — `<out>/3-mybatis/src/main/java/com/example/<slug>/**/*.java` → `<target>/src/main/java/com/nexacro/uiadapter/<slug>/**/*.java`. `package`/`import` 선언 자동 rewrite.
2. **Resources overlay** — `schema.sql` / `data.sql` 은 `.scaffold.bak` 백업 후 교체. MyBatis mapper xml 은 `namespace`/`type`/`resultType`/`parameterType` rewrite 후 복사.
3. **xfdl form copy** — `<out>/4-nexacro/nxui/_form_/*.xfdl` → `<target>/nxui/packageN/<slug>/*.xfdl` (신규 prefix dir).
4. **Menu inject** — `<target>/nxui/packageN/frame/frameLogin.xfdl` 의 `<Dataset id="dsSample">` 안에 도메인 그룹 row (`BIZ_<DOMAIN>`) + entity row (`BIZ_<DOMAIN>_<ENTITY>`) 추가. **컬럼 schema mismatch 시 menu 단계만 skip** (다른 단계 계속).
5. **Typedef merge** — `<target>/nxui/packageN/typedefinition.xml` 의 `<Services>` 에 `<Service prefixid="<slug>" type="form" url="./<slug>/" cachelevel="session" version=""/>` 한 줄 삽입.
6. **Report** — `<out>/scaffold-report.md` 의 `## Stage 5 overlay` 섹션에 copied/renamed/backed_up 카운트 + (있다면) menu schema-mismatch 경고 기록.

**Idempotency:**
- 동일 명령 2회 실행: menu row 중복 추가 0, Service entry 중복 0, `.bak` 파일 1개만 (one-shot 백업)
- 단, 2회차는 java/xfdl 이 이미 존재 → `--overlay-force` 필요 (의도적)

---

## 4. 통합 — Stage 3+4 → nexacro-fullstack-starter overlay

핸드오프 계약 전문은 [`needs/Plugin참조/3. Middle+Frontend - Stage 3→4 nexacro 핸드오프 계약.md`](../needs/Plugin%EC%B0%B8%EC%A1%B0/3.%20Middle%2BFrontend%20-%20Stage%203%E2%86%924%20nexacro%20%ED%95%B8%EB%93%9C%EC%98%A4%ED%94%84%20%EA%B3%84%EC%95%BD.md) 참조.
요점만 발췌:

### 4.1 실행 순서 (반드시 이 순서)

```
[1] Stage 4' (nexacro-fullstack-starter)  →  빈 ./<PROJECT>/ scaffold 생성
[2] Stage 3 (rdb-mybatis) overlay         →  src/main/java + resources/mybatis 덮어쓰기
[3] Stage 4 (rdb-nexacro) overlay         →  nxui/_form_, _datasets_, patches 덮어쓰기
[4] mvn package                           →  war 빌드
```

이유: Stage 4'는 `TARGET_DIR`이 존재하면 중단합니다. Stage 3은 `pom.xml` /
`Application.java` / `config/`를 건드리지 않고 **도메인 코드만** 얹는 모델입니다.

### 4.2 충돌 처리 정책

v0.4 Phase F `--target-project` 사용 시 Stage 5 가 다음 정책으로 자동 적용:

| 파일 | 정책 |
| :-- | :-- |
| `src/main/java/com/nexacro/uiadapter/<slug>/{controller,service,service/impl,mapper,domain}/<Entity>*.java` | 존재 시 `.bak` 백업 후 덮어쓰기. `--overlay-force` 없으면 사전 conflict-scan 단계에서 RuntimeError + 충돌 파일 listing (변경 시작 전에 fail-fast) |
| `src/main/resources/mybatis/mapper/<Entity>Mapper.xml` | 위 동일. xml 안의 `namespace`/`type`/`resultType`/`parameterType` 의 `com.example.<slug>` 도 `com.nexacro.uiadapter.<slug>` 로 자동 rewrite |
| `src/main/resources/schema.sql` | base 본을 `schema.sql.scaffold.bak` 로 1회 백업 후 Stage 3 본으로 교체 |
| `src/main/resources/data.sql` | 위 동일 (`data.sql.scaffold.bak`) |
| `pom.xml`, `Application.java`, `config/*.java`, `application.yml` | **절대 수정 안 함** (Stage 4' 보존) |
| `nxui/packageN/<slug>/<entity>.xfdl` | 신규 prefix dir 이므로 충돌 거의 없음. 존재 시 `.bak` (overlay-force 필요) |
| `nxui/packageN/frame/frameLogin.xfdl` | 원본 `frameLogin.xfdl.bak` 1회 백업 후 in-place patch (`<Dataset id="dsSample">` 안의 `</Rows>` 직전에 도메인 row append). 동일 `menuId` 존재 시 skip (idempotent). **컬럼 schema mismatch 시** patch 하지 않고 실 ColumnInfo + 필요 컬럼 (`level/groupId/menuId/menuNm/menuUrl/sortNo/upMenuId/useYn/auth`) + missing 목록을 `scaffold-report.md` 에 사용자 메시지로 출력 후 menu 단계만 skip. Java/xfdl/typedef 단계는 계속 |
| `nxui/packageN/typedefinition.xml` | 원본 `typedefinition.xml.bak` 1회 백업 후 `<Services>` 닫기 직전에 `<Service prefixid="<slug>" .../>` 한 줄 삽입. 동일 `prefixid` 존재 시 skip (idempotent) |

(`--target-project` 미지정 시 Stage 5 skip → 위 정책 적용 안 됨. 수동 overlay 절차는 §2.6 (B) 참조.)

> v0.4 Phase E 부터 entity 별이 아닌 도메인당 1개 Service 만 생성 (`SvcOrder` 단일 — `SvcOrderItem`/`SvcPayment` 분리 X).

### 4.3 검증 체크리스트 (overlay 후)

**공통 (수동 / 자동 overlay 모두 해당):**

- [ ] `mvn -q -DskipTests compile` 성공
- [ ] `src/main/java/com/nexacro/uiadapter/Application.java` 존재 (Stage 4' 보존)
- [ ] `src/main/java/com/nexacro/uiadapter/<slug>/controller/<Entity>Controller.java` 존재 (Stage 3 + Phase F package rename 적용)
- [ ] `mybatis/mapper/<Entity>Mapper.xml`의 `namespace`가 `com.nexacro.uiadapter.<slug>.mapper.<Entity>Mapper`와 일치
- [ ] `schema.sql`의 NOT NULL 제약이 blueprint `nullable: false` 컬럼과 1:1 매핑
- [ ] `mvn spring-boot:run` 후 `http://localhost:8080/uiadapter/` 응답
- [ ] `POST /uiadapter/<entity>/select_datalist_map` → NexacroResult 직렬화 성공

**Stage 5 자동 overlay (`--target-project` 사용 시 추가 확인):**

- [ ] `scaffold-report.md`의 `stage5` 섹션에 `java_copied`, `resources_copied`, `xfdl_copied` 목록 출력
- [ ] target의 모든 .java 파일이 `src/main/java/com/nexacro/uiadapter/<slug>/...` 아래 위치 (구버전 `com/example/...` 잔존 없음)
- [ ] target `nxui/packageN/frame/frameLogin.xfdl`의 `dsSample` Rows에 도메인 그룹 (`BIZ_<DOMAIN>`) + entity 메뉴 row가 추가됨
- [ ] target `nxui/packageN/typedefinition.xml`의 `<Services>` 블록에 `prefixid="<slug>"` Service entry 존재
- [ ] target `nxui/packageN/<slug>/<Entity>.xfdl` 파일이 존재
- [ ] 기존 `schema.sql` 가 있던 경우 `schema.sql.scaffold.bak` 백업 파일 생성됨 (1회만)
- [ ] `frameLogin.xfdl.bak`, `typedefinition.xml.bak` 백업 파일 존재 (1회만 생성, 재실행해도 변경 없음)
- [ ] `report["menu_warning"]` 가 `None` (schema mismatch 없음). 경고가 있으면 dsSample ColumnInfo 점검 필요 — §5.5 참조

### 4.4 JDK / lane 매핑

| Stage 3가 emit하는 import | 호환 Stage 4' runner |
| :-- | :-- |
| `com.nexacro.uiadapter.jakarta.core.*` | `boot-jdk17-jakarta` (Spring Boot 3 + JDK17) |
| `com.nexacro.uiadapter.spring.core.*` (legacy) | `boot-jdk8-javax` (Spring Boot 2 + JDK8) — Stage 3 v0.1.4 미발행 |

> 현재는 jakarta lane 만 생성합니다. javax/JDK8이 필요하면 Stage 3에 lane 파라미터
> (`--lane jakarta|javax`) 도입이 필요 (후속 작업).

---

## 5. 트러블슈팅

### 5.1 Stage 1 (rdb-skill)

| 증상 | 원인 | 해결 |
| :-- | :-- | :-- |
| `_blueprint.yaml`의 컬럼이 NOT NULL 누락 | 구버전의 `null:` 키 (YAML null literal과 충돌) | v0.1.1로 업그레이드. 모든 컬럼이 `nullable:` 키를 사용해야 함 |
| `validation.passed: false` | 관계 cycle / 필수 키 누락 / unknown type | `compile` 출력의 validation 섹션 확인 후 wiki 수정 |
| 동일 entity가 wiki에 여러 번 ingest됨 | `ingest` 호출 시 중복 검사 안 함 | `wiki/entities/<name>.md` 직접 수정 또는 `init`으로 reset |

### 5.2 Stage 2 (rdb-ddl)

| 증상 | 원인 | 해결 |
| :-- | :-- | :-- |
| `V004__seed.sql` 없음 | blueprint에 `seed:` 블록 없음 | 정상 동작 |
| `--dialect hsqldb`에서 일부 타입이 변환됨 | HSQLDB 미지원 타입의 fallback | `--dialect postgres`로 운영 DDL 생성 |
| Java entity에 `@Id` 없음 | blueprint 컬럼에 `pk: true` 누락 | wiki에서 PK 컬럼 표기 후 재컴파일 |

### 5.3 Stage 3 (rdb-mybatis)

| 증상 | 원인 | 해결 |
| :-- | :-- | :-- |
| `endpoints.json` 없음 | Stage 3 v0.1.3 이하 사용 중 | v0.1.4 이상으로 업그레이드 (Phase 0 변경사항) |
| `mvn compile` 실패: `package com.nexacro.uiadapter.jakarta.core does not exist` | uiadapter 의존성 누락 또는 javax lane 사용 중 | Stage 4' scaffold의 `pom.xml` 사용 — jakarta artifact가 들어 있음 |
| Mapper namespace mismatch | Stage 4' scaffold sample mapper와 충돌 | overlay 시 Stage 3 본이 wins (덮어쓰기). namespace 수동 확인 |

### 5.4 Stage 4 (rdb-nexacro)

| Validator | 증상 | 해결 |
| :-- | :-- | :-- |
| **N001** | `[N001 blueprint validation.passed must be true]` | Stage 1로 돌아가 blueprint 수정 후 `compile` 재실행 |
| **N002** | `[N002 endpoints.json not found ...]` 또는 `unsupported version` | Stage 3 v0.1.4+ 출력의 endpoints.json 경로 확인. 없으면 `--infer-endpoints` 사용 (Stage 3 산출 없을 때) |
| **N003** | `[N003 entity sets diverge ...]` | blueprint와 endpoints의 entity 집합이 불일치. 둘 중 하나 동기화 |
| **N004** | `[N004 entity 'X' has no PK column]` | blueprint에서 해당 entity의 PK 컬럼에 `pk: true` 표기 |
| **N005** | `[N005 entity 'X' has no searchable columns]` | PK도 NOT NULL 컬럼도 없는 entity. 최소 1개 컬럼을 `nullable: false`로 |
| **N006** | `[N006 malformed XML ...]` | 보통 템플릿 변경 후 발생. PR로 보고. 임시 회피 — 해당 entity만 제외 후 generate |
| **N007** | `[N007 overlay conflict: ... exists — use --force]` | 의도적이면 `--force` 추가. xfdl이 `.bak`로 자동 백업됨 |

**기타:**
- `python scripts/form_gen.py: ModuleNotFoundError` → `PYTHONPATH=<repo>/scripts` 환경변수 설정 후 재실행
- xfdl이 nexacro Studio에서 안 열림 → `nexacro-report.md`로 어떤 entity가 emit됐는지 확인. dsMenu seed가 실제 화면 ID와 매칭되는지 점검

### 5.5 통합 (overlay + war)

| 증상 | 해결 |
| :-- | :-- |
| `target.replace(target.with_suffix(target.suffix + ".bak"))` 후에도 N007 발생 | `.bak` 파일이 이미 존재. 수동으로 제거 후 `--force` 재시도 |
| nexacro Studio에서 `dsMenu` 비어 있음 | `nxui/_datasets_/dsMenu.seed.xml`을 nexacro project에 import 했는지 확인 |
| ~~`typedefinition.xml`에 Service entry 없음~~ | **v0.4 Phase F 부터 `--target-project` 사용 시 `typedef_merger`가 자동 삽입.** 수동 옵션은 §2.6 (B) 참조 |
| `POST /uiadapter/...` → 500 license error | nexacro N v24 라이선스 미설치. 개발 환경엔 라이선스가 필요. 대안으로 plain JSON 응답 모드 검토 |

**Stage 5 자동 overlay 전용 (v0.4 Phase F):**

| 증상 | 원인 | 해결 |
| :-- | :-- | :-- |
| `RuntimeError: Stage 5 overlay would overwrite existing files (use --overlay-force to allow)` | target에 이미 동일 경로 파일이 존재 (이전 overlay 흔적 또는 수동 작성본) | 충돌 파일 list를 확인 — (1) 의도적 덮어쓰기면 `--overlay-force` 추가 (모든 충돌 파일이 `.bak` 백업됨), (2) 수동 작성본을 보존하려면 해당 파일을 target에서 삭제/이동 후 재시도 |
| `report["menu_warning"]: ... dsSample column schema mismatch — menu injection skipped` | target `frameLogin.xfdl`의 `<Dataset id="dsSample">` `ColumnInfo`가 tool이 기대하는 9개 컬럼(level/groupId/menuId/menuNm/menuUrl/sortNo/upMenuId/useYn/auth)을 모두 포함하지 않음 | (1) 경고 메시지의 `missing` 컬럼 목록 확인 → frameLogin.xfdl에 해당 `<Column id="..." type="STRING" size="256"/>` 추가, 또는 (2) menu 단계만 수동 처리. 다른 step (java/resources/xfdl/typedef)은 정상 진행됨 |
| `report["menu_warning"]: frameLogin.xfdl not found at ...` | target이 nexacro-fullstack-starter 기반이 아님, 또는 frame 디렉터리 구조가 다름 | menu 단계 건너뛰고 수동으로 dsSample Row 추가. 나머지 step은 정상 진행 |
| `report["typedef_warning"]: typedefinition.xml not found at ...` | target에 `nxui/packageN/typedefinition.xml` 없음 | 수동으로 `<Service id="Svc<Pascal>" prefixid="<slug>" url="./<slug>/" .../>` 삽입 |
| 재실행 후 메뉴 row가 중복됨 | (Phase F idempotency 보장에서 어긋남 — 발견 시 보고 요망) | `frameLogin.xfdl.bak`로 복원 후 `--target-project`만 재실행 (overlay_force 불필요). row 중복은 버그 후보 |
| `.bak` 파일이 자동 정리되지 않음 | 의도된 정책 — `.bak` / `.scaffold.bak`은 사용자가 명시적으로 삭제할 때까지 유지 | 만족 후 수동 삭제 (`Remove-Item *.bak -Recurse`) |

---

## 6. 다음 단계

### 6.1 Stage 4 v0.1.1 로드맵 (final reviewer notes)

- [ ] `_pascal()` 헬퍼를 `scripts/utils.py`로 추출 (3개 모듈에 중복)
- [ ] `tests/_review_out2/` 정리 + `.gitignore`
- [ ] `TypeMapperError`에 N008 코드 부여 + `form_gen.py`에서 catch
- [ ] `keep_trailing_newline` 차이를 템플릿 헤더에 명시

### 6.2 향후 추가 plugin (`/nexacro-claude-skills`)

```
/nexacro-data-format     ← Dataset 표준화
/nexacro-form-maker      ← 화면 생성 보조
/nexacro-project-maker   ← project 단위 scaffold
/nexacro-build           ← build 자동화
```

### 6.3 후속 작업 (TBD)

- Stage 3에 `--lane jakarta|javax` 도입 → Spring Boot 2 / JDK8 환경 호환 *(현재 `--lane nexacro|vanilla` 만 — v0.3 Phase B 산출)*
- `/business-fullstack-creater scaffold` 슬래시 커맨드 — Stage 1→2→3→4+overlay 자동화 *(v0.4 완료 — `scripts/scaffold_cli.py` 참조)*
- Overlay 단계 entity 충돌 감지 시 사용자 확인 prompt

### 6.4 전략 로드맵 (v0.3 ~ v0.7)

단기 ToDo (1: Web UI / 2: 어댑터화 / 3: 단위 확장)와 장기 C 차원 (메타 추출 / 도메인 추천 / 마켓플레이스, 구 task #97)을 **데이터 흐름 기준**으로 통합 재정렬. 핵심 원칙:
- **C 차원의 진입 조건은 "데이터"**: 누적된 catalog · learn-log · contribute 가 없으면 무의미 → 데이터 조건이 차오르는 시점에 진입 (장기 ≠ 후순위, "조건 충족 시 즉시").
- **v0.3 + 실 사용이 데이터를 만든다** — C는 그 위에 올라간다.
- **Web UI 진입 위험 회피**: "1회 실행 큐레이션" 가치는 CLI scaffold만으로 80% 달성 가능 → Web UI는 비개발자 수요가 실제로 생긴 다음에.

각 단계는 v0.2처럼 Milestone Gate 5축 자체 리뷰 통과를 조건으로 다음 진행.

| 순위 | 버전 | 내용 | 진입 조건 | Effort | 상태 |
|:-:|---|---|---|:-:|:-:|
| 1 | **v0.3** | 단위 확장 (#3): M:N · vanilla lane · UI 패턴 catalog | 즉시 | 2주 | ✅ 완료 (2026-05-18, M-C 4.8/5) |
| 2 | **v0.3.x** | C-2 유사 도메인 추천 | catalog 5+ 도메인 | 1주 | 대기 |
| 3 | **v0.4** | CLI scaffold (#1 핵심가치 80%) | v0.3 완료 | 2주 | ✅ 완료 (2026-05-18, M-D 4.4/5) |
| 4 | **v0.5** | 어댑터화 (#2): contract + MySQL + lane 정식화 | v0.4 + 실사용 1회 | 3-4주 | 대기 |
| 5 | **v0.6** | C-1 메타 추출 | 실 프로젝트 3+ | 1-2주 | 대기 |
| 6 | **v0.7** | C-3 마켓플레이스 + Web UI 풀버전 | catalog format 안정 + 비개발자 수요 | 4주+ | 대기 |

#### v0.3 — 단위 기능 확장 ✅ (Phase A + B + C 완료, 2026-05-18)

- **Phase A (back-end)** — blueprint `relations[]` 의 M:N junction 자연 지원 + 복합 PK + 복합 FK (`fk.column: [a, b]`). Stage 1 V005 가 junction 패턴을 INFO 로 감지. Stage 2 토포소트 / FK 생성기 다중 컬럼 케이스 처리. *(M-A 게이트 통과)*
- **Phase B (middle)** — Stage 3 에 `--lane vanilla` 추가 (기본 `--lane nexacro`). vanilla lane 산출은 NexacroBase / NexacroResult / DataSet 의존성 없는 표준 Spring Boot 3 + MyBatis POJO + `@RestController` + DTO 기반 service-impl. `endpoints.json` v2 (vanilla 전용) 동시 emit. *(M-B 게이트 4.4/5)*
- **Phase C (front-end)** — Stage 4 form layout 을 명명된 파일 기반 pattern catalog 로 분리. 번들 3종: **D2** (detail-2-tier, 기본), **F1** (form-1-tier 단일 record), **C1** (card-1-tier readonly picker). entity frontmatter 의 `pattern: <name>` 또는 `--default-pattern` 으로 선택. 패턴 카탈로그는 번들 → 글로벌 (`~/.karpathy-rdb/catalog/patterns/`) → `PatternNotFoundError`. `/karpathy-rdb contribute --kind pattern <name>` 으로 글로벌 카탈로그 승격. *(M-C 게이트 4.8/5)*

게이트 문서: [Phase A](./superpowers/specs/2026-05-15-v0.3-phase-a-ma-gate.md) · [Phase B](./superpowers/specs/2026-05-15-v0.3-phase-b-mb-gate.md) · [Phase C](./superpowers/specs/2026-05-18-v0.3-phase-c-mc-gate.md)

#### v0.3.x — C-2 유사 도메인 추천 (장기 C-2를 앞당김)
- `01-init.md` Phase 3 preset 선택 단계에서 사용자 입력 도메인명을 **LLM이 catalog frontmatter와 비교**해 가장 가까운 seed 3개 자동 제안 (벡터 DB 없음, Karpathy 원칙 유지).
- **앞당기는 이유**: C 중 가장 가볍고(1주) catalog 누적이 이미 시작됨. C 진입 첫걸음.

#### v0.4 — CLI scaffold ✅ (2026-05-18, M-D 4.4/5 PASS)

**슬래시 커맨드 (권장):**
```
/business-fullstack-creater:scaffold --domain "고객관리" --preset 고객관리
```

**직접 CLI:**
```powershell
# preset 모드 (catalog에서 도메인 wiki 자동 생성)
python scripts/scaffold_cli.py --domain "고객관리" --wiki-mode preset --preset 고객관리 `
  --package com.example.customer --out ./customer-scaffold

# wiki 모드 (기존 wiki 디렉터리 직접 지정)
python scripts/scaffold_cli.py --domain "주문관리" --wiki-mode wiki --wiki ./order-wiki `
  --package com.example.order --out ./order-scaffold

# v0.4 Phase E — HSQLDB 임베디드 + 단일 Service + 자동 data.sql 시드
python scripts/scaffold_cli.py --domain "주문관리" --wiki-mode preset --preset 주문관리 `
  --package com.example.order --out ./order-scaffold `
  --dialect hsqldb --service-name Order
```

**Phase E 전용 플래그:**

| Flag | 기본 | 설명 |
| :-- | :-- | :-- |
| `--dialect postgres\|hsqldb` | `postgres` | Stage 2 SQL 방언. `hsqldb` 선택 시 Spring Boot 임베디드 DB 로 바로 부팅 가능 |
| `--service-name <PascalCase>` | `domain_slug` → PascalCase 자동 도출 | nexacro 단일 Service id (`SvcXxx`) 와 URL slug (`/uiadapter/xxx`). 도메인 1개 = Service 1개 모델 |

**출력 레이아웃:**
```
<out>/
├── 1-wiki/                ← Stage 1 산출 (_blueprint.yaml + wiki/)
├── 2-ddl/                 ← Stage 2 산출 (migrations/ + entities/)
├── 3-mybatis/             ← Stage 3 산출 (backend/ + endpoints.json)
├── 4-nexacro/             ← Stage 4 산출 (nxui/_form_/ + datasets + patches/)
└── scaffold-report.md     ← 전체 실행 요약 (성공/실패 stage, 경로, 소요 시간)
```

**sibling-repo 규약 + 경로 오버라이드:**
- 기본: `D:\AI\workspace\` 하위에 `andrej-karpathy-rdb-{skill,ddl,mybatis,nexacro}` 가 있으면 자동 탐지.
- 오버라이드: `config/stage-paths.yaml` 로 각 stage 경로를 명시 (`.gitignore` 등재됨).
  예시: `config/stage-paths.yaml.example` 참조.

**부분 실패 시:** 실패한 stage 이후는 skip되고 `scaffold-report.md` 에 어느 stage까지 성공했는지, 에러 메시지가 기록됩니다. 성공 stage 산출물은 보존됩니다.

게이트 문서: [Phase D](./superpowers/specs/2026-05-18-v0.4-md-gate.md)

#### v0.5 — 교체 가능 아키텍처 (Phase B · 단기 #2)
- **어댑터 계약 먼저, 어댑터 두 번째.** tier마다 contract 문서 (`adapters/backend-contract.md`, `service-contract.md`, `ui-contract.md`) 선행. 입력·출력·파일 위치·호환 버전 명시.
- **back-end DB**: PostgreSQL + HSQLDB 두 어댑터를 contract로 추상화 → MySQL 추가로 일반화 검증.
- **middle service**: Stage 3 `--lane jakarta|javax|vanilla` 정식화 (v0.3의 vanilla lane을 contract 기반으로 정리).
- **front-end UI**: Stage 4(nexacro) + Stage 4'(외부 starter) 외에 React/Vue 어댑터 슬롯 정의.

#### v0.6 — C-1 메타 추출 (장기 C-1)
- `scripts/meta_extract.py`: 복수 프로젝트 `learn-log.md` 횡단 → `~/.karpathy-rdb/catalog/meta/<도메인>_meta.md` 생성 (공통 패턴, 반복 등장 entity, false-belief 경향).
- **진입 조건**: 실 프로젝트 3개 이상 누적 (각각 ingest + contribute 1회 이상). v0.3~0.5 사용 과정에서 자연 충족.

#### v0.7 — C-3 마켓플레이스 + Web UI 풀버전
- **C-3**: `catalogs/preset-catalog.yaml`을 별도 git repo로 분리, `plugin.json`에 `catalog_remote` URL 필드. 외부 contribute 도입 + 충돌 해결 정책.
- **Web UI 풀버전 (단기 #1 잔여)**: 사용자가 요구만 입력하면 agent가 단계별 큐레이션, 결과 시연·테스트, WAR/JAR 다운로드.
- **Karpathy 정신 보존 가드레일**: Web app은 **파일 기반 파이프라인 위의 view + runner**로만 동작. 진실의 원천은 항상 `wiki/`, `_blueprint.yaml`, `~/.karpathy-rdb/catalog/`. Web 측에 별도 DB·세션 상태를 두지 않는다.
- **Run Manifest**: 1회 실행 = `runs/YYYY-MM-DD-<topic>/manifest.yaml` (blueprint + 선택 어댑터 + 선택 패턴 → 산출 WAR). 재현·공유·롤백 가능.

---

## 참조

- 요구기능 원문: [`needs/business-fullstack-creater 플러그인 요구기능.md`](../needs/business-fullstack-creater%20%ED%94%8C%EB%9F%AC%EA%B7%B8%EC%9D%B8%20%EC%9A%94%EA%B5%AC%EA%B8%B0%EB%8A%A5.md)
- Stage 1 참조: [`needs/Plugin참조/1. Plan - andrej-karpathy-rdb-skill 구현.md`](../needs/Plugin%EC%B0%B8%EC%A1%B0/1.%20Plan%20-%20andrej-karpathy-rdb-skill%20%EA%B5%AC%ED%98%84.md)
- Stage 2 참조: [`needs/Plugin참조/2. Backend - DB 스키마(DDL) 생성하기.md`](../needs/Plugin%EC%B0%B8%EC%A1%B0/2.%20Backend%20-%20DB%20%EC%8A%A4%ED%82%A4%EB%A7%88(DDL)%20%EC%83%9D%EC%84%B1%ED%95%98%EA%B8%B0.md)
- Stage 3↔4 핸드오프: [`needs/Plugin참조/3. Middle+Frontend - Stage 3→4 nexacro 핸드오프 계약.md`](../needs/Plugin%EC%B0%B8%EC%A1%B0/3.%20Middle%2BFrontend%20-%20Stage%203%E2%86%924%20nexacro%20%ED%95%B8%EB%93%9C%EC%98%A4%ED%94%84%20%EA%B3%84%EC%95%BD.md)
- 설계 문서: [`docs/superpowers/specs/`](./superpowers/specs/)
- 구현 플랜: [`docs/superpowers/plans/`](./superpowers/plans/)

| Plugin repo | 경로 |
| :-- | :-- |
| Stage 1 (rdb-skill) | `D:\AI\workspace\andrej-karpathy-rdb-skill` |
| Stage 2 (rdb-ddl) | `D:\AI\workspace\andrej-karpathy-rdb-ddl` |
| Stage 3 (rdb-mybatis) | `D:\AI\workspace\andrej-karpathy-rdb-mybatis` |
| Stage 4 (rdb-nexacro) | `D:\AI\workspace\andrej-karpathy-rdb-nexacro` |
| Stage 4' (외부) | `/nexacro-fullstack-starter` (`/plugin install`) |

---

*Last updated: 2026-05-18 — v0.4.2 보완 (`--target-package-prefix` / source prefix 자동 도출 / Korean domain slug 안전망), v0.4 Phase F 완료 (Stage 5 자동 overlay: `--target-project` / Java package rename / frameLogin dsSample 메뉴 주입 / typedefinition Service merge / `.bak` 멱등 백업), Phase E (HSQLDB dialect / 자동 data.sql wiring / 단일 Service / `--service-name`)도 포함 — M-E 4.8/5, M-F 4.6/5 PASS, M-G v0.4.2 진행 중*
