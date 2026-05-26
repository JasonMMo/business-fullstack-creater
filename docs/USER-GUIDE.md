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

> **v0.5.x Gap 2~6 (2026-05-19~20) 변경점**: 패턴/워크플로 커버리지 강화.
> - **Gap 2 — Workflow service template**: blueprint entity 에 `workflow:` 블록(`status_column` + `states` + `transitions`)이 있으면 Stage 3 가 `<Entity>WorkflowService.java` + `Impl` 을 추가 emit. action 별 from-state 가드 + `update_<entity>_status` mapper method/XML 까지 자동 발행 (`approval_request`, `notification` 시드에 즉시 적용). `workflow:` 없는 entity 는 기존과 동일.
> - **Gap 3 — React overlay MD/TR pattern 컴포넌트**: master-detail-2-tier(MD) · tree-1-tier(TR) entity 가 blueprint 에 있으면 Stage 5 (react lane) 가 `MDPage.tsx` · `TRPage.tsx` 도 emit (기존 H4 API 모듈에 더해).
> - **Gap 4 — V002 validator FK side 정정**: `relations[].kind` 가 `belongs_to`/`many_to_one` 이면 FK 컬럼 존재를 **FROM** 엔티티에서 확인 (이전: 항상 TO 에서 확인하여 customer→customer_category 같은 정상 관계를 false-fail). `many_to_many` 는 junction 사용 → 컬럼 검사 skip. kind 미지정 관계는 기존(TO-side) 동작 유지 → 하위 호환 100%.
> - **Gap 5 — React overlay 7 패턴 parity**: react lane 이 nexacro 와 동일하게 **D2 · F1 · C1 · L2 · MD · TR · RO** 7종 모두 emit. 각 entity 의 `pattern` frontmatter 가 그대로 `<Pascal><Suffix>Page.tsx` 로 변환되고 (`D2Page`/`F1Page`/`C1Page`/`L2Page`/`MDPage`/`TRPage`/`ROPage`), `RO` 는 read-only 불변식대로 `saveDataListMap` 호출 없이 `exportToCsv()` 만 노출.
> - **Gap 6 — Pattern resolver 회귀 freeze**: 7 패턴 (`D2/F1/C1/L2/MD/TR/RO`) 의 manifest + form.xfdl.j2 가 generic resolver 로 모두 로드되는지 parametrized 회귀 테스트로 동결. 누군가 manifest 를 지우거나 이름을 바꾸면 silent 한 D2 fallback 대신 즉시 실패.

> **v0.7.4 (2026-05-20) 변경점**: standalone shell × per-domain 1-pass 통합 + 통합 시나리오 정비.
> - Growth-16~19 가 묶여 단일 명령(`scaffold_cli --shell-mode MDI --dialect <hsqldb|postgres|mysql>`) 으로 빌드 가능한 nexacro+Spring Boot WAR 트리가 만들어지는 흐름 완성. 더 이상 `/nexacro-fullstack-starter` 외부 plugin 의존이 필수가 아님.
> - Growth-19: seed `display` → blueprint `label_ko` → frameLeft `ds_menu` 한국어 라벨 보존 체인. shell-mode 의 menu skip 은 `menu_skipped` 첫 클래스 필드로 명시화 (silent fallback 아님). typedef_merger 1-pass 가 `<Service prefixid="svc">`(shell) + `<Service prefixid="<domain>">`(per-domain) 둘 다 한 파일에 보존.
> - 신규 §2.7 (권장 통합 경로) + §3.10 (Growth-16~19 통합 시나리오 매트릭스).
> - 하위 호환 100% — shell-mode/`label_ko` 모두 선택 플래그/필드. 상세: [`docs/superpowers/specs/2026-05-15-karpathy-alignment-review.md`](./superpowers/specs/2026-05-15-karpathy-alignment-review.md)

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

> **Tip (Growth-51):** 어떤 도메인 preset 이 있는지 모르겠으면 먼저 `/list-domains` 슬래시 커맨드로 14개 카탈로그를 확인하세요. 신규 도메인이면 자유 입력으로 진행해도 됩니다 — Stage 1 ingest 가 새 도메인을 학습합니다. 상세: §3.13.

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

### 2.7 권장 통합 경로 — Standalone shell (Growth-16~19)

`/nexacro-fullstack-starter` 외부 plugin 없이 **빈 디렉터리 한 개**에서 출발해
`mvn package` 까지 한 번에 가는 권장 경로. Growth-16~19 가 묶여 다음 4 가지가
한 명령으로 보장된다:

| 보장 | 출처 | 검증 위치 |
| :-- | :-- | :-- |
| 한국어 메뉴 라벨 (seed `display` → frameLeft) | Growth-19 | `nxui/packageN/frame/frameLeft.xfdl` 의 `<Col id="label">` |
| dialect 별 application.yml + pom.xml | Growth-18 | `src/main/resources/application.yml`, `pom.xml` |
| Maven 빌드 디스크립터 4종 | Growth-17b | `pom.xml`, `Application.java`, `application.yml`, `NexacroBase.java` |
| typedef 1-pass 병합 (svc + per-domain) | Growth-19 | `nxui/packageN/typedefinition.xml` |

**원클릭 (배송관리 + Postgres + MDI):**

```powershell
python scripts/scaffold_cli.py `
  --domain "배송관리" --wiki-mode preset --preset "배송관리" `
  --package com.example.shipping --service-name Shipping `
  --target-package-prefix com.acme.shipping `
  --dialect postgres --lane nexacro `
  --out .\shipping-scaffold `
  --target-project .\shipping-app `
  --shell-mode MDI `
  --nexacrolib-from D:\nexacro\nexacrolib   # 옵션: 사내 nexacrolib 복사
```

**빌드 + 실행:**
```powershell
cd .\shipping-app
mvn -B -DskipTests package
java -jar .\target\shipping-shell-0.1.0-SNAPSHOT.jar
# → http://localhost:8080/uiadapter/
```

**언제 §2.6 (수동 overlay) 대신 §2.7 을 쓰는가:**
- 신규 프로젝트 0→1 (빈 디렉터리 출발)
- nexacro 패키지명을 직접 통제하고 싶을 때 (`--shell-app-id`)
- 사내 표준 base scaffold 가 없거나 starter plugin 을 도입하기 어려울 때
- dialect 를 hsqldb 외로 바꿀 때 (postgres/mysql) — application.yml + pom.xml 까지 자동 동기

**§2.6 (외부 starter overlay) 가 여전히 적절한 경우:**
- 이미 starter 로 만든 사내 표준 프로젝트 위에 도메인만 얹는 경우
- frameMain/frameLogin 등 frame 5종을 회사 표준으로 별도 관리하는 경우
- 한 프로젝트에 여러 도메인을 누적 overlay 하는 경우 (idempotent 보장)

