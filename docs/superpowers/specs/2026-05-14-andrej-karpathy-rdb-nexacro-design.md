# Stage 4 — `andrej-karpathy-rdb-nexacro` Design Spec

> **Status:** Draft v0.1 (2026-05-14)
> **Pipeline position:** Stage 4 — Frontend nexacro form generator
> **Predecessor:** `andrej-karpathy-rdb-mybatis` v0.1.3 (Stage 3) — emits `_blueprint.yaml` 기반 MyBatis backend
> **Overlay target:** `nexacro-fullstack-starter` v0.6.0 scaffold (external plugin)
> **Companion contract:** `needs/Plugin참조/3. Middle+Frontend - Stage 3→4 nexacro 핸드오프 계약.md`

## 1. 목표 (Goal)

Stage 1 (`_blueprint.yaml`) + Stage 3 (`endpoints.json`) 입력으로부터 **entity 별 nexacro xfdl form** 과 **메뉴/typedefinition 패치**를 자동 생성하여, `nexacro-fullstack-starter` scaffold 위에 overlay 가능한 nxui 트리를 만든다.

핵심 가치:
- Stage 3 가 생성한 Controller endpoint (`/{entity}/select_datalist_map.do` + `/save_datalist_map.do`) 를 **호출하는 화면을 손수 작성 없이** 발행
- 백엔드 (Stage 3) 와 프론트엔드 (Stage 4) 가 **동일 blueprint 를 단일 진실로** 공유

## 2. 비목표 (Non-Goals, v0.1)

- Entity 간 master-detail / parent-child 자동 연결 (D3) — v0.1 은 entity 당 독립 form
- 사용자 패턴 커스터마이즈 (D6) — `char(1)+*_yn → CheckBox` 컨벤션 외 override 없음
- nexacro license/build 자동화 — `nexacro-build` 별도 skill 영역
- form pattern 변형 (wizard, dashboard 등) — v0.1 은 **3단 구조 (Search + Grid + Edit)** 하나

## 3. 6대 설계 결정 (Design Decisions)

| ID | 결정 | 채택안 | 근거 |
| :-: | :-- | :-- | :-- |
| D1 | Form pattern | **2단 구조** — Search 상단 (60px) + **편집 가능 Grid** 중단 (520px) + 액션 버튼 (조회/추가/저장/삭제). Grid cell 직접 편집, 별도 Edit panel 없음 | dsSearch 명세 기반 PK/business key 검색 + Grid in-place 편집으로 화면 단순화 |
| D2 | Frame style | **packageN MDI** | frameLeft 메뉴 + 다중 ChildFrame, 업무 시스템 표준 UX |
| D3 | Relations | **v0.1: entity 당 독립 form** | 관계 자동화는 schema 추론 부정확, v0.2 로 분리 |
| D4 | Input contract | **`_blueprint.yaml` + `endpoints.json`** | Stage 1 + Stage 3 산출물의 결합. endpoints.json 미존재 시 `--infer-endpoints` fallback |
| D5 | Output strategy | **별도 dir emit + overlay 스크립트** | scaffold 보존, overlay 충돌 가시화, Stage 3 동일 패턴 |
| D6 | Type mapping | **고정 매트릭스 (12 카테고리) + `*_yn` 컨벤션** | 결정성 + 한국 업무 관례 수용, override v0.2 |

## 4. 아키텍처 (Architecture)

### 4.1 데이터 흐름

```
[Stage 1] wiki/_blueprint.yaml ────┐
                                   ├─→ [Stage 4] karpathy-rdb-nexacro compile
[Stage 3] endpoints.json ──────────┘                │
                                                    ▼
                                        out/{nxui/, patches/, docs/, overlay.sh}
                                                    │
                                                    ▼
                                        [overlay.sh]
                                                    ▼
                              <PROJECT_NAME>/nxui/_form_/<entity>.xfdl
                              <PROJECT_NAME>/nxui/_datasets_/dsMenu.seed.xml
                              <PROJECT_NAME>/nxui/typedefinition.xml (patched)
```

### 4.2 입력 계약

