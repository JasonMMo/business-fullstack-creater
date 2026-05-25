# learn-log.md — business-fullstack-creater

> **역할 분리** (G5, 2026-05-21): CLAUDE.md는 "변하지 않는 원칙·절차", 이 파일은 "매 Growth마다 누적되는 활동 원장(ledger)". 새로 배운 도메인·구현 패턴·dialect 트랩·검증 결과를 1줄 단위로 환류한다.

**기록 컨벤션 (CLAUDE.md §작업시체크리스트 3번 항목 구체화):**

```
YYYY-MM-DD | Growth-N | <kind> | <name> | <domain/lane/dialect> | <한줄요약>
```

`<kind>` 카테고리:
- `domain` — 새 도메인 preset 추가/확장
- `entity` — 신규 entity·관계
- `pattern` — frontend pattern (D2/F1/C1/L2/MD/TR/RO/SHELL...)
- `lane` — backend lane 추가/확장 (vanilla/javax/jakarta/nexacro)
- `dialect` — dialect 어댑터 (postgres/hsqldb/mysql) 트랩 또는 확장
- `overlay` — UI overlay (nexacro/react) 패턴
- `validation` — 라이브 WAS·JDBC·Maven 검증 이정표
- `bug` — 발견된 codegen/template 결함 (환류 task ID 동봉)
- `convention` — 패턴화 결정 (seed 작성법, FK seed id, MERGE explicit-id ...)

---

## 0. Layer Ownership Card (Phase A — 2026-05-22)

5축 책임표의 활동 뷰. CLAUDE.md §핵심 운영 원칙 표가 "변하지 않는 책임", 이 표는 "현재 누적 상태"다. Growth 마다 트랩 카운트와 미해결 환류를 갱신한다.

| 축 | 깊이 누적 위치 | 단위 테스트 디렉토리 | 누적 트랩 | 미해결 환류 |
|---|---|---|---|---|
| **skill (Stage 1)** | `andrej-karpathy-rdb-skill/.claude/skills/karpathy-rdb/presets/*.seed.md` + `protocols/` + `scripts/meta_extract.py`(v0.6 C-1) + `presets/INDEX.md` 3단계 fallback(v0.6 C-2) | `andrej-karpathy-rdb-skill/tests/` (194 그린) | 0 | — |
| **ddl (Stage 2)** | `andrej-karpathy-rdb-ddl/catalogs/preset-catalog.yaml`, dialect 어댑터(postgres/hsqldb/mysql) | `andrej-karpathy-rdb-ddl/tests/` | 3 (HSQLDB IDENTITY 0-base, SQL:2008 `LEAD`, HSQLDB vs postgres-default schema) | — |
| **mybatis (Stage 3)** | `andrej-karpathy-rdb-mybatis/templates/<lane>/`, lane(nexacro/vanilla/jakarta/javax) | `andrej-karpathy-rdb-mybatis/tests/` | 7 (explicit-id MERGE, `@Mapper` bean, typed seed sentinel, REST snake_case URL, Map placeholder case, nexacro `_RowType_` 안전추출, +T-NexacroUiaPkg-javax: nexacro controller/serviceImpl 의 `.jakarta.core.` 하드코딩 → `--uia-namespace` 파라미터) | — |
| **nexacro (Stage 4+5)** | `andrej-karpathy-rdb-nexacro/patterns/`(D2/F1/C1/L2/MD/RO/TR/TG/MT/PS/MDS), UI overlay(nexacro/react) | `andrej-karpathy-rdb-nexacro/tests/` | 0 | — |
| **creater (Orchestrator)** | `business-fullstack-creater/.claude/commands/`(scaffold·full-test·growth-start·contribute-back·cleanup-runner) + `scripts/workflow/`(full_test·live_*·lane_runner_map·learn_log) | `business-fullstack-creater/tests/` | 3 (javax lane URL 컨벤션, JDK8 source/target on JDK17 JAVA_HOME, +T-Probe-LaneRunner-Mismatch RESOLVED Growth-48: scaffold-lane override via `scaffold-report.md` lane line) | `cleanup_runner.py` PowerShell subexpression syntax error (Growth-42 메모, deferred) |

**갱신 규칙:**
- 새 트랩이 §4 에 추가되면 해당 layer 행의 "누적 트랩" 카운트를 +1 하고 한 줄 요약을 괄호 안에 append
- 미해결 환류가 해결되면 그 텍스트만 지움 (행 자체는 유지)
- `/contribute-back` 체크리스트 항목 5번 (Phase A4) 이 이 표의 어느 행에 기여했는지 묻는다

---

## 1. 라이브 WAS 검증대 상태 (lane × runner)

`nexacroN-fullstack/samples/runners/` 매트릭스. CLAUDE.md §풀테스트 4계층 표 4번을 통과한 lane.

| lane | 디폴트 러너 | 검증 상태 | 비고 |
|---|---|---|---|
| **nexacro** | `boot-jdk17-jakarta` (Spring Boot 3.3, jakarta-for-nexacro) | ✅ Growth-42 (customer, envelope CRUD round-trip) | nexacro lane = jakarta runner + uiadapter overlay; envelope `POST /uiadapter/<entity>/save_datalist_map.do` 5-step CRUD 그린 |
| **jakarta** | `boot-jdk17-jakarta` (Spring Boot 3.3) | ✅ Growth-28 (finance) + Growth-31 (sales) | 2 도메인 횡단 검증 완료 |
| **javax** | `boot-jdk8-javax` (Spring Boot 2.7) | ✅ Growth-32 (sales), ✅ Growth-49 (customer fresh scaffold + nexacro lane — **풀테스트 그린** L1+L2+L3-skip+L4-rebuild+probe200/ec=0/rows=3+envelope CRUD baseline=3→+1=4→final=3) | JAVA_HOME=JDK17, target=1.8 (JDK8 부재 시 우회); G-Jackson(Growth-46) + T-NexacroUiaPkg-javax(Growth-47) + T-Probe-LaneRunner-Mismatch(Growth-48) 3개 픽스 누적 후 종단검증 그린 |
| **vanilla** | (직접 러너 없음 — `boot-jdk8-javax` 호스트 임포트) | ✅ Growth-48 (board scaffold — L1+L2+L3 PASS, L4 overlay 26w/2e PASS; L4 mvn rc=1 = boot-repackage가 stale `.jar` 잠금 해제 실패 = 환경성, codegen 결함 아님) | controller 템플릿이 `org.springframework.web.bind.annotation.*` 만 사용 → Spring 5/6 (javax.servlet / jakarta.servlet) 양쪽 러너 호환. "vanilla → javax-host 검증" 라벨로 누적 |