> 두 경로 모두 같은 4-stage 산출물을 공유한다. 차이는 **frame/typedef/xadl 의 소유권** — §2.7 은 shell adapter, §2.6 은 외부 starter.

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

**Workflow service (Gap 2, v0.5.x):** blueprint entity 가 `workflow:` 블록을 선언하면 위 산출에 더해 `service/<Entity>WorkflowService.java` + `service/impl/<Entity>WorkflowServiceImpl.java` + mapper `update_<entity>_status` / `select_<entity>_by_id` 가 추가 발행됩니다.

```yaml
# blueprint 예시
entities:
  - name: approval_request
    columns: [...]
    workflow:
      status_column: status
      states: [DRAFT, SUBMITTED, IN_PROGRESS, APPROVED, REJECTED, CANCELLED]
      transitions:
        - { action: submit,  from: [DRAFT],                          to: SUBMITTED }
        - { action: approve, from: [IN_PROGRESS],                    to: APPROVED }
        - { action: cancel,  from: [DRAFT, SUBMITTED, IN_PROGRESS],  to: CANCELLED }
```

- 각 `action` 은 service interface 의 `<action>_<entity>(...)` 메서드 + impl 의 `ALLOWED_FROM_<ACTION>` 가드로 emit. 잘못된 from-state 호출 시 `IllegalStateException("cannot \`<action>\` from <state>")`.
- workflow 가 없는 entity 는 일반 CRUD 만 발행 (하위 호환).

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
| `--ui nexacro\|react` | `nexacro` | **v0.5 H4.** Stage 5 UI overlay adapter. `react` 는 `frontend/src/api/*.ts` fetch 모듈 emit |
| `--shell-mode none\|MDI\|SDI` | `none` | **Growth-16.** 비어있는 target 위에 standalone nexacro shell 렌더 (`<target>/nxui/packageN/` 5 frame + typedefinition.xml + packageN.xadl). `none` 은 기존 overlay-only 동작 유지 |
| `--nexacrolib-from <dir>` | — | **Growth-16.** 지정 시 nexacrolib 트리를 `<target>/nxui/nexacrolib/` 로 복사 (shell-mode 와 함께 사용) |
| `--shell-app-id <name>` | `packageN` | **Growth-16.** shell adapter 의 `branding.app_id`. 기본은 `packageN` |

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

### 3.6 Growth-16 — standalone SHELL (`--shell-mode`)

**의도:** `/nexacro-fullstack-starter` 가 없거나 맞지 않는 환경에서도 한 번의 명령으로 **완성된 standalone nexacro 프로젝트**가 떨어지도록 한다. shell adapter 가 frame/typedef/xadl 을 직접 렌더하고, 그 위에 도메인 overlay 를 얹는다.

**언제 쓰는가:**
- 신규 프로젝트 0→1: 빈 디렉터리에 바로 WAR-ready 트리 만들기
- 자체 nexacro 패키지(예: `packageN`)를 가진 사내 표준이 별도로 있을 때
- starter 의존을 끊고 5-repo 만으로 closure 를 유지하고 싶을 때

**원클릭 예시 — 배송관리 SDI:**
```powershell
python scripts/scaffold_cli.py `
  --domain "배송관리" --preset "배송관리" `
  --package com.example.shipping --service-name Shipping `
  --dialect hsqldb `
  --out .\shipping-scaffold `
  --target-project .\shipping-app `
  --shell-mode SDI `
  --nexacrolib-from D:\nexacro\nexacrolib `
  --shell-app-id packageN
```

산출:
```
shipping-app/
├── nxui/
│   ├── packageN/
│   │   ├── frame/  (frameMain, frameSDI, frameLeft, frameTop, frameLogin)
│   │   ├── typedefinition.xml
│   │   ├── packageN.xadl
│   │   └── shipping/  (도메인 xfdl)
│   └── nexacrolib/  (선택: --nexacrolib-from 시 복사)
└── src/main/java/com/nexacro/uiadapter/shipping/  (Java overlay)
```

**Variant — MDI vs SDI:**
| Variant | work_frame | 용도 |
| :-- | :-- | :-- |
| `MDI` | `frameMDI` | 탭 기반 다중 문서 (`openTab`/`closeTab`) |
| `SDI` | `frameSDI` | 단일 문서 교체 — 가벼운 단일 워크플로 |

**Frame 3-tier 우선순위 (per file):**
1. `blueprint.shell.frame_overrides[<name>]` (project-local)
2. `.claude/skills/karpathy-rdb-nexacro/patterns/SHELL/variants/<variant>/<name>.xfdl.j2`
3. `.../variants/MDI/<name>.xfdl.j2` (shared fallback)

→ 새 variant 를 만들 때 한 개 frame 만 차별화하면 나머지는 MDI 가 자동으로 채운다.

**shell↔도메인 overlay 분담:**
- `ds_menu` (frameLeft) — **shell adapter** 가 blueprint entities 로부터 trees row 생성 (권위적 소스)
- `frameLogin.xfdl` 의 `dsSample` — **shell-mode 시 의도적으로 없음**; per-domain overlay 의 menu inject 단계는 자동 soft-warn 으로 skip (`menu_warning` 보고)

**5축 복리 환류:**
- Backend: 없음 (shell 은 frontend 전용)
- Middle: 없음
- Frontend: `patterns/SHELL/` 가 새 pattern kind. 신 variant 추가 시 `variants/<NAME>/` 디렉터리 + manifest 1줄

---

### 3.7 Growth-17 — standalone shell 을 진짜 buildable 프로젝트로

3.6 의 standalone shell 은 **frontend 자산만** 떨어졌다. 실제 `mvn package` 까지 한 번에 가도록 세 가지 보강이 들어갔다.

**Growth-17a — frame filename casing 계약 (Linux WAR 안전):**
- `frame_mdi` 템플릿 키는 항상 `frameMDI.xfdl` 로 렌더 (소문자 `frameMdi` 금지)
- Windows 는 case-insensitive 라 통과하지만, Linux WAR 배포 시 `frameMain.xfdl` 안의 `work_frame="frameMDI"` 참조가 깨진다 — 회귀 테스트로 잠금

**Growth-17b — Maven 빌드 디스크립터 4종 자동 생성:**

SHELL manifest 의 `build:` 섹션이 다음 4 파일을 프로젝트 루트에 렌더한다:

| 파일 | 역할 |
| :-- | :-- |
| `pom.xml` | Spring Boot 3.3.5 + jakarta uiadapter + tobesoft-snapshots Nexus. `nxui/packageN` 을 `static/packageN` 으로 Boot static resource 로 번들. `{{*}}` Maven custom delimiter 로 `BACKEND_URL` 치환 지원 |
| `src/main/java/{pkg_path}/Application.java` | `@SpringBootApplication` + `@MapperScan("{target_pkg_prefix}.{domain_slug}.mapper")` — Stage 3 매퍼 인터페이스가 `@Mapper` annotation 없이 등록되도록 |
| `src/main/resources/application.yml` | HSQLDB in-memory + mybatis `mapper-locations: classpath:mybatis/mapper/**/*.xml` + uiadapter context-path `/uiadapter` |
| `src/main/java/{pkg_path}/{domain_slug}/domain/NexacroBase.java` | Stage 3 nexacro-lane POJO 들이 `extends NexacroBase` (import 없는 same-package 참조) 하므로 **같은 패키지에** 위치해야 한다. `DataSetRowTypeAccessor` 구현 — uiadapter 가 `_RowType_` per row 보존 |