**`_blueprint.yaml`** (Stage 1 v0.1.1)
- `version: 1`, `validation.passed: true`
- `entities[].columns[].{name, type, pk, nullable}` (`nullable` 키 정렬 완료)

**`endpoints.json`** (Stage 3 v0.1.4 신규 — 후속 작업)
```json
{
  "version": 1,
  "context_path": "/uiadapter",
  "entities": [{
    "name": "customer",
    "endpoint_base": "/customer",
    "endpoints": [
      {"method": "select_datalist_map", "http_path": "/customer/select_datalist_map.do",
       "input": {"dsSearch": "param-dataset"}, "output": {"output1": "list-dataset"}},
      {"method": "save_datalist_map", "http_path": "/customer/save_datalist_map.do",
       "input": {"dataList": "row-dispatch"}, "output": {}}
    ]
  }]
}
```

`--infer-endpoints`: endpoints.json 부재 시 blueprint entity name 으로 추론 (`/{entity}/select_datalist_map.do` 등).

### 4.3 출력 매니페스트

```
<out>/
├── nxui/
│   ├── _form_/<entity>.xfdl                      # entity 당 1 form
│   └── _datasets_/dsMenu.seed.xml                # frameLeft 메뉴 seed rows
├── patches/
│   ├── typedefinition.patch.xml                  # Services 블록 추가분
│   └── typedefinition.merge.py                   # patch → 실 파일 idempotent 머지
├── docs/
│   ├── nexacro-report.md                         # entity → form 매핑, 타입 결정 trace
│   └── warnings.md                               # 비치명 경고 (타입 fallback 등)
└── overlay.sh                                    # scaffold 위 overlay 실행
```

### 4.4 플러그인 레이아웃

```
andrej-karpathy-rdb-nexacro/
├── .claude/
│   ├── plugin.json                               # name, version 0.1.0
│   ├── commands/karpathy-rdb-nexacro.md
│   └── skills/karpathy-rdb-nexacro/
│       ├── SKILL.md
│       └── references/
│           ├── blueprint-input-contract.md
│           ├── endpoints-input-contract.md
│           ├── type-mapping-matrix.md
│           ├── form-layout.md
│           ├── overlay-policy.md
│           └── output-layout.md
├── scripts/
│   ├── form_gen.py                               # CLI entry
│   ├── blueprint_loader.py                       # N001
│   ├── endpoints_loader.py                       # N002 + infer
│   ├── type_mapper.py                            # PG → nexacro
│   ├── form_composer.py                          # xfdl 조립
│   ├── typedef_patcher.py                        # Services 패치
│   ├── menu_dataset_gen.py                       # dsMenu rows
│   └── revalidator.py                            # N001~N006
├── templates/
│   ├── form.xfdl.j2
│   ├── dataset.xml.j2
│   ├── search_field.xml.j2
│   ├── grid_format.xml.j2                        # cell.edittype 포함 (편집 가능 Grid)
│   ├── typedefinition_patch.xml.j2
│   └── menu_dataset.xml.j2
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── fixtures/
│       ├── golden_blueprint.yaml
│       ├── golden_endpoints.json
│       └── expected/<entity>.xfdl
└── README.md
```

## 5. Form 템플릿 (form.xfdl.j2 핵심)

2단 구조 — Search 상단 (60px) + 편집 가능 Grid 중단 (520px) + 버튼.

- `<Layout>` width=900, height=620
- `<Dataset id="dsSearch">` — PK / business key / NOT NULL 후보 컬럼으로 구성
- `<Dataset id="ds{Pascal}">` — Grid 의 단일 메인 dataset (편집 in-place)
- `<Grid binddataset="ds{Pascal}" autofittype="col">` — `<Format>` 의 각 `<Cell>` 에 컬럼별 `edittype` 지정
  - varchar/text → `edittype="text"`
  - numeric → `edittype="masknumber"`
  - date/timestamp → `edittype="date"`
  - char(1) + `*_yn` → `edittype="combo"` (combodataset = 인라인 Y/N)
  - boolean → `edittype="checkbox"`
  - PK / auto-key → `edittype="none"` (readonly)