---

## 2. 누적 도메인 카탈로그 (preset-catalog.yaml 동등 뷰)

`andrej-karpathy-rdb-ddl/catalogs/preset-catalog.yaml` 가 진실원천. 여기는 "어떤 Growth에서 추가되었나" 추적.

| 도메인 | preset 파일 | 추가/확장 Growth |
|---|---|---|
| 고객관리 | `고객관리.seed.md` | Growth-1 (customer_category 살붙임) |
| 주문관리 | `주문관리.seed.md` | Growth-2A (order_status_history) |
| 재고관리 | (preset) | Growth-2B (stock_movement) |
| 인사관리 | (preset) | Growth-2C (attendance) |
| 게시판/회원 | `게시판.seed.md` | Growth-2D |
| 배송관리 | (preset) | Growth-15 |
| 권한관리 | (preset) | Growth-9, Growth-21a-1 (oauth_account + refresh_token) |
| 공통코드 | (preset) | Growth-10 |
| 결재 | `결재.seed.md` | Growth-11 |
| 알림 | (preset) | Growth-12 |
| 파일관리 | (preset) | Growth-13 |
| 영업관리 (CRM) | `영업관리.seed.md` | Growth-21b (+1/2/3/4 cross-FK), Growth-31 jakarta 검증, Growth-32 javax 검증 |
| 공급망 (SCM) | (preset) | Growth-22 |
| 재무관리 | `재무관리.seed.md` | Growth-26 (journal_entry double-entry v4), Growth-27 (v5 IDENTITY 트랩), Growth-28 jakarta 검증 |

---

## 3. 누적 패턴 (frontend + lane + dialect + overlay)

| 종류 | 이름 | 추가/검증 Growth |
|---|---|---|
| frontend pattern | D2 (datalist-2-tier) | (초기) |
| frontend pattern | L2 (list-detail) | Growth-3 |
| frontend pattern | MD (master-detail-2-tier) | Growth-4, Growth-5 (compose_form 자동 wiring) |
| frontend pattern | TR (tree-1-tier) | Growth-6 |
| frontend pattern | RO (read-only-list-1-tier) | Growth-7 |
| frontend pattern | F1 / C1 | v0.4 Phase C |
| frontend pattern | SHELL (MDI/SDI) | Growth-16 |
| backend lane | nexacro (jakarta-for-nexacro) | (초기) |
| backend lane | jakarta | v0.5 H3 |
| backend lane | javax | v0.5 H3 + Growth-32 (라이브 검증) |
| backend lane | vanilla | v0.5 H3 |
| dialect | hsqldb | (초기) |
| dialect | postgres | Growth-18 |
| dialect | mysql | v0.5 H2 |
| overlay | nexacro | (초기) |
| overlay | react | v0.5 H4, Growth-24 (OAuth2 로그인 화면) |

---

## 4. dialect / lane 트랩 & 컨벤션