**Growth-17c — `mvn package` 1회 실빌드 스모크:**

배송관리 standalone shell scaffold 위에서 실제 `mvn package` 를 돌려 fat-jar 생성을 검증. 스모크 도중 다음 3개 contract bug 가 발견·수정됨:
1. `NexacroBase.java` 미생성 → 4× `cannot find symbol`
2. `application.yml` `mapper-locations` 가 실제 emit 경로(`mybatis/mapper/`)와 불일치
3. `data-locations: classpath:data.sql` 가 standalone flow 에서 없는 파일을 참조 → Boot 시작 실패

**스모크 명령:**
```powershell
# 0. scaffold (Growth-16 명령 그대로)
python scripts/scaffold_cli.py --domain "배송관리" --preset "배송관리" `
  --package com.acme.shipping --service-name Shipping --dialect hsqldb `
  --out .\shipping-scaffold --target-project .\shipping-app `
  --shell-mode MDI --target-package-prefix com.acme.shipping

# 1. 실빌드
cd .\shipping-app
mvn -B -DskipTests package

# 2. fat-jar 확인 (Spring Boot repackaged)
ls .\target\shipping-shell-*-SNAPSHOT.jar       # ~50 MB
ls .\target\shipping-shell-*-SNAPSHOT.jar.original  # ~40 KB (pre-repackage)

# 3. 실행
java -jar .\target\shipping-shell-0.1.0-SNAPSHOT.jar
# → http://localhost:8080/uiadapter/  (REST + nxui 정적 자원 same-origin)
```

**검증 포인트 (fat-jar 내부):**
```
BOOT-INF/classes/com/acme/shipping/Application.class                       # Boot main
BOOT-INF/classes/com/acme/shipping/shipping/domain/NexacroBase.class       # 컴파일 통과 증거
BOOT-INF/classes/static/packageN/frame/frameMDI.xfdl                       # nxui 번들
```

### 3.8 Growth-18 — `--dialect` 가 standalone shell 까지 흐른다

Growth-17c 까지 standalone shell scaffold 는 `--dialect postgres` 를 줘도
`schema.sql` 만 postgres 방언으로 생성되고 `application.yml` / `pom.xml` 은
HSQLDB 하드코딩이 남아 있었음 (계약 누수). Growth-18 에서 두 contract bug 를
한 번에 닫는다:

**Bug #1 — shell template 이 dialect 를 모름**

- `scripts/nexacro_shell_overlay.py` 에 `_DIALECT_DATASOURCES` registry
  (`hsqldb` / `postgres` / `mysql`) 와 `_resolve_datasource(dialect,
  domain_slug)` 헬퍼 추가. 각 dialect 별 JDBC URL / driver class / 자격증명 /
  init mode / Maven 좌표 (groupId·artifactId·version) 를 한 곳에서 결정
- `_shell_overlay_run(...)` 가 `dialect="hsqldb"` kwarg 를 받아
  `ctx_common` 에 `{{ dialect }}` 와 `{{ datasource }}` 를 노출
- `scripts/scaffold_orchestrator.py` 가 `args.dialect` 를 shell-mode stage5
  overlay 호출에 forward
- nexacro-skill 의 `SHELL/variants/MDI/application.yml.j2` 와 `pom.xml.j2`
  가 하드코딩 대신 `{{ datasource.* }}` 를 렌더. Postgres/MySQL 은 init mode
  `embedded` (Spring 기본값 — Flyway/Liquibase 가 마이그레이션 소유) /
  HSQLDB 는 `always` (in-memory 라 매 부팅마다 schema.sql 안전)
- 미등록 dialect 는 hsqldb 로 fallback (back-compat — 기존 호출부 무변경)

**Bug #2 — Postgres DEFAULT 값 quoting**

- `rdb-ddl/scripts/ddl_gen.py` 에 `_sql_default` Jinja 필터 추가. 리터럴 문자열은
  싱글쿼트로 감싸고 (`'pending'` → `DEFAULT 'pending'`), 함수/예약어
  (`CURRENT_TIMESTAMP`, `now()`, `NULL`, `TRUE`/`FALSE`, 숫자 리터럴) 는
  raw 로 통과. 3개 dialect 템플릿 (`postgres/hsqldb/mysql/tables.sql.j2`)
  이 모두 `| sql_default` 필터를 거치도록 통일
- 11종 단위 테스트 + 3 dialect parametrize E2E 로 회귀 안전망 구성

**스모크 명령 (Postgres):**
```powershell
$env:PYTHONPATH = "D:\AI\workspace\business-fullstack-creater\scripts"
python -m scripts.scaffold_cli `
  --domain "배송관리" --wiki-mode preset --preset "배송관리" `
  --dialect postgres --lane nexacro `
  --package com.example.shipping --target-package-prefix com.acme.shipping `
  --target-project .tmp_smoke_pg/shell --shell-mode MDI `
  --overlay-force --out .tmp_smoke_pg/out
```

**검증 포인트:**
```
application.yml  →  url: jdbc:postgresql://localhost:5432/shipping
                    driver-class-name: org.postgresql.Driver
                    spring.sql.init.mode: embedded
pom.xml          →  <postgresql.version>42.7.4</postgresql.version>
                    <groupId>org.postgresql</groupId>
                    <artifactId>postgresql</artifactId>
schema.sql       →  DEFAULT TRUE / DEFAULT 'pending' / DEFAULT now() / DEFAULT 1
```

> 같은 패턴이 `--dialect mysql` 에도 자동 적용 (mysql-connector-j 8.4.0,
> `com.mysql.cj.jdbc.Driver`). `--dialect` 미지정 시 hsqldb 동작은 v0.7.3
> 과 100% 동일하게 유지된다 (regression 테스트 4종 통과).

---

### 3.9 Growth-19 — Stage 5 × shell 1-pass 통합 (Korean 메뉴 + 명시적 contract)

`--shell-mode MDI|SDI` 와 per-domain overlay 가 한 번의 `scaffold_cli` 실행에서
같은 target 디렉터리로 흘러들어가는 1-pass 통합이 v0.7.4 에서 다음 세 가지를
보장한다.

**1. seed `display` 가 frameLeft 메뉴 라벨까지 보존된다**