- `<Script>`
  - `fn_search()` → `this.transaction("select", ".../select_datalist_map.do", "dsSearch=dsSearch", "output1=ds{Pascal}")`
  - `fn_add()` → `ds{Pascal}.addRow()` + 현재 row 로 Grid 포커스 이동 (PK 초기값: bigserial=공란, varchar(uuid)=공란, 사용자 입력 또는 server-side fill)
  - `fn_save()` → `_RowType_` 검사 후 `this.transaction("save", ".../save_datalist_map.do", "dataList=ds{Pascal}:U")`
  - `fn_delete()` → 선택 row `deleteRow()` + 저장 시 D 로 dispatch

## 6. Type Mapping Matrix (D6 확정)

PostgreSQL 타입 → (Dataset type, size, Search 컴포넌트, Grid cell `edittype`/`displaytype`, 비고). Edit panel 제거 (D1) — 편집은 Grid cell 에서 직접 수행.

| PG type | Dataset | size | Search 컴포넌트 | Grid `edittype` | Grid `displaytype` | 비고 |
| :-- | :-- | :-: | :-- | :-- | :-- | :-- |
| `bigserial`, `serial`, `bigint`, `integer` | `BIGDECIMAL` | — | `Edit` | `none` (pk) / `masknumber` | `number` | PK readonly |
| `varchar(n)`, `text` | `STRING` | n or 4000 | `Edit` | `text` | `text` | — |
| `char(1)` + name matches `*_yn` | `STRING` | 1 | `Combo` (Y/N/전체) | `combo` (inline Y/N) | `combotext` | 한국 컨벤션 |
| `char(n)` | `STRING` | n | `Edit` | `text` | `text` | — |
| `numeric(p,s)`, `decimal` | `BIGDECIMAL` | p | `Edit` | `masknumber` | `number` | — |
| `boolean` | `STRING` | 1 | `Combo` | `checkbox` | `checkbox` | Y/N 변환 |
| `date` | `STRING` | 8 | `Calendar` range | `date` | `date` | YYYYMMDD |
| `timestamp`, `timestamptz` | `STRING` | 14 | `Calendar` | `date` | `date` | YYYYMMDDHHMISS |
| `time` | `STRING` | 6 | `Edit` | `mask` (HH:MM:SS) | `text` | — |
| `json`, `jsonb` | `STRING` | 4000 | (검색 제외) | `text` | `text` (truncate) | — |
| `uuid` | `STRING` | 36 | `Edit` | `none` (pk) / `text` | `text` | — |
| **(미매핑)** | `STRING` | 100 | `Edit` | `text` | `text` | `warnings.md` 기록, `--strict` 시 exit 1 |

## 7. 검증 (Validators)

| ID | 검증 | 실패 조건 |
| :-- | :-- | :-- |
| **N001** | blueprint contract | `version != 1` / `validation.passed != true` |
| **N002** | endpoints.json contract | `version != 1` / entity 누락 / `method` ∉ `{select_datalist_map, save_datalist_map}` |
| **N003** | entity 대조 | blueprint.entities ↔ endpoints.entities 이름 1:1 일치 |
| **N004** | PK 존재 | 각 entity 에 `pk: true` 컬럼 ≥ 1 |
| **N005** | dsSearch 비공집합 | 각 entity 에 검색 가능 컬럼 ≥ 1 |
| **N006** | XML well-formed | 생성된 `*.xfdl` `*.xml` 모두 ElementTree 파싱 통과 |

## 8. 에러 처리 정책

| 계층 | 정책 |
| :-- | :-- |
| **CLI** | 모든 validator 실패는 stderr `[Nxxx] ...` + exit 1. 출력은 tmp dir → atomic move (rollback). |
| **Template** | Jinja `UndefinedError` 는 entity + column + 누락 키 포함해 re-throw. |
| **Type mapper 미매핑** | fallback (`STRING/Edit/100`) + `warnings.md` 1줄. `--strict` 시 exit 1. |
| **Overlay 충돌** | `<entity>.xfdl` 기존재 시 stop + `[N007]`. `--force` 시 `.bak` 백업 교체. |
| **endpoints.json 부재** | `[N002] not found` 안내, `--infer-endpoints` 우회. |

## 9. 테스트 전략

