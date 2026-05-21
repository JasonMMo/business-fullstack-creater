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

## 1. 라이브 WAS 검증대 상태 (lane × runner)

`nexacroN-fullstack/samples/runners/` 매트릭스. CLAUDE.md §풀테스트 4계층 표 4번을 통과한 lane.

| lane | 디폴트 러너 | 검증 상태 | 비고 |
|---|---|---|---|
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

---

## 5. 미해결 환류 항목 (codegen 결함)

발견 시 task를 만들고 여기 1줄로 인덱싱. 해결 시 줄긋고 commit SHA 첨부.

- ~~**task #240** — Stage 2 seed MERGE explicit-id 패턴 기본화 (Growth-32 발견)~~ → fixed in `andrej-karpathy-rdb-ddl` c1c2a6b (seed_gen.py) + e0f27ba (regression tests), 107 passed
- ~~**task #241** — Stage 3 javax/jakarta 도메인 orphan JPA 어노테이션 제거 (Growth-32 발견)~~ → fixed in `andrej-karpathy-rdb-mybatis` 9188339 (javax) + 04fe964 (jakarta), 둘 다 plain POJO
- ~~**task #242** — Stage 3 REST lane service interface 시그니처 동기화 (Growth-32 발견)~~ → fixed in `andrej-karpathy-rdb-mybatis` e696861 (service-interface.rest.j2) + 59e9ef1 (codegen iface_suffix routing)
- ~~**task #243** — Stage 3 REST lane mapper interface CRUD 반환형 int 통일 (Growth-32 발견)~~ → fixed in `andrej-karpathy-rdb-mybatis` a82cdb8 (mapper-interface.rest.j2) + 59e9ef1 (codegen iface_suffix routing). 회귀: 283d755 (javax tests) + 255a1bf (jakarta tests + nexacro sanity), 85 passed

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

---

## 7. 사용 규칙

1. 새 Growth 시작 시 § 6 행 추가 (1줄)
2. lane/runner 검증 결과 변경 시 § 1 갱신
3. 신규 도메인/패턴/dialect/overlay 등장 시 해당 표 (§ 2 또는 § 3) 갱신
4. dialect/lane 트랩 발견 시 § 4 1행 + 환류 위치 명시
5. codegen 결함 발견 시 task 생성 → § 5에 task ID 인덱싱
6. 해결되면 § 5에서 줄긋고 commit SHA 첨부 (예: `~~task #240~~ → fixed in abc123def`)

CLAUDE.md 의 § 작업시체크리스트 3번 "wiki/learn-log.md 에 1줄 기록" 의 구체 위치가 **이 파일**이다.