Stage 1 blueprint 컴파일러(`rdb_index.py`)가 entity frontmatter 의 `display`
필드를 `_blueprint.yaml` 의 `label_ko` 로 정규화한다. shell 어댑터의
`_derive_menu_items` 가 `e.get("label_ko") or e["name"]` 을 읽기 때문에
`frameLeft.xfdl` 의 `ds_menu` 행에는 한국어 라벨이 그대로 노출된다.

```text
배송관리.seed.md           → entity.display: 배송사
_blueprint.yaml             → entity.label_ko: 배송사
frameLeft.xfdl              → <Col id="label">배송사</Col>
```

선택 필드라 누락 시에는 종전대로 entity name 이 fallback 으로 사용된다
(하위 호환). `version: 1` 유지.

**2. menu 주입은 shell-mode 에서 명시적으로 skip 된다**

`_nexacro_overlay_run` 이 `shell_mode != "none"` 을 인지하면 `frameLogin.xfdl`
의 `dsSample` 주입을 **건너뛰는 것이 정상 계약**이다 (메뉴는 shell 이
`frameLeft.ds_menu` 로 소유). 결과 report 에는 다음과 같이 명시된다.

```python
overlay_report = {
    "menu_skipped": "shell_mode=MDI: menu owned by shell adapter (ds_menu in frameLeft)",
    "menu_warning": None,      # 경고가 아님 — 의도된 분기
    ...
}
```

기존의 `menu_warning` 키는 *예상 외* 의 schema mismatch / dsSample 부재
상황에서만 채워진다.

**3. typedef 가 1-pass 로 병합된다**

shell 패스가 `<Service prefixid="svc" type="module" .../>` 를 emit 한 뒤,
per-domain overlay 의 `typedef_merger` 가 동일 파일에 `<Service
prefixid="shipping" type="form" url="./shipping/" .../>` 를 추가한다.
두 항목이 한 `typedefinition.xml` 에 공존하는지는 회귀 테스트
`tests/golden/test_growth16_shell_e2e.py::test_growth19_one_pass_korean_labels_and_typedef_merge`
가 직접 검증한다.

> 이 세 가지가 깨지면 *동일한 도메인 지식이 두 파이프라인에 흩어졌다는 신호* —
> Karpathy 정렬 리뷰(`docs/superpowers/specs/2026-05-15-karpathy-alignment-review.md`)
> 의 진단표 갭에 해당한다.

---

### 3.10 통합 시나리오 매트릭스 (Growth-16~19)

standalone shell 경로(§2.7)의 **각 보장이 어느 Growth-N 에서 들어왔고 어느
파일이 권위자(authority)인가**를 한 표로 정리. 회귀 발생 시 어느 commit/file
로 거슬러 올라갈지 결정하는 1차 참조.

| 보장 (Contract) | Growth | 권위 파일 (authority) | 검증 위치 (test/path) |
| :-- | :-- | :-- | :-- |
| frame 5종 + xadl + typedef 초기 emit | G-16 P1 | `andrej-karpathy-rdb-nexacro/patterns/SHELL/variants/<MDI\|SDI>/` | `tests/golden/test_growth16_shell_e2e.py::test_standalone_shell_mdi_renders_full_project` |
| Stage 5 adapter registry (`nexacro-shell`) | G-16 P2 | `scripts/nexacro_shell_overlay.py` | 동상 (registry dispatch) |
| `scaffold_cli --shell-mode MDI/SDI` 흐름 | G-16 P3 | `scripts/scaffold_orchestrator.py`, `scripts/scaffold_cli.py` | 동상 |
| `--nexacrolib-from` 도우미 | G-16 P4 | `scripts/nexacro_shell_overlay.py` (`_copy_nexacrolib`) | `tests/golden/test_growth16_shell_e2e.py::test_standalone_shell_with_nexacrolib_copy` |
| frame casing (Linux WAR 안전) | G-17a | `patterns/SHELL/variants/MDI/manifest.yaml` (`frameMDI.xfdl`) | nexacro-rdb regression test |
| Maven 빌드 디스크립터 4종 emit | G-17b | `patterns/SHELL/variants/MDI/{pom.xml,Application.java,application.yml,NexacroBase.java}.j2` | scaffold-report stage5 ok + `mvn package` 그린 |
| `mvn package` 1회 실빌드 안전망 | G-17c | `docs/USER-GUIDE.md §3.7` (절차) | (수동 스모크) |
| dialect→application.yml/pom.xml 흐름 | G-18 | `_DIALECT_DATASOURCES` in `nexacro_shell_overlay.py` | rdb-ddl `tests/test_sql_default.py` + creater dialect smoke |
| Postgres `DEFAULT` 값 quoting | G-18 | `rdb-ddl/scripts/ddl_gen.py::_sql_default` | rdb-ddl `tests/test_sql_default.py` |
| seed `display` → blueprint `label_ko` | G-19 | `rdb-skill/scripts/rdb_index.py` (entity emit loop) | rdb-skill `tests/test_blueprint_spec.py` |
| frameLeft `ds_menu` 한국어 라벨 | G-19 | `nexacro_shell_overlay.py::_derive_menu_items` | `test_growth19_one_pass_korean_labels_and_typedef_merge` |
| shell-mode 시 dsSample 주입 의도적 skip | G-19 | `scripts/stage5_overlay.py` (`menu_skipped` 필드) | 동상 |
| `<Service prefixid="svc">` + `<Service prefixid="<domain>">` 공존 | G-19 | `scripts/typedef_merger.py` (1-pass merge) | 동상 |

**복리식 환류 (3축 매핑):**
- **Backend (Stage 2 catalog/dialect)**: G-18 (dialect adapter), G-18 (`_sql_default` 필터)
- **Middle (Stage 3 lane templates)**: 직접 변경 없음 — shell-mode 가 middle 산출물을 그대로 소비
- **Frontend (Stage 4/5 patterns + overlay)**: G-16 (SHELL pattern), G-17 (빌드 descriptor 4종), G-19 (shell↔per-domain 분담 계약)

> 새 도메인(Growth-21 후보 — CRM/공급망/회계)을 추가할 때는 이 표가 **회귀 체크리스트**로 동작한다.
> 각 칸의 *권위 파일* 변경 없이 도메인이 추가되면, 그 도메인은 자동으로 위 13개 보장을 모두 얻는다.

---

### 3.11 Growth-27 — HSQLDB IDENTITY 0-base 트랩 (smoke-test 컨벤션)

**발견 경위 (2026-05-21):** 재무관리 v5 생성 산출물(`schema.sql`)을 HSQLDB
인메모리 DB에 실제로 실행해본 첫 user-level 검증(`.tmp_e2e_finance/FinanceSmoke.java`)에서 다음 에러가 발생.

```
SQL FAIL: INSERT INTO journal_entry (..., fiscal_period_id, ...) VALUES (..., 1, ...)
  -> integrity constraint violation: foreign key no parent;
     FK_JOURNAL_ENTRY__FISCAL_PERIOD_ID table: JOURNAL_ENTRY value: 1
```