```
tests/
├── unit/        — loader / type_mapper / form_composer 단위
├── integration/ — golden xfdl byte-exact 비교, typedef patch idempotent, dsMenu rows
├── e2e/         — Stage 1→2→3→4 + scaffold + overlay (+ NEXACRO_LIBS_DIR 있을 때 mvn compile)
└── fixtures/    — golden_blueprint.yaml (customer/customer_address/customer_memo), expected/*.xfdl
```

- Jinja: `trim_blocks=True`, `lstrip_blocks=True`, lf 줄바꿈, indent 2
- 비결정성 토큰 (timestamp/uuid) 템플릿에서 제거
- e2e smoke: `xmllint --noout` 또는 Python ET 파싱 통과 종료조건

## 10. CLI 시그니처

```bash
karpathy-rdb-nexacro compile \
  --blueprint   <path>/_blueprint.yaml      # 필수
  --endpoints   <path>/endpoints.json       # 권장
  [--infer-endpoints]                       # endpoints 부재 시 추론
  --out         <dir>
  [--frame      packageN|minimal]           # 기본 packageN
  [--strict]                                # 타입 fallback 금지
  [--force]                                 # overlay 충돌 .bak 교체
```

## 11. Stage 3 v0.1.4 선결 작업 (Predecessor Patch)

Stage 3 가 emit 해야 할 추가 산출물:
- `<OUT_BACKEND>/endpoints.json` — 위 §4.2 스키마
- entity 당 (select_datalist_map, save_datalist_map) 2개 endpoint 행 고정
- `endpoint_base` = `/{entity_table_name}` (또는 controller `@RequestMapping` prefix)
- `context_path` = `application.yml` 의 `server.servlet.context-path` (기본 `/uiadapter`)

본 작업은 Stage 4 implementation 보다 **선행**되어야 함 (Stage 4 의 N002/N003 validator 가 의존).

## 12. 진행 단계 (Plan Outline)

| 순서 | 작업 | 산출 |
| :-: | :-- | :-- |
| 1 | Stage 3 v0.1.4 — endpoints.json emit | `OUT_BACKEND/endpoints.json` |
| 2 | Stage 4 plugin scaffold (`.claude/`, scripts/, templates/, tests/fixtures/) | repo 초기 |
| 3 | Stage 4 loaders + N001~N003 | `blueprint_loader.py`, `endpoints_loader.py`, `revalidator.py` |
| 4 | type_mapper + 단위 테스트 (12 카테고리) | `type_mapper.py` |
| 5 | form_composer + golden xfdl 1개 (customer) | byte-exact 통과 |
| 6 | dsMenu + typedef patcher | `menu_dataset_gen.py`, `typedef_patcher.py` |
| 7 | overlay.sh + e2e smoke | `.smoke/` Stage1→4 통과 |
| 8 | v0.1.0 release tag + 핸드오프 계약 문서 업데이트 | needs/Plugin참조/4 |

## 13. 후속 작업 (Out of Scope, v0.2+)

- D3 master-detail relation 자동화
- D6 사용자 정의 type override (config)
- `--lane jakarta|javax` 분기 (Stage 3 와 동조)
- `nexacro-build` 자동 호출 (xfdl → JS/HTML 빌드)
- frameLeft.xfdl schema 자동 추론 (현재는 `{menu_id, menu_pid, menu_nm, form_url, level}` 가정 — 플랜 Task 0 에서 nexacro-project-maker packageN scaffold 의 실제 schema 확인 필요)

## 14. 참조 문서

- 핸드오프: `needs/Plugin참조/3. Middle+Frontend - Stage 3→4 nexacro 핸드오프 계약.md`
- Stage 1 설계: `docs/superpowers/specs/2026-05-13-andrej-karpathy-rdb-skill-design.md`
- Stage 2 설계: `docs/superpowers/specs/2026-05-13-andrej-karpathy-rdb-ddl-design.md`
- Stage 3 설계: `docs/superpowers/specs/2026-05-13-stage3-mybatis-uiadapter-codegen-design.md`
- nexacro-fullstack-starter v0.6.0 SKILL.md (cache)
- nexacro-form-maker v1.7.0 binding-patterns.md (cache)