| 항목 | 발견 | 환류 위치 |
|---|---|---|
| **HSQLDB IDENTITY 0-base 트랩** | Growth-27 (재무 v5 E2E), Growth-31 (sales FK 재발) | `seed-conventions.md`, `dialect.py`, USER-GUIDE §3.11 |
| **SQL:2008 예약어 `LEAD`** | Growth-31 | Stage 2 DDL 자동 인용 — overlay 시 schema/data 만 손대면 됨 |
| **explicit-id MERGE 패턴** | Growth-32 | seed의 `MERGE USING (VALUES(...))`에 명시적 `id` 포함하면 IDENTITY 트랩 + `s.id` 참조 누락을 한 번에 회피. Stage 2 seed 템플릿 기본화 대상 (task #240). |
| **javax lane URL 컨벤션** | Growth-32 | `/api/<entity>` (REST). `/uiadapter/<entity>/<method>.do` 는 nexacro lane 한정. |
| **JDK8 source/target on JDK17 JAVA_HOME** | Growth-32 | pom.xml `<source>1.8</source><target>1.8</target>` 가 진실. 사용자 환경에 JDK8 없을 때 우회로. |
| **Spring Boot mapper bean = `@Mapper` 어노테이션 진실원천** | Growth-33 | `boot-jdk8-javax` runner는 `Application.java`에 `@MapperScan` 없음 → MyBatis starter 자동검출이 `@Mapper` per-interface 만 신뢰. 템플릿 (mapper-interface.rest.j2 + mapper-interface.j2) 모두 `@Mapper` 기본 탑재로 환류 (task #246). |
| **타입-aware seed sentinel** | Growth-33 | timestamp/datetime/time 컬럼은 문자열 'TBD' → `CURRENT_TIMESTAMP`/`CURRENT_TIME` 로 자동 치환. dialect-agnostic. (task #245) |
| **REST controller URL = snake_case** | Growth-33 | 생성된 `@RequestMapping` 은 `/api/<table_name>` (snake_case). camelCase 호출은 404. 스모크 테스트 작성 시 주의. |
| **MyBatis Map placeholder case = envelope key case** | Growth-42 | `<Col id="customer_id">` (nexacro envelope snake_case) ↔ `#{customer_id}` 일치 필요. mapper.xml 의 SQL 컬럼은 UPPER 유지(HSQLDB unquoted-normalize 호환), placeholder + `<if test>` key 만 lowercase. case 불일치 = silent INSERT skip (NPE 없음, ErrorCode=0 응답, log에 SQL execute 라인 부재). 환류: mapper.xml.j2 + precompute.py + 테스트 (`rdb-mybatis`). |
| **nexacro service `_RowType_` 안전 추출** | Growth-42 | runner `BoardServiceImpl` 패턴 — `Object raw = row.get(DataSetRowTypeAccessor.NAME); int rowType = (raw instanceof Number) ? ((Number)raw).intValue() : DataSet.ROW_TYPE_NORMAL;` — generated `AddressServiceImpl` 등도 동일 패턴 적용. unsafe `Integer.parseInt((String) row.get(...))` 는 NumberFormatException → 트랜잭션 rollback. 환류: `service-impl.nexacro.java.j2` (`rdb-mybatis`). |
| **HSQLDB schema vs postgres-default scaffold** | Growth-42 | scaffold default dialect=postgres → `BIGINT GENERATED BY DEFAULT AS IDENTITY ... BOOLEAN NOT NULL DEFAULT FALSE` HSQLDB 파싱 실패("unexpected token: DEFAULT"). HSQLDB 검증 시 `--dialect hsqldb` 명시 필요. L2 JDBC smoke 가 dialect mismatch 즉시 노출. |
| **T-NexacroUiaPkg-javax** (nexacro-uiadapter 패키지 변종) | Growth-47 | nexacro-uiadapter 라이브러리는 두 변종: (a) Spring 6 / jakarta.servlet → `com.nexacro.uiadapter.jakarta.core.*` (boot-jdk17-jakarta runner), (b) Spring 5 / javax.servlet → `com.nexacro.uiadapter.spring.core.*` (boot-jdk8-javax runner). 이전엔 mybatis `controller.java.j2` + `service-impl.java.j2` 가 `.jakarta.core.` 하드코딩 → javax runner 빌드 시 `ParamDataSet/NexacroResult/NexacroException/DataSetRowTypeAccessor` symbol-not-found. 환류: `precompute.py`/`codegen.py`/`compile.py` 에 `uia_namespace` 파라미터 추가, 두 템플릿이 `{{ uia_namespace }}.core.*` 사용, `scaffold_cli.py`/`scaffold_orchestrator.py` 가 `--uia-namespace {jakarta|spring}` 노출(기본 jakarta). 회귀: rdb-mybatis 3 신규 테스트(spring variant + jakarta default + invalid value rejection) → 12/12 그린. |
| **T-Probe-LaneRunner-Mismatch** (scaffold lane vs runner deployment conflation) | Growth-47 발견 → **RESOLVED Growth-48** | `lane_runner_map.lane_probe_kind/url/crud_kind/supports_crud` 가 단일 `lane` 인자만 받아 wire protocol(REST vs envelope)을 결정했는데, 그 lane 은 `full_test.py --lane` 인자(러너 선택)와 동일하게 다뤄짐 → nexacro 스캐폴드를 javax runner 위에 올리면 probe 가 `GET /api/{entity}` 호출(실제는 `POST /uiadapter/{entity}/select_datalist_map.do`). **환류** (A안 채택): 4개 dispatcher 에 `scaffold_lane: str \| None = None` optional override 추가 + `_effective_lane()` helper 가 supplied 시 우선. `live_overlay.discover_scaffold_lane(scaffold_dir)` 가 `scaffold-report.md` 의 `- lane: ` `<name>` ` 라인을 regex 로 읽어 반환(파일/라인 부재 시 None — graceful fallback). `full_test.run_l4_live` 가 probe/CRUD dispatch 전 discover 호출 후 4개 dispatcher 모두에 `scaffold_lane=` 전달. 신규 9 테스트(lane_runner_map 5 + discover_scaffold_lane 4 + full_test wiring 2) → 82/82 그린(workflow suite). |

---

## 5. 미해결 환류 항목 (codegen 결함)

발견 시 task를 만들고 여기 1줄로 인덱싱. 해결 시 줄긋고 commit SHA 첨부.

- ~~**task #240** — Stage 2 seed MERGE explicit-id 패턴 기본화 (Growth-32 발견)~~ → fixed in `andrej-karpathy-rdb-ddl` c1c2a6b (seed_gen.py) + e0f27ba (regression tests), 107 passed
- ~~**task #241** — Stage 3 javax/jakarta 도메인 orphan JPA 어노테이션 제거 (Growth-32 발견)~~ → fixed in `andrej-karpathy-rdb-mybatis` 9188339 (javax) + 04fe964 (jakarta), 둘 다 plain POJO
- ~~**task #242** — Stage 3 REST lane service interface 시그니처 동기화 (Growth-32 발견)~~ → fixed in `andrej-karpathy-rdb-mybatis` e696861 (service-interface.rest.j2) + 59e9ef1 (codegen iface_suffix routing)
- ~~**task #243** — Stage 3 REST lane mapper interface CRUD 반환형 int 통일 (Growth-32 발견)~~ → fixed in `andrej-karpathy-rdb-mybatis` a82cdb8 (mapper-interface.rest.j2) + 59e9ef1 (codegen iface_suffix routing). 회귀: 283d755 (javax tests) + 255a1bf (jakarta tests + nexacro sanity), 85 passed
- ~~**task #245** — Stage 2 seed 타입-aware sentinel (Growth-33 발견, datetime 컬럼에 'TBD' 문자열 삽입 → HSQLDB 파싱 실패)~~ → fixed in `andrej-karpathy-rdb-ddl` d7f36e0 (seed_gen.py type detection) + 8163012 (regression test)
- ~~**task #246** — Stage 3 REST lane mapper interface `@Mapper` 어노테이션 누락 (Growth-33 발견, Spring Boot MyBatis starter auto-discovery 의존)~~ → fixed in `andrej-karpathy-rdb-mybatis` 0657292 (mapper-interface.rest.j2) + 5d4bc68 (mapper-interface.j2 일관성). 회귀: 3644050 (javax test) + a87bee9 (jakarta test). Golden 갱신: a227d5e (CustomerMapper) + c8d0f9f (AddressMapper). 87/87 passed
- ~~**gap G-Jackson** (Growth-33 라이브 검증 부분실패 원인) — `boot-jdk8-javax` runner classpath의 Jackson 버전이 `JsonToken.valueDescFor` (2.16+) 미보유 → NexacroResult 직렬화 시 `NoSuchMethodError`~~ → fixed Growth-46 (2026-05-22): `nexacroN-fullstack/samples/runners/boot-jdk8-javax/pom.xml` `<dependencyManagement>` 에 **jackson-bom 2.17.2 import 를 spring-boot-dependencies 보다 먼저** 배치 — Maven BOM first-wins 규칙으로 jackson-core/annotations/databind/datatype-jdk8/datatype-jsr310/module-parameter-names 6개 모두 2.17.2 통일. 검증: (a) `mvn dependency:tree` jackson-* 전부 2.17.2 확인, (b) runner BUILD SUCCESS, (c) `POST /uiadapter/select_datalist_map.do` envelope → HTTP 200 + ErrorCode=0 + NexacroResult dataset rows(`output1`, 23 rows) 직렬화 성공 — `NoSuchMethodError` 없음.

---

## 6. Growth 이력 (요약)

상세는 git log + USER-GUIDE §3.12 검증 이력 표 참조. 여기는 "어떤 살이 붙었나" 인덱스만.

| Growth | 일자 | 살붙임 요약 |
|---|---|---|
| Growth-1 | 2026-04 | 고객관리 + customer_category |
| Growth-2A~D | 2026-04 | 주문/재고/인사/게시판 살붙임 |
| Growth-3~7 | 2026-04 | 패턴 5종 추가 (L2/MD/TR/RO + compose 확장) |
| Growth-8 | 2026-04 | fn_export_dataset 어댑터 (nexacro + react) |
| Growth-9~13 | 2026-04 | 도메인 5종 신규 (권한/공통코드/결재/알림/파일) |
| Growth-14 | 2026-05 | F1/C1/L2 패턴을 적합 entity에 매핑 |
| Growth-15 | 2026-05 | 배송관리 도메인 신규 |
| Growth-16~20 | 2026-05 | SHELL pattern + Stage 5 통합 + WAR 빌드 검증 |
| Growth-21a | 2026-05 | jakarta auth 번들 (OAuth2/JWT) |
| Growth-21b | 2026-05 | 영업관리 도메인 신규 + cross-domain FK |
| Growth-22 | 2026-05 | 공급망(SCM) 도메인 |
| Growth-23 | 2026-05 | vanilla/javax auth 번들 이식 |
| Growth-24 | 2026-05 | react overlay OAuth2 로그인 패턴 |
| Growth-25 | 2026-05 | seed 컨벤션 문서화 |
| Growth-26~28 | 2026-05 | 재무 v4 (double-entry) + IDENTITY 트랩 환류 + jakarta 라이브 검증 |
| Growth-29~30 | 2026-05 | 풀테스트 4계층 절차 자체 리뷰 + 검증대 매트릭스 |
| Growth-31 | 2026-05-21 | jakarta lane × 영업관리 라이브 검증 (cross-domain) |
| Growth-32 | 2026-05-21 | javax lane × 영업관리 라이브 검증 + codegen bug 4건 |
| Growth-33 | 2026-05-21 | javax lane re-검증 (regenerated, no manual edits) — pytest/JDBC/Maven/Spring context PASS, 엔드포인트 응답은 runner Jackson dep 결함으로 500 → **"라이브 WAS 부분검증"**. codegen 결함 2건 환류 (#245 seed sentinel, #246 `@Mapper` 어노테이션). 새 gap G-Jackson 등록. |
| Growth-34 | 2026-05-21 | Claude Code workflow A안 (구현 완료) — `/cleanup-runner`, `/growth-start`, `/full-test`, `/contribute-back` 4 슬래시 커맨드 + `scripts/workflow/` 6 모듈 + 30 테스트(전부 그린). settings.local.json 슬림. CLAUDE.md 풀테스트/체크리스트 섹션에 자동 실행 힌트 1줄씩 환류. |
| Growth-35 | 2026-05-21 | B-plan L4 live WAS 실구현 — `live_overlay` (5-point overlay, idempotent) + `live_runner` (Spring Boot fat-jar 기동 + ready-poll, 180s timeout) + `live_probe` (nexacro envelope POST + 200/ErrorCode/row_count 판정, 30s timeout) 3 모듈 신규 + `full_test.run_l4_live` 가 placeholder 에서 overlay→`mvn package`→start→wait_until_ready→probe→stop orchestration 으로 교체. 22 신규 테스트(6 overlay + 8 runner + 8 probe) + 7 wiring 테스트 — 60/60 전 그린. CLAUDE.md L4 행 / USER-GUIDE §3.12 자동화 노트 환류. **전제 컨벤션**: scaffold 디렉터리 이름 = Java sub-package 식별자(ASCII slug). `sales-growth33-javax` 같은 hyphen 포함 dir 은 컨벤션 위배 — slug 자동 도출 또는 도메인 매개변수화는 Growth-36 후보. |
| Growth-36 | 2026-05-21 | Scaffold ↔ runner 갭 해소 — Phase 1: `live_overlay.discover_scaffold` 가 Stage 3 실 출력(`com.nexacro.uiadapter.<slug>.*` / `3-mybatis/src/main/resources/{schema,data}.sql` / `mybatis/mapper/`)과 legacy fixture(`com.example.<slug>` / `2-ddl/` / `mybatis/mappers/`) **양쪽 자동 도출**. Phase 2: lane-aware 프로브 dispatch — `lane_runner_map.lane_probe_kind/url` 추가, nexacro 는 `/uiadapter/<entity>/select_datalist_map.do` 엔벨로프 / jakarta·javax·vanilla 는 `GET /api/<entity>` JSON. `full_test.run_l4_live` 가 lane 별로 `probe_endpoint` vs `probe_endpoint_json` 자동 선택. `derive_entity_slug` kebab/PascalCase 양형 지원. 신규 12 테스트(probe 4 + lane_map 5 + full_test 3 파라메트라이즈) + 회귀 71 = 83/83 그린. 실 scaffold `out/sales-growth33-javax` + 실 `boot-jdk8-javax` runner 로 overlay 단계 종단 확인(26 파일 written, 2 edited). 후속 잔여: real-runner mvn rebuild + JVM smoke 는 G-Jackson 차단으로 미실행(Growth-37 후보). |
| Growth-37 | 2026-05-21 | L2 placeholder → 실 JDBC smoke + L1 silent-pass guard — `_jdbc_smoke.java` (JDK 11+ single-file source-mode 런처, HSQLDB in-mem, `^^` separator, 옵션 invariant `SELECT...=<int>`) + `jdbc_smoke.py` 래퍼(env `HSQLDB_JAR` 우선 → fallback path, 없으면 `SmokeResult(ok=True, skipped=True)` 로 L3/L4 비차단). `full_test.run_l2_jdbc` 가 `discover_sql`(Stage 3 우선 → 2-ddl fallback) + `run_smoke` 호출로 교체. `run_l1_pytest` 에 empty-skip guard 추가 — sibling repo 0개 실행 시 silent True 대신 False 반환(worktree/sandbox 갭 노출). 신규 17 테스트(jdbc_smoke unit 8 + 실-HSQLDB integration 4 skipif-gated + full_test wiring 5) = 100/100 그린. 후속 잔여: L3 pom 탐색 일반화 + live_probe retry/backoff (Growth-38 후보). |
| Growth-38 | 2026-05-21 | 풀테스트 견고성 3종 — (1) **L3 pom 탐색 일반화**: `_find_pom` 헬퍼 추가, 탐색 순서 `5-overlay/pom.xml` → `3-mybatis/pom.xml` → root `pom.xml`. Stage 3-only scaffold(오버레이 미실행)도 빌드 가능. (2) **live_probe transient retry**: `probe_endpoint(_json)` 에 `retries`/`retry_delay_sec` 파라미터 — urlopen 예외(connection refused/timeout)에만 재시도, `HTTPError` 는 즉시 surface(실응답이므로 재시도하면 안 됨). ready-poll 직후 바인드 지연으로 거부 한두 번 발생하는 케이스 자동 흡수. (3) **lane pre-validation**: `run()` 진입부에서 `resolve_runner(lane)` 호출 — 잘못된 lane 인자는 L1/L2/L3 낭비 없이 즉시 `ValueError`. 신규 11 테스트(probe retry 4 + L3 pom 5 + lane validation 1 + run_l3_mvn no-pom 1) = 111/111 그린. |
| Growth-39 | 2026-05-21 | `/full-test --json` 머신리더블 출력 — `run()` 반환을 `str` → `FullTestResult` dataclass(label/lane/scaffold/layers dict)로 승격, `__str__` → label 로 레거시 호출자 무손상. `main(argv)` + argparse 추가, `--json` 시 `builtins.print` 를 stderr 로 monkey-patch 해 per-layer 출력 격리 → stdout 은 단일 파싱 가능 JSON. 종료코드 0 = `L4_full` PASS, 1 = 그 외 — CI rc 분기 가능. 신규 6 테스트(결과 객체 / `__str__` / json mode / text mode / stdout 격리 / non-zero exit) = 117/117 그린. 슬래시 커맨드 argument-hint 에 `[--json]` 노출. 후속 잔여: CRUD endpoint verdict(POST insert + row delta + DELETE round-trip, lane-aware) → Growth-40 후보. |
| Growth-40 | 2026-05-21 | REST lane CRUD round-trip probe — `live_crud.crud_roundtrip_rest()` 가 baseline GET → POST insert(`_rowType=I`) → +1 verify GET → POST delete(`_rowType=D`) → baseline verify GET 5-step round-trip, 모두 200 + affected≥1 + count delta 일치 시 `ok=True`. `build_insert_template()` 가 `data.sql` MERGE 첫 행을 마이닝해 컬럼/값 도출하고 PK 만 sentinel=999001 로 치환(FK ref 보존, IDENTITY 0-base 트랩 회피). SQL 리터럴 coercion: `CURRENT_TIMESTAMP/DATE/TIME` → ISO 문자열(MyBatis JdbcType 바인딩이 서버에서 coerce), `TRUE/FALSE/NULL`, 쿼트 escape `''` 지원. `lane_supports_crud()` gate 가 REST lane(jakarta/javax/vanilla)만 허용 — nexacro 엔벨로프 CRUD(dsInsert/dsDelete)는 Growth-41 후보로 deferral. `full_test.run_l4_live` 가 optional `layers: dict` kwarg 수용 — REST lane × probe full pass 일 때만 CRUD 단계 실행, 결과를 `layers["L4_crud"]`/`["L4_crud_reason"]` 에 기록(enrichment, 라벨 게이트 아님). 2-arg 레거시 호출은 CRUD 스킵 — 무손상 back-compat. 신규 33 테스트(live_crud 27 + full_test wiring 6) = 150/150 그린. |
| Growth-41 | 2026-05-21 | nexacro **복잡 화면 패턴(Complex Screen Patterns)** 미러 + Stage 4 loader 연동 — 외부 출처 [`nexacro-claude-skills/.../nexacro-form-maker/SKILL.md#복잡-화면-패턴`](https://github.com/JasonMMo/nexacro-claude-skills) 의 5개 복합 패턴 중 **이미 등재된 MD** 를 제외한 **4종** 을 `rdb-nexacro/.claude/skills/karpathy-rdb-nexacro/patterns/` 에 신규 디렉터리로 추가: **MT** (multi-tab-N-tier — 3탭 lazy-loading, 탭2 child entity 자동 wiring), **TG** (tree-grid-2-pane — 좌측 `dsCategory` treeitemcontrol + 우측 entity 그리드, 카테고리 선택 → `dsSearch.{category_fk_column}` 자동 주입), **PS** (popup-search-1-tier — `<Form classname="Popup">` + `opener.fnReceivePopupData(oData)` 콜백, oncelldblclick 선택, 코드 마스터/거래처 picker), **MDS** (multi-dataset-save-header-lines — 헤더 BindItem + 라인 grid 를 `dataList=ds{M}:U,dsChildList=ds{C}:U` 단일 transaction 동시 저장, 주문서/발주서/송장 작성). 각 패턴 = `manifest.yaml` + `form.xfdl.j2` + `README.md` 3-파일 컨벤션 준수. **새 템플릿** `templates/header_field.xml.j2` (MDS 헤더 BindItem 렌더). `form_composer.compose_form` 에 `pattern == "MDS"` 분기 추가 — 헤더 필드 자동 렌더 후 `ctx["header_fields"]` 주입. **테스트** 8개 신규 (pattern_loader 4 파라메트라이즈 + form_composer 렌더 4) → 93/93 그린. `references/patterns-spec.md` 에 Growth-41 절 추가 (MD vs MDS 구별 명시). 패턴 코드 컬렉션: 7개 → **11개** 로 확장 (D2/F1/C1/L2/MD/TR/RO + MT/TG/PS/MDS, SHELL 은 화면 패턴이 아닌 shell 패턴 별도). blueprint 사용 예: `entities[*].pattern: MT\|TG\|PS\|MDS`. |
| Growth-43 | 2026-05-22 | **karpathy alignment plan 완료** — `loader.py` `extends` 해결자 구현(M3 잔여 갭). `_find_catalog_entity()` 가 `~/.karpathy-rdb/catalog/*.seed.md` 스캔 → 이름 일치 entity 블록 반환. `_resolve_extends()` 가 base columns/indexes/constraints 를 merge 후 현재 entity 우선(same-name override). `load_blueprint()` 가 모든 entity 를 자동 resolve — extends 없으면 passthrough, 있는데 catalog 미발견 시 `BlueprintError`(silent fallback 금지). `test_extends.py` 13 테스트 신규(find/resolve/integration) → **121/121 그린** (rdb-ddl, 1 skipped). 2 커밋 pushed `andrej-karpathy-rdb-ddl` origin/master (0de75d4·2e9408e). M1-M3 5축 자체평가: 반복 데이터 효율(4) · 지식 누적(5) · 풍부한 Seeds(5) · WAR 완성도(3, 메커니즘) · Karpathy 정신(5) = **평균 4.4/5**. |
| Growth-42 | 2026-05-21 | nexacro **envelope CRUD round-trip** probe — Growth-40 가 미뤘던 nexacro 엔벨로프 wire 를 신규 모듈 `live_crud_nexacro.py` 로 구현: `POST /uiadapter/<entity>/save_datalist_map.do` + `<Root xmlns=".../platform/dataset"><Dataset id="ds<Pascal>"><Rows><Row Type="insert"\|"delete">...</Row></Rows>` 5-step (baseline `select_datalist_map.do` → insert envelope → +1 verify → delete envelope → baseline verify). `<Col id="...">` XML escape (`&` `<` `>`) + `null → <Col/>` + bool → `"true"/"false"`. `_parse_error_code`/`_count_rows` 는 live_probe 의 정규식 contract 재사용(circular import 회피 위해 inline). 디스패처 일반화: `lane_runner_map.lane_crud_kind(lane)` → `"rest"` (jakarta/javax/vanilla) \| `"envelope"` (nexacro), `lane_supports_crud` 는 backward-compat shim — 이제 nexacro 도 True. `full_test.run_l4_live` 가 probe full pass 직후 `ckind` 로 dispatch — REST 는 `live_crud.crud_roundtrip_rest`, envelope 는 `live_crud_nexacro.crud_roundtrip_envelope(select_url, save_url, dataset_id=ds<Pascal>, insert_row, pk_column, pk_value)`. 결과: `layers["L4_crud"]`(bool)/`["L4_crud_reason"]`(str)/`["L4_crud_kind"]`("rest"\|"envelope") — 실패 시 어느 직렬화 스택(REST controller vs NexacroResult)인지 즉시 어트리뷰트 가능. 신규 23 테스트(envelope builder 8 + 5-step happy 1 + 7 error paths + 6 dispatcher/helper + transport contract) + 기존 `test_run_l4_live_crud_skipped_for_nexacro_lane` 를 `..._dispatches_envelope_crud` 로 의미 반전(REST 0회/envelope 1회 + dataset_id="dsLead" + save_url 컨벤션 검증) → **173/173 그린**. `nexacro_dataset_id(entity)` = snake → `ds<Pascal>` (`account` → `dsAccount`, `order_item` → `dsOrderItem`). **라이브 검증 (2026-05-22, real `boot-jdk17-jakarta` runner, `out/customer-growth42-nexacro` scaffold, dialect=hsqldb)**: L1 4-repo pytest rc=0 · L2 schema+data 12+12 stmt OK · L3 SKIP=PASS (nexacro lane convention) · L4 overlay 26w/2e + mvn rc=0 + probe 200/ErrorCode=0/rows=3 + **CRUD envelope ok=True baseline=3→+1=4→final=3** → **풀테스트 그린**. 환류 codegen 결함 2건 동시 수정: (a) `AddressServiceImpl` 등 generated service 의 unsafe `_RowType_` 추출 → runner `BoardServiceImpl` 패턴 (instanceof + DEFAULT fallback) 로 안전화, (b) mapper.xml 의 SQL 컬럼은 UPPER (HSQLDB unquoted-normalize) 유지하되 `#{placeholder}` + `<if test>` key 는 lowercase 로 통일 — envelope `<Col id="customer_id">` ↔ Map key 대소문자 mismatch 로 인한 silent INSERT-skip 차단. 추가 코드 정리: `cleanup_runner` 가 generated overlay tree(`com.example`) 만 제거하고 runner 자체 패키지(`com.nexacro.uiadapter`) 는 보존. |
| Growth-45 | 2026-05-22 | **v0.6 C-2 유사 도메인 추천 강화** — `protocols/01-init.md` Phase 1 Q2 를 3단계 fallback 으로 재구성: (2-1) 로컬 `presets/INDEX.md` 매칭(v0.3.x 점수 알고리즘 그대로 — 제목/aliases +5, keywords 토큰당 +2, entities +3, 한 줄 +1~3) → (2-2) `~/.karpathy-rdb/catalog/` 글로벌 frontmatter 추가 스캔, 동일 알고리즘으로 후보 풀 합산(로컬·글로벌 동명 도메인 시 글로벌 우선·점수는 max) → (2-3) `~/.karpathy-rdb/catalog/meta/<X>_meta.md` (C-1 출력) 존재 시 반복 등장 entity/concept/false-belief 표를 추천 컨텍스트로 부착. 글로벌 디렉터리/메타 파일 부재 시 단계별 **SKIP=PASS**(로컬 INDEX only fallback). 점수 분기 ≥5/2~4/0 + 출처 라벨(local|global) 사용자 노출. 벡터 DB 금지(Karpathy 정신). `SKILL.md` 에 "유사 도메인 추천 (v0.6 C-2)" 1단락 추가. 신규 6 테스트(`test_init_protocol_c2.py` — 3단계 헤더/글로벌 경로/메타 경로/SKIP=PASS/§7.2 참조/점수 임계) → **194/194 그린**. 알리먼트 리뷰 §7.2 충족(C-1 짝꿍, 진입 게이트 = 글로벌 카탈로그·메타 부재 시 자동 폴백). |
| Growth-44 | 2026-05-22 | **v0.6 C-1 메타 추출 진입** — Phase A 정렬(§0 Layer Ownership Card + CLAUDE.md 5축 + 4 layer SKILL.md ownership + contribute-back self-check + bgIsolation settings) 8커밋 선행. `andrej-karpathy-rdb-skill/scripts/meta_extract.py` 신규 — 복수 프로젝트의 `wiki/learn-log.md` 횡단 → 도메인별 반복 등장(≥`--min-projects`, default 3) entity/concept/rule/false-belief 를 `~/.karpathy-rdb/catalog/meta/<도메인>_meta.md` 로 산출. **2단 게이트**: (a) 프로젝트 수 < threshold → SKIP=PASS, (b) 도메인 등장 프로젝트 수 < threshold → 해당 도메인만 SKIP, (c) 모든 도메인 미달 → SKIP=PASS. CLI: `extract --project <p>... [--projects-file <f>] [--output-root <dir>] [--min-projects N]`. contribute 이벤트(kind=`contribute`/`pattern-contribute`)는 메타 추출 대상 제외(메타-메타 회피). 신규 12 테스트(parse/aggregate/skip-gate 3종/render/CLI 양형) → **188/188 그린** (rdb-skill 전체). 명시 호출 전용·자동 머지 없음·LLM/벡터 검색 없음(Karpathy 정신 유지). 알리먼트 리뷰 §7.1 진입조건(실 프로젝트 3개) 도달 시 자동 가용 — 현재 wiki 컨벤션 프로젝트 0개라 dry-run 은 [warn] rc=2 정상. |
| Growth-46 | 2026-05-22 | **G-Jackson gap 해결** (Growth-33 부터 미해결) — `nexacroN-fullstack/samples/runners/boot-jdk8-javax/pom.xml` `<dependencyManagement>` 에 **jackson-bom 2.17.2 import 를 spring-boot-dependencies(2.7.18) 보다 먼저** 배치. Maven BOM 임포트는 first-wins 규칙(전이 의존성 해결 시 먼저 선언된 BOM 우선) → jackson-core/annotations/databind/datatype-jdk8/datatype-jsr310/module-parameter-names **6개 모듈 모두 2.17.2 통일**. 원인: 이전엔 `jackson-databind` 만 explicit 2.17.2, 나머지는 spring-boot 2.7.18 BOM 의 ~2.13.5 사용 → databind 가 `JsonToken.valueDescFor`(Jackson 2.16+ API) 호출 시 core 2.13.5 가 `NoSuchMethodError` 던짐 → NexacroResult 직렬화 500. **검증 3-tier**: (a) `mvn dependency:tree` jackson-* 6개 모두 `2.17.2:compile` 확인, (b) `mvn -DskipTests package` BUILD SUCCESS (30.9s), (c) runner boot + `POST http://localhost:8080/uiadapter/select_datalist_map.do` (board domain runner-default) 엔벨로프 → HTTP 200 + `<Parameter id="ErrorCode" type="int">0</Parameter>` + `<Dataset id="output1">` 23 rows 직렬화. NoSuchMethodError 부재. **codegen 결함 아님 — runner-side dep 픽스만**. §0 mybatis 행 미해결 환류 갱신, §5 G-Jackson 항목 strikethrough + 픽스 SHA 후속 첨부. javax lane fresh scaffold 종단 검증(L1-L4 그린 라벨)은 별도 task — 현 `out/sales-growth33-javax` 가 pgsql DDL 사용해 HSQLDB 검증대 부적합. |
| Growth-49 | 2026-05-22 | **javax fresh-scaffold 풀테스트 그린** (Growth-46/47/48 3-픽스 누적 종단검증) — `customer` 도메인 + `--lane nexacro --dialect hsqldb --uia-namespace spring` fresh scaffold(`out/customer-growth49-javax`) → `scripts/workflow/full_test.py javax` 실행 → **모든 4계층 PASS + 라벨 "풀테스트 그린"**. L1 4-repo pytest rc=0 · L2 schema 12 stmts + seed 12 stmts OK · L3 SKIP=PASS(runner-provides-pom) · L4 overlay 26w/2e + mvn rc=0 + probe envelope http=200 errcode=0 rows=3 + CRUD envelope ok=True baseline=3→+1=4→final=3. **결정적 검증 메시지**: `[L4] scaffold_lane=nexacro differs from runner lane=javax — probe/CRUD dispatch follows scaffold` (Growth-48 픽스가 envelope endpoint 로 dispatch). 3-픽스 누적 의미: G-Jackson(Growth-46, runner-side jackson-bom first-import) → NexacroResult JSON 직렬화 NoSuchMethodError 해소; T-NexacroUiaPkg-javax(Growth-47, `--uia-namespace spring` 파라미터 6단계 환류) → ParamDataSet/NexacroResult symbol-not-found 해소; T-Probe-LaneRunner-Mismatch(Growth-48, scaffold_lane override) → REST probe 가 envelope endpoint 미스 해소. 회귀 0 (신규 코드 변경 없음 — 기존 픽스 검증만). cleanup 후 runner clean(`git status --short` 0줄). §0 creater row 미해결 환류 deferred 1건은 그대로(cleanup_runner PowerShell quoting). §1 javax row `⚠️ Growth-47` → `✅ Growth-49`. 알려진 잡음: `full_test.py` cleanup의 `Remove untracked mappers` 가 PowerShell subexpression quoting 으로 FAIL → 수동 `Remove-Item` 으로 처리(creater row 미해결 환류와 동일 트랩). |
| Growth-48 | 2026-05-22 | **T-Probe-LaneRunner-Mismatch 픽스** (Growth-47 잔여 차단) — `scripts/workflow/lane_runner_map.py` 의 4개 dispatcher(`lane_probe_kind` / `lane_probe_url` / `lane_crud_kind` / `lane_supports_crud`) 에 optional `scaffold_lane: str \| None = None` 매개변수 추가. 신규 `_effective_lane(lane, scaffold_lane)` helper 가 supplied 시 scaffold_lane 우선, 미지정 시 lane 그대로(pre-Growth-48 API 무손상). `scripts/workflow/live_overlay.py` 에 `discover_scaffold_lane(scaffold_dir)` 신규 — `scaffold-report.md` 의 `^\s*-\s*lane:\s*\`<name>\`` 라인을 regex 로 추출, 파일/라인 부재 시 graceful None. `scripts/workflow/full_test.py:run_l4_live` 가 probe/CRUD dispatch 전 `discover_scaffold_lane` 호출 → 4개 dispatcher 모두에 `scaffold_lane=` 키워드 전달, divergence 발견 시 informational print(`[L4] scaffold_lane=... differs from runner lane=...`). **wire-protocol 의 진실원천이 deployment runner 가 아니라 Stage 3 codegen 산출물** 임을 코드로 인코딩. 신규 11 테스트 — `test_lane_runner_map.py` 5(scaffold_lane override probe_kind/url/crud_kind + None legacy preserve + unknown ValueError), `test_live_overlay.py` 4(report-only/3-lane parametrize/missing-file/missing-line), `test_full_test.py` 2(scaffold_lane=nexacro on javax runner uses envelope · no-report falls back to runner lane). 회귀: workflow suite 82/82 그린, 본 코어 변경 후 sibling pre-existing failures(`test_live_crud_nexacro` 7건 — Growth-42 후속 stale tests, 본 작업 무관) 외 zero regression. §0 creater row trap 카운트 그대로 3(T-Probe-LaneRunner-Mismatch 가 트랩 → RESOLVED 라벨 갱신) + 미해결 환류에서 제거. §4 트랩 행 상태 deferred → RESOLVED. **연계로 vanilla lane 검증대 신설** (mybatis row 미해결 환류 "vanilla 검증대 부재" 동시 해소): `board` 도메인 fresh scaffold (`--lane vanilla --dialect hsqldb`) → `scripts/workflow/full_test.py vanilla` → 라벨 **JDBC + 빌드까지만 검증 → javax-host 검증** (L1 4-repo pytest rc=0 · L2 schema+seed OK · L3 `mvn package` rc=0 · L4 overlay 26w/2e PASS · L4 mvn rc=1 = boot-repackage 가 stale `runner-boot-jdk8-javax-0.1.0-SNAPSHOT.jar` 잠금 해제 실패 = **환경성, codegen 결함 아님**). 핵심 발견: `controller.vanilla.java.j2` 가 `org.springframework.web.bind.annotation.*` 만 사용(`jakarta.servlet`/`javax.servlet` import 없음) → vanilla scaffold 는 Spring 5(`boot-jdk8-javax`) / Spring 6(`boot-jdk17-jakarta`) 양 러너 호환. `BoardController` 산출물에서 servlet-API import 0건 직접 확인. §1 vanilla row 가 `⚠️ 검증대 부재` → `✅ Growth-48 (board scaffold)` 로 갱신, "vanilla → javax-host 검증" 라벨 컨벤션이 라이브 검증대 매트릭스에 최초 적용. |
| Growth-47 | 2026-05-22 | **javax fresh scaffold 종단 검증 + T-NexacroUiaPkg-javax 픽스** (라벨: **라이브 WAS 부분검증** — L1+L2+L4-빌드 PASS, L4-probe FAIL). `customer` 도메인 fresh scaffold(`lane=nexacro` + `dialect=hsqldb` + `--uia-namespace spring` + boot-jdk8-javax 러너 타깃) 시도 중 L4 `mvn package` 가 `ParamDataSet/NexacroResult/NexacroException` 심볼 미발견으로 컴파일 실패. **원인**: mybatis `controller.java.j2` + `service-impl.java.j2` 가 `com.nexacro.uiadapter.jakarta.core.*` 하드코딩 → boot-jdk8-javax 러너의 uiadapter 라이브러리는 `.spring.core.*` 변종(Spring 5/javax.servlet). **6단계 환류** (A안 — 템플릿 수정 + 종단검증 채택, B fallback / C trap-only 거부): (1) `rdb-mybatis/scripts/precompute.py` `build_entity_context` 에 `uia_namespace: str = "jakarta"` 파라미터 + validation(`{jakarta,spring}` 외 ValueError) + 컨텍스트 dict 주입, (2) `codegen.py` `render_entity_files` 가 `uia_namespace` 를 receive → precompute 로 forward, (3) `compile.py` 가 `--uia-namespace {jakarta,spring}` argparse 추가, (4) `controller.java.j2` 가 3개 import 를 `{{ lib_prefix }}.{{ uia_namespace }}.core.*` 사용, (5) `service-impl.java.j2` 의 `DataSetRowTypeAccessor` import 도 동일, (6) `creater/scripts/scaffold_cli.py` + `scaffold_orchestrator.py` 가 `--uia-namespace` 노출하고 `_run_stage3` cmd 에 forward. **회귀 3 신규 테스트**(`test_codegen.py`): spring variant 4-import 검증 + jakarta default 미오염 검증 + invalid value ValueError → **12/12 그린** (rdb-mybatis). **L4 재빌드 rc=0** (검증). **잔여 L4-probe FAIL**: `lane_runner_map.lane_probe_kind` 가 `--lane javax`(runner 선택)만 보고 REST probe 사용 → 실제 endpoint(`/uiadapter/customer/select_datalist_map.do`, scaffold-side nexacro lane) 미스. 새 트랩 **T-Probe-LaneRunner-Mismatch** §4 등재(Growth-48 후보). G-Jackson 실 종단 클로저는 Growth-46 (board 도메인 hand-written BoardController) 가 이미 달성. |

---

## 7. 사용 규칙

1. 새 Growth 시작 시 § 6 행 추가 (1줄)
2. lane/runner 검증 결과 변경 시 § 1 갱신
3. 신규 도메인/패턴/dialect/overlay 등장 시 해당 표 (§ 2 또는 § 3) 갱신
4. dialect/lane 트랩 발견 시 § 4 1행 + 환류 위치 명시
5. codegen 결함 발견 시 task 생성 → § 5에 task ID 인덱싱
6. 해결되면 § 5에서 줄긋고 commit SHA 첨부 (예: `~~task #240~~ → fixed in abc123def`)

CLAUDE.md 의 § 작업시체크리스트 3번 "wiki/learn-log.md 에 1줄 기록" 의 구체 위치가 **이 파일**이다.