**근본 원인:** HSQLDB `BIGINT GENERATED BY DEFAULT AS IDENTITY` 의 시작값은
**`0`** 이다 (PostgreSQL `BIGSERIAL` 은 `1`). 따라서 첫 row 의 `id` 는 `1` 이
아니라 `0` — `fiscal_period_id, 1` 같은 하드코딩 FK 는 존재하지 않는 부모를
참조하게 된다.

**환류 (3-axis):**

| 축 | 위치 | 변경 |
|---|---|---|
| **Backend dialect** | `andrej-karpathy-rdb-ddl/scripts/dialect.py` | `HSQLDB` 정의 직상단 코멘트 — 0-base 시작 + `RETURN_GENERATED_KEYS` 권장 |
| **Backend spec** | `andrej-karpathy-rdb-ddl/.claude/skills/karpathy-rdb-ddl/references/ddl-spec.md` | `## Dialect quirks — smoke-test guidance` 섹션 신설 (JDBC 예시 포함) |
| **Seed verified** | `andrej-karpathy-rdb-skill/.claude/skills/karpathy-rdb/presets/재무관리.seed.md` v5 | `## verified (실 DB 검증 — Growth-26 E2E)` 블록 — Schema apply / Double-entry invariant / CASCADE / RESTRICT 4가지 보증 |

**컨벤션 (모든 JDBC 스모크 하니스):**

```java
// 부모 row INSERT 후 자동 키 캡처
try (PreparedStatement ps = c.prepareStatement(
        "INSERT INTO fiscal_period (year, month) VALUES (2026, 5)",
        Statement.RETURN_GENERATED_KEYS)) {
    ps.executeUpdate();
    try (ResultSet rs = ps.getGeneratedKeys()) { rs.next(); fpId = rs.getLong(1); }
}
// 자식 row INSERT 는 ? placeholder 로 fpId 바인딩 — 절대 하드코딩 금지
ps.setLong(1, fpId);
```

> 이 트랩은 PostgreSQL/MySQL 에서는 IDENTITY 시작값이 `1` 이라 우연히 가려진다.
> **HSQLDB 만 노출시키는 latent bug** — 그래서 in-memory dialect 가 한 번이라도
> 실제로 돌면 잡힌다. `--dialect hsqldb` 가 단순 in-memory 테스트용이 아니라
> **dialect contract 의 시금석** 역할을 한다는 운영적 의미가 추가로 확보됐다.

**참조 하니스:** `.tmp_e2e_finance/FinanceSmoke.java` — 6-step 검증
(schema apply / seed / journal post / double-entry invariant / CASCADE / RESTRICT)
전체 그린. 다음 도메인에서 비슷한 검증이 필요하면 이 파일이 출발점.

---

### 3.12 Growth-28 — 라이브 WAS 스모크 (`boot-jdk17-jakarta` runner 오버레이)

**목적:** Stage 3 산출물(controller/service/mapper) 이 **실제 Spring Boot WAS 위에서** Nexacro envelope 으로 호출됐을 때 `200 OK` + `output1` dataset 을 돌려주는지 한 번이라도 확인한다. JDBC-수준 스모크(§3.11)는 schema/seed 까지만 보장하므로, lane(`jakarta`) × MyBatis × NexacroResult 직렬화 stack 전체는 별도 검증이 필요하다.

**대상 runner:** `D:\AI\workspace\nexacroN-fullstack\samples\runners\boot-jdk17-jakarta` (Spring Boot 3.3.5 + JDK 17 + MyBatis-Spring-Boot 3.0.3 + HSQLDB 2.7.3)

**원리 — in-place overlay + git restore:** runner 레포를 **영구히** 수정하지 않는다. 오버레이 → 빌드 → 호출 → 확인 → `git restore` 로 원복. 이 절차로 runner 가 "검증대"로 재사용 가능 + nexacroN-fullstack 쪽 히스토리 오염 없음.

**5 가지 오버레이 포인트** (재무관리 v5 예시):

| # | 위치 | 변경 |
|---|---|---|
| 1 | `Application.java` | `scanBasePackages = {"com.nexacro.uiadapter", "com.example.finance"}` + `@MapperScan(basePackages = {"com.nexacro.uiadapter.mapper", "com.example.finance.mapper"})` — 도메인 mapper 인터페이스가 per-interface `@Mapper` 를 안 달기 때문에 클래스-레벨 스캔 필수 |
| 2 | `src/main/resources/application.yml` | `schema-locations: classpath:schema.sql,classpath:finance-schema.sql` + `data-locations: classpath:data.sql,classpath:finance-data.sql` (콤마 누적) |
| 3 | `src/main/resources/finance-schema.sql` (신규) | Stage 2 산출 `schema.sql` 의 `;` → **`^^`** 치환. runner 의 `spring.sql.init.separator: "^^"` 컨벤션에 맞춤 |
| 4 | `src/main/resources/finance-data.sql` (신규) | 최소 2 row seed (account 2건 + fiscal_period 1건). `;` → `^^` 동일 |
| 5 | `src/main/resources/mybatis/mappers/{account,fiscalperiod,journalentry,ledgerentry}-mapper.xml` | Stage 3 PascalCase `AccountMapper.xml` → kebab-case `account-mapper.xml` (runner glob `*-mapper.xml` 매칭) |

**자바 소스 + 매퍼 XML 본체:** `src/main/java/com/example/finance/**` 17 파일 + 4 mapper XML 을 그대로 복사 (rename 만 필요).

**WAS 기동 — JDK 17 명시 (PATH 가 JDK 21 이어도 안전):**

```powershell
Start-Process -FilePath "C:\Program Files\Java\jdk-17\bin\java.exe" `
  -ArgumentList "-jar","<runner>\target\runner-boot-jdk17-jakarta-0.1.0-SNAPSHOT.jar" `
  -RedirectStandardOutput was.log -RedirectStandardError was.err -PassThru
# 기동 신호: "Started Application in N.NNN seconds"
```

**호출 — Nexacro envelope:**

```powershell
$body = @'
<?xml version="1.0" encoding="UTF-8"?>
<Root xmlns="http://www.nexacroplatform.com/platform/dataset">
<Parameters></Parameters>
<Dataset id="dsSearch"><ColumnInfo><Column id="searchKeyword" type="STRING" size="100"/></ColumnInfo><Rows><Row><Col id="searchKeyword"></Col></Row></Rows></Dataset>
</Root>
'@
Invoke-WebRequest -Uri "http://localhost:8080/uiadapter/account/select_datalist_map.do" `
  -Method POST -ContentType "application/xml" -Body $body -UseBasicParsing
