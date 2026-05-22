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
| **skill (Stage 1)** | `andrej-karpathy-rdb-skill/.claude/skills/karpathy-rdb/presets/*.seed.md` + `protocols/` | `andrej-karpathy-rdb-skill/tests/` | 0 | — |
| **ddl (Stage 2)** | `andrej-karpathy-rdb-ddl/catalogs/preset-catalog.yaml`, dialect 어댑터(postgres/hsqldb/mysql) | `andrej-karpathy-rdb-ddl/tests/` | 3 (HSQLDB IDENTITY 0-base, SQL:2008 `LEAD`, HSQLDB vs postgres-default schema) | — |
| **mybatis (Stage 3)** | `andrej-karpathy-rdb-mybatis/templates/<lane>/`, lane(nexacro/vanilla/jakarta/javax) | `andrej-karpathy-rdb-mybatis/tests/` | 6 (explicit-id MERGE, `@Mapper` bean, typed seed sentinel, REST snake_case URL, Map placeholder case, nexacro `_RowType_` 안전추출) | **G-Jackson** (javax runner Jackson 2.16+ 부재, Growth-33~), **vanilla lane 검증대 부재** |
| **nexacro (Stage 4+5)** | `andrej-karpathy-rdb-nexacro/patterns/`(D2/F1/C1/L2/MD/RO/TR/TG/MT/PS/MDS), UI overlay(nexacro/react) | `andrej-karpathy-rdb-nexacro/tests/` | 0 | — |
| **creater (Orchestrator)** | `business-fullstack-creater/.claude/commands/`(scaffold·full-test·growth-start·contribute-back·cleanup-runner) + `scripts/workflow/`(full_test·live_*·lane_runner_map·learn_log) | `business-fullstack-creater/tests/` | 2 (javax lane URL 컨벤션, JDK8 source/target on JDK17 JAVA_HOME) | `cleanup_runner.py` PowerShell subexpression syntax error (Growth-42 메모, deferred) |

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
| **javax** | `boot-jdk8-javax` (Spring Boot 2.7) | ✅ Growth-32 (sales) | JAVA_HOME=JDK17, target=1.8 (JDK8 부재 시 우회) |
| **vanilla** | (직접 러너 없음) | ⚠️ 검증대 부재 | `javax` 러너에 servlet 임포트 또는 자체 minimal-servlet 러너 미정 |

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

---

## 5. 미해결 환류 항목 (codegen 결함)

발견 시 task를 만들고 여기 1줄로 인덱싱. 해결 시 줄긋고 commit SHA 첨부.

- ~~**task #240** — Stage 2 seed MERGE explicit-id 패턴 기본화 (Growth-32 발견)~~ → fixed in `andrej-karpathy-rdb-ddl` c1c2a6b (seed_gen.py) + e0f27ba (regression tests), 107 passed
- ~~**task #241** — Stage 3 javax/jakarta 도메인 orphan JPA 어노테이션 제거 (Growth-32 발견)~~ → fixed in `andrej-karpathy-rdb-mybatis` 9188339 (javax) + 04fe964 (jakarta), 둘 다 plain POJO
- ~~**task #242** — Stage 3 REST lane service interface 시그니처 동기화 (Growth-32 발견)~~ → fixed in `andrej-karpathy-rdb-mybatis` e696861 (service-interface.rest.j2) + 59e9ef1 (codegen iface_suffix routing)
- ~~**task #243** — Stage 3 REST lane mapper interface CRUD 반환형 int 통일 (Growth-32 발견)~~ → fixed in `andrej-karpathy-rdb-mybatis` a82cdb8 (mapper-interface.rest.j2) + 59e9ef1 (codegen iface_suffix routing). 회귀: 283d755 (javax tests) + 255a1bf (jakarta tests + nexacro sanity), 85 passed
- ~~**task #245** — Stage 2 seed 타입-aware sentinel (Growth-33 발견, datetime 컬럼에 'TBD' 문자열 삽입 → HSQLDB 파싱 실패)~~ → fixed in `andrej-karpathy-rdb-ddl` d7f36e0 (seed_gen.py type detection) + 8163012 (regression test)
- ~~**task #246** — Stage 3 REST lane mapper interface `@Mapper` 어노테이션 누락 (Growth-33 발견, Spring Boot MyBatis starter auto-discovery 의존)~~ → fixed in `andrej-karpathy-rdb-mybatis` 0657292 (mapper-interface.rest.j2) + 5d4bc68 (mapper-interface.j2 일관성). 회귀: 3644050 (javax test) + a87bee9 (jakarta test). Golden 갱신: a227d5e (CustomerMapper) + c8d0f9f (AddressMapper). 87/87 passed
- **gap G-Jackson** (Growth-33 라이브 검증 부분실패 원인) — `boot-jdk8-javax` runner classpath의 Jackson 버전이 `JsonToken.valueDescFor` (2.16+) 미보유 → NexacroResult 직렬화 시 `NoSuchMethodError`. 컨트롤러는 정상 도달, 핸들러는 정상 호출됨. 환류 방향: runner 의존성 업그레이드 또는 NexacroResult-Jackson 격리 어댑터. **codegen 결함 아님** — runner-side dep 문제.

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

---

## 7. 사용 규칙

1. 새 Growth 시작 시 § 6 행 추가 (1줄)
2. lane/runner 검증 결과 변경 시 § 1 갱신
3. 신규 도메인/패턴/dialect/overlay 등장 시 해당 표 (§ 2 또는 § 3) 갱신
4. dialect/lane 트랩 발견 시 § 4 1행 + 환류 위치 명시
5. codegen 결함 발견 시 task 생성 → § 5에 task ID 인덱싱
6. 해결되면 § 5에서 줄긋고 commit SHA 첨부 (예: `~~task #240~~ → fixed in abc123def`)

CLAUDE.md 의 § 작업시체크리스트 3번 "wiki/learn-log.md 에 1줄 기록" 의 구체 위치가 **이 파일**이다.