```

**검증된 응답 (2026-05-21):**

```xml
<Parameters><Parameter id="ErrorCode" type="int">0</Parameter></Parameters>
<Dataset id="output1">
  <ColumnInfo>... CODE, ID, TYPE, NAME ...</ColumnInfo>
  <Rows>
    <Row><Col id="CODE">1000</Col><Col id="ID">0</Col><Col id="TYPE">asset</Col>...</Row>
    <Row><Col id="CODE">4000</Col><Col id="ID">1</Col><Col id="TYPE">revenue</Col>...</Row>
  </Rows>
</Dataset>
```

HTTP **200 OK**, `ErrorCode=0`, 2 행. **첫 행 `ID=0`** — §3.11 의 HSQLDB IDENTITY 0-base 트랩이 **JDBC 수준이 아닌 컨테이너 응답에서도 동일 재현**된다. dialect 환류가 schema 만이 아니라 응답 payload 까지 영향을 미친다는 증거.

**원복 (반드시 3단계 모두 수행):**

```powershell
# 1) WAS 정지 — 누락 시 :8080 leak 으로 다음 검증 실패
Get-Process java -EA SilentlyContinue | Where-Object { $_.Path -like "*jdk-17*" } | Stop-Process -Force

# 2) 추적 파일 원복
git -C D:\AI\workspace\nexacroN-fullstack restore samples/runners/boot-jdk17-jakarta/src/main/java/com/nexacro/uiadapter/Application.java
git -C D:\AI\workspace\nexacroN-fullstack restore samples/runners/boot-jdk17-jakarta/src/main/resources/application.yml

# 3) 오버레이로 신규 생성한 파일 제거
Remove-Item -Recurse -Force samples\runners\boot-jdk17-jakarta\src\main\java\com\example
Remove-Item -Force samples\...\finance-schema.sql, finance-data.sql, mybatis\mappers\{account,...}-mapper.xml

# 검증: 다음 명령이 empty 출력이어야 한다
git -C D:\AI\workspace\nexacroN-fullstack status --short samples/runners/boot-jdk17-jakarta/
```

**판정 기준 (4계층 중 layer 4):**
- ✅ PASS: HTTP 200 + `ErrorCode=0` + 기대 dataset 행수 일치 + 기대 컬럼 모두 존재
- ⚠️ 부분검증: WAS 는 떴지만 위 4 조건 중 하나라도 미달 — "라이브 WAS 부분검증" 라벨
- ❌ FAIL: WAS 기동 실패 / 5xx / 응답 dataset 미존재

**언제 이 절차를 다시 쓰나:**
- 새 도메인 산출물의 **응답 직렬화** 가 의심될 때 (Map vs DataSet, 한글 컬럼명, BigDecimal 등)
- 새 lane(`vanilla`/`javax`) 어댑터가 NexacroResult 와 호환되는지 첫 검증할 때
- `@MapperScan` / `scanBasePackages` 외에 또 다른 오버레이 지점이 생기면 위 표에 한 줄 추가

> **컨벤션:** runner 레포는 "원본 read-only + 오버레이 후 즉시 원복" 원칙으로만 만진다. 영구 변경이 필요하면 그건 runner 자체 PR 사안 — 이 절차의 범위 밖.

**자동화 (Growth-35):** 위 5포인트 overlay + 빌드 + 기동 + 호출 + 정지 + git restore 전체가 `/full-test <lane> [domain]` 의 L4 단계로 자동화돼 있다. 모듈 분리:
- `scripts/workflow/live_overlay.py` — 5-point overlay (idempotent)
- `scripts/workflow/live_runner.py` — fat-jar 기동 + `Started Application in N.NNN seconds` ready-poll (timeout 180s)
- `scripts/workflow/live_probe.py` — nexacro envelope POST + `200 OK + ErrorCode=0 + row_count>=1` 판정 (timeout 30s)
- `scripts/workflow/full_test.run_l4_live` — 위 3 모듈 + `_mvn_rebuild_runner` orchestration. 라벨링 (full/partial/fail) 은 §3.12 판정 기준과 동일.

**전제 컨벤션 (자동화 작동 조건):** scaffold 디렉터리 이름 = Java sub-package 식별자(`finance`, `sales` 등 ASCII slug). 디폴트 lane→runner 매핑은 `scripts/workflow/lane_runner_map.py` 단일 출처.

**자동화 보강 이력 (Growth-36 ~ 38):** Growth-35 베이스 위에 누적된 견고성·일반화 개선. 이전 절차 변경 없이 더 많은 scaffold/lane 모양을 흡수한다.

| Growth | 영역 | 변경 |
|---|---|---|
| Growth-36 | L4 lane-aware | (1) `live_overlay.discover_scaffold` — Stage 3 실 출력(`com.nexacro.uiadapter.<slug>.*` / `3-mybatis/src/main/resources/{schema,data}.sql` / `mybatis/mapper/`) **및** legacy fixture(`com.example.<slug>` / `2-ddl/` / `mybatis/mappers/`) 양쪽 자동 도출. (2) `lane_runner_map.lane_probe_kind/url` 신설 — `nexacro` 는 `POST /uiadapter/<entity>/select_datalist_map.do` 엔벨로프 / `jakarta·javax·vanilla` 는 `GET /api/<entity>` JSON. `run_l4_live` 가 lane 별 `probe_endpoint` vs `probe_endpoint_json` 자동 선택. (3) `derive_entity_slug` kebab/PascalCase 양형 지원. |
| Growth-37 | L1 + L2 실구현 | (1) L2 가 placeholder 였던 것을 실제 JDBC smoke 로 교체 — `_jdbc_smoke.java` (JDK 11+ single-file source-mode, HSQLDB in-mem, `^^` separator) + `jdbc_smoke.py` 래퍼. `HSQLDB_JAR` env 미설정·jar 부재 시 `skipped=True` 로 L3/L4 비차단. `discover_sql` 은 Stage 3 우선 → `2-ddl/` fallback. (2) L1 silent-pass guard — sibling repo 0 개 실행 시 silent True 대신 False (worktree/sandbox 갭 노출). |
| Growth-38 | L3 + L4 견고성 | (1) `_find_pom` 헬퍼 — 탐색 순서 `5-overlay/pom.xml` → `3-mybatis/pom.xml` → root `pom.xml`. Stage 3-only scaffold(오버레이 미실행)도 빌드 가능. (2) `live_probe.probe_endpoint(_json)` 에 `retries`/`retry_delay_sec` 파라미터 — urlopen 예외(connection refused/timeout)에만 재시도, `HTTPError` 는 즉시 surface(실응답이므로 재시도하면 안 됨). ready-poll 직후 바인드 지연으로 거부 한두 번 발생하는 케이스 자동 흡수. (3) lane pre-validation — `run()` 진입부에서 `resolve_runner(lane)` 호출, 잘못된 lane 인자는 L1/L2/L3 낭비 없이 즉시 `ValueError`. |

**L1~L4 동작 요약 (보강 후):**

| 계층 | 모듈 | 정상 | 스킵 가능 조건 |
|---|---|---|---|
| L1 pytest | `run_l1_pytest` | 4 sibling repo 각각 `pytest -q` → all-green | repo 0 개 실행 시 **FAIL** (silent pass 금지) |
| L2 JDBC smoke | `jdbc_smoke.run_smoke` | schema + data 적용 + 옵션 invariant | `HSQLDB_JAR` env 미설정 / jar 부재 → **SKIP (PASS)** |
| L3 Maven build | `run_l3_mvn` | `_find_pom` 발견 후 `mvn -q package -DskipTests` | pom 부재 시 **FAIL** (3-mybatis/5-overlay/root 모두 부재) |
| L4 live WAS | `run_l4_live` | overlay → mvn rebuild → start → ready-poll → lane-aware probe → stop | lane × runner 매핑 부재 시 **`run()` 진입 즉시 ValueError** (L1~L3 낭비 안 함) |

**검증 이력 (도메인 × lane × runner):**

| 일자 | Growth | 도메인 | lane | runner | 결과 | 비고 |
|---|---|---|---|---|---|---|
| 2026-05-21 | Growth-28 | 재무관리 (finance) | nexacro (jakarta-for-nexacro) | boot-jdk17-jakarta | ✅ 200 OK · ErrorCode=0 · 2행 · 첫행 ID=0 | `/uiadapter/account/select_datalist_map.do` |
| 2026-05-21 | Growth-31 | 영업관리 (sales/CRM) | nexacro (jakarta-for-nexacro) | boot-jdk17-jakarta | ✅ 200 OK · ErrorCode=0 · 2행 · 첫행 ID=0 | `/uiadapter/lead/select_datalist_map.do` · 예약어 `LEAD` 인용 필요 · IDENTITY 0-base 트랩이 seed FK(`sales_activity.opportunity_id`) 에 재발 → seed 를 `0,1` 로 정정 후 통과 |
| 2026-05-21 | Growth-32 | 영업관리 (sales/CRM) | javax (vanilla REST + javax imports) | boot-jdk8-javax (Spring Boot 2.7, JAVA_HOME=JDK17/target=1.8) | ✅ 200 OK · 3행 · id=1,2,3 (explicit-id MERGE 패턴) | `/uiadapter/api/lead` · `/uiadapter/api/opportunity` (FK 정상) · seed `MERGE ... VALUES(id,...)` 로 IDENTITY 우회 → 0-base 트랩 회피 · Stage 3 javax 템플릿 4건 버그 발견(아래 §3.12 부록 참조) |

**Growth-31 추가 발견 (이 절차의 일반화 가치):**
- 절차 자체가 **재무관리 외 도메인**에서도 그대로 작동 — overlay 5포인트 표 (Application.java / application.yml / `<domain>-schema.sql` / `<domain>-data.sql` / mapper XML rename) 가 도메인-agnostic 임이 입증됨
- HSQLDB IDENTITY 0-base 트랩이 **intra-domain FK seed** 에서도 동일하게 재현 — `seed-conventions.md` 의 "first-row id=0" 주의가 cross-FK 가 아닌 도메인 내부에서도 필수
- SQL:2008 예약어(`LEAD`)는 quoted identifier(`"LEAD"`) 로 schema · seed · mapper SQL 3 곳 모두 동시 수정 필요 — Stage 2 DDL 생성기가 자동 인용해 주므로 overlay 시점에는 schema/data 만 손대면 됨 (mapper 는 그대로 통과)

**Growth-32 추가 발견 (javax lane 첫 라이브 검증 — 코드 생성 버그 4건):**

오버레이 시점에 손으로 패치하여 통과시켰으나, **상류(Stage 2/3 템플릿)에 반드시 환류해야 할 결함**:

| # | 단계 | 결함 | 회피책 (overlay 시점) | 환류 위치 |
|---|---|---|---|---|
| 1 | Stage 2 seed | `MERGE` 의 `ON` 절이 `s.id` 를 참조하지만 `s` 튜플에 `id` 컬럼 누락 — HSQLDB 파서 에러 + IDENTITY 0-base 트랩 재발 | `VALUES(...)` 에 명시적 `id` 포함 + `AS s(id, ...)` 컬럼 추가 | `andrej-karpathy-rdb-ddl` seed 템플릿 — explicit-id MERGE 패턴을 기본화 |
| 2 | Stage 3 domain | `com.example.<domain>.domain.*` 에 `javax.persistence.@Id/@Column/@Transient` 어노테이션 부착 → JPA 의존성 없는 runner 에서 컴파일 실패. 또한 Map-based mapper 가 직접 소비하므로 **사용처 없음** | overlay 시 domain 디렉터리 통째로 삭제 | `andrej-karpathy-rdb-mybatis` javax lane 템플릿 — Map-only consumer 일 때 domain 생성 스킵하거나 어노테이션 제거 |
| 3 | Stage 3 service iface | `select_*(Map<String,String>)`, `void save_*(...)` — impl 은 `Map<String,Object>` + `int` 반환 → 인터페이스 불일치 컴파일 실패 | regex 패치: `Map<String, String>` → `Map<String, Object>`, `void (save_\w+_datalist_map)\(` → `int $1(` | `service-interface.javax.java.j2` — impl 시그니처와 동기화 |
| 4 | Stage 3 mapper iface | `void insert/update/delete (Map<String,Object>)` — ServiceImpl 은 `n += mapper.insert_*(row)` → `int + void` 컴파일 실패 | regex 패치: `void (insert_\w+\|update_\w+\|delete_\w+)\(` → `int $1(` | `mapper-interface.javax.java.j2` — CRUD 반환형 `int` 통일 |

**lane 일반화 시사점:**
- javax lane URL 컨벤션은 `/api/<entity>` (REST) 이지 `/uiadapter/<entity>/<method>.do` (NexacroResult) 가 아님 — 검증 endpoint 호출 시 lane 별 path 형태 차이를 반드시 확인
- javax lane 산출물도 `Map<String,Object>` payload 직렬화로 endpoint 응답이 잘 도는지 확인하는 단계가 추가로 필요 (NexacroResult 가 가려주던 Map ↔ JSON 직렬화 책임이 Jackson 으로 이관됨)
- JDK 8 source/target 컴파일은 JDK 17 JAVA_HOME 으로도 가능 — pom.xml 의 `<source>1.8</source><target>1.8</target>` 이 진실 (사용자 환경에 JDK 8 부재 시 우회로)

### 3.13 Growth-51 — 외부 사용자 첫인상 보강 (R1/R3/R4 service review)

서비스 관점 리뷰에서 발견된 "신규 사용자가 첫 도메인을 등록·검증할 때 막히는 3 지점" 을 보강한다. 모두 명령·CLI 의 1차 표면에 추가되어, 별도 문서 학습 없이 즉시 도달 가능.

#### 3.13.1 `--slug` 명시 옵션 + 침묵 폴백 제거 (R1)

`scripts/scaffold_cli.py` 의 `resolve_slug()` 가 3-단계 우선순위로 슬러그를 결정한다:

| 우선순위 | 소스 | 동작 |
|---|---|---|
| 1 | `--slug <name>` (명시) | sanitize 후 사용. 빈 결과 → 에러 |
| 2 | `--domain <한글/ASCII>` 에서 유도 | 영문/숫자 추출. 비어있으면 다음 |
| 3 | `--package` 마지막 세그먼트 | sanitize 후 사용. stderr `INFO: slug = '<X>' (source: package-fallback)` |

기존 침묵 폴백(`'고객관리' → 'domain'` 같은 식별 불가 결과) 이 사라졌다. 한글 domain 만 주고 package 도 없으면 명시 에러(`cannot derive slug from domain=...`) 로 중단된다.

```powershell
# 권장: explicit slug
python scripts/scaffold_cli.py --domain 고객관리 --slug customer --package com.example.customer
# OK: package-fallback (stderr 에 INFO 노출됨)
python scripts/scaffold_cli.py --domain 고객관리 --package com.example.customer
```

#### 3.13.2 `/full-test` recovery hint (R3)

`scripts/workflow/full_test.py` 가 L1~L4 중 첫 실패 계층에 대해 **다음 한 줄 명령** 을 출력한다. JSON output 의 `recovery_hint` 필드 + 사람용 stdout 양쪽에 노출.

| 실패 계층 | 권장 다음 명령 |
|---|---|
| L1 (pytest) | `pytest -q` (실패 sibling repo 에서 `-v` 로 재실행) |
| L2 (JDBC smoke) | `set HSQLDB_JAR=<path>` 확인 후 `python scripts/workflow/jdbc_smoke.py` |
| L3 (mvn package) | `mvn -X package -DskipTests` in `<scaffold>` |
| L4_full=false | `Get-Content <runner>/was.log -Tail 60` |
| L4_partial=true, _full=false | probe URL 직접 호출 (context-path `/uiadapter` 포함) |

```powershell
python scripts/workflow/full_test.py nexacro customer
# (실패 시 마지막 줄)
# Next: mvn -X package -DskipTests in `D:\AI\workspace\customer-mgmt\stage5-overlay`
```

#### 3.13.3 `/list-domains` — preset 카탈로그 노출 (R4)

`scripts/workflow/list_domains.py` + `/list-domains` 슬래시 커맨드가 `andrej-karpathy-rdb-skill` 의 `presets/INDEX.md` 14 도메인을 표/JSON 으로 노출한다. 사용자가 Stage 1 `init --preset <X>` 를 입력하기 전 어떤 도메인이 준비되어 있는지 즉시 확인할 수 있다.

```powershell
# 표 형식
python scripts/workflow/list_domains.py
# JSON (스크립트 입력용)
python scripts/workflow/list_domains.py --json | jq '.[].name'
# 도메인 1건 상세
python scripts/workflow/list_domains.py --verbose --name 고객관리
```

> **환류 게이트**: 새 preset 추가 시 `INDEX.md` 의 4 필드(aliases/keywords/entities/한 줄 요약) 누락 = `/list-domains` 에서 누락 = 외부 사용자 미발견. `/contribute-back` 의 R4 self-check 가 이 정합성을 매 Growth 끝에서 점검한다.

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
| `nxui/packageN/<slug>/Export.xjs` | **Growth-8 (RO 패턴 한정).** blueprint 에 하나라도 `pattern: RO` 엔티티가 있으면 `fn_export_dataset(ds, name)` 헬퍼 (`Dataset.saveCSV` 기반) 를 발행. RO `form.xfdl.j2` 가 `this.parent.fn_export_dataset(...)` 를 호출하므로 사용자는 발행된 `Export.xjs` 를 typedefinition `<Scripts>` 에 등록하고 parent frame 에서 include 하면 끝 (one-time). `report["nexacro_export_emitted"]` 가 발행 경로를 노출 |
| `frontend/src/api/<entity>.ts` (lane=react) | **Growth-8.** 각 entity 모듈에 `exportToCsv(params?, filename?)` 도 함께 emit (RO 패턴 외 entity 에서도 호출 가능). `selectDataListMap()` 결과를 Blob+`a.download` 로 즉시 다운로드. `report["react_export_csv_added"]` 가 emit 된 entity 목록을 노출 |
| `frontend/src/pages/<entity>/<Pascal><Suffix>Page.tsx` (lane=react) | **Gap 3 + Gap 5.** entity 의 `pattern` 에 따라 7종 페이지 컴포넌트 emit: `D2Page` (편집 grid + Search/Save), `F1Page` (단일 record form), `C1Page` (선택 가능 card grid + `onPick`), `L2Page` (list+detail 2-pane), `MDPage` (master-detail child grid), `TRPage` (tree), `ROPage` (read-only + `exportToCsv()`). RO 는 `saveDataListMap` 호출 없이 read-only 불변식 유지. 충돌 시 `--overlay-force` 없으면 fail-fast |

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
| 4 | **v0.5** | 어댑터화 (#2): contract + MySQL + lane 정식화 | v0.4 + 실사용 1회 | 3-4주 | 🔄 진행 중 (H1 완료 2026-05-19, H2-H4 대기) |
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
- **어댑터 계약 먼저, 어댑터 두 번째.** tier마다 contract 문서 (`adapters/backend-contract.md`, `service-contract.md`, `ui-contract.md`) 선행. 입력·출력·파일 위치·호환 버전 명시. → **✅ H1 완료 (2026-05-19)**: [adapters/](../adapters/README.md) 3 contract + 인덱스.
- **back-end DB**: PostgreSQL + HSQLDB 두 어댑터를 contract로 추상화 → MySQL 추가로 일반화 검증. → **H2 대기**
- **middle service**: Stage 3 `--lane jakarta|javax|vanilla` 정식화 (v0.3의 vanilla lane을 contract 기반으로 정리). → **H3 대기**
- **front-end UI**: Stage 4(nexacro) + Stage 4'(외부 starter) 외에 React/Vue 어댑터 슬롯 정의. → **H4 대기**

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

*Last updated: 2026-05-20 — Growth-16: standalone SHELL pattern (`--shell-mode none|MDI|SDI` + `--nexacrolib-from` + `--shell-app-id`) — starter 없이도 단일 명령으로 WAR-ready 트리 산출. MDI/SDI variant 3-tier frame fallback, ds_menu 권위적 소스 이전. 이전: Gap 2~6 (workflow service template · React overlay 7-pattern parity · V002 validator FK side · pattern resolver freeze), Growth-8 (`fn_export_dataset`), v0.5 H1 어댑터 contract, v0.4.2 (`--target-package-prefix`), Phase F (Stage 5 자동 overlay), Phase E (HSQLDB / data.sql / 단일 Service).*
