# UI Adapter Contract (v0.5)

**Status:** v0.5 H4 (overlay registry + react skeleton) — 2026-05-19
**Scope:** Front-end UI 어댑터 (Stage 4 = `andrej-karpathy-rdb-nexacro` + Stage 5 overlay)
**Reference impls:** `nexacro` (D2 / F1 / C1 pattern + Stage 5 starter overlay), `react` (v0.5 H4 skeleton — endpoints fetch hooks)

> "front-end UI: Stage 4(nexacro) + Stage 4'(외부 starter) 외에 React/Vue 어댑터 슬롯 정의." — USER-GUIDE §6.4 v0.5

---

## 1. 목적

같은 blueprint + `endpoints.json` 에서 **다른 UI 스택** (React, Vue, Vanilla HTML …) 의 화면을 생성 가능하게 한다. UI 어댑터의 핵심 결정 두 가지:

1. **렌더 슬롯 (Stage 4)**: blueprint + pattern → UI 파일 변환
2. **오버레이 슬롯 (Stage 5)**: 생성된 UI 를 외부 starter 프로젝트에 병합

두 슬롯은 직교 — 어댑터는 둘 중 하나 또는 둘 다 구현 가능.

---

## 2. 어댑터 슬롯 — UI 종류 식별자

`--ui` CLI 플래그 (v0.5 H4 도입, `scaffold_cli.py:--ui`) 의 값:

| ui | 도입 | 슬롯 |
|:-:|:-:|:-:|
| `nexacro` | v0.1 / H4 default | 렌더 (.xfdl) + 오버레이 (Stage 5 nexacro-starter) |
| `react` ✅ | v0.5 H4 | 오버레이 (frontend/src/api/`<entity>`.ts fetch 모듈) — 렌더(.tsx)는 v0.6+ |
| `nexacro-only` *(예정)* | v0.6 | 렌더만 (오버레이 SKIP) — `--target-project` 생략으로 현재도 가능 |
| `vue` *(예정)* | v0.6 | 렌더 (.vue) + 오버레이 (Vite starter) |

---

## 3. 렌더 슬롯 — Pattern 시스템

위치: `andrej-karpathy-rdb-nexacro/.claude/skills/karpathy-rdb-nexacro/patterns/<PATTERN>/`

각 패턴 = **2-file 묶음**:

| 파일 | 역할 |
|:-:|:-:|
| `form.xfdl.j2` *(또는 ui 별 확장자)* | UI 본체 템플릿 |
| `manifest.yaml` | 패턴 메타 — 적용 가능 entity kind, 컬럼 요구 사항 |

### 3.1 현재 Reference Patterns (nexacro)

| pattern | 의미 | 적용 |
|:-:|:-|:-:|
| `D2` | dual-grid (master grid + detail form) | 표준 CRUD |
| `F1` | single form (1-tier) | 단일 entity 단일 record |
| `C1` | card-1-tier (카드 레이아웃) | 마스터 데이터 |

### 3.2 Pattern 해석 — `resolve_pattern`

위치: `andrej-karpathy-rdb-nexacro/scripts/pattern_loader.py:18`

```python
def resolve_pattern(name, bundled_root, global_root=None) -> ResolvedPattern
```

탐색 순서: (1) bundled (skill 패키지), (2) global (`~/.karpathy-rdb/patterns/`). `/contribute --kind pattern` 으로 global 누적.

→ **모든 UI 어댑터는 동일한 pattern 해석 메커니즘 재사용** (bundled + global fallback).

### 3.3 새 UI 어댑터의 패턴 디렉터리 컨벤션

```
karpathy-rdb-<ui>/.claude/skills/karpathy-rdb-<ui>/patterns/<PATTERN>/
  ├── form.<ext>.j2       # ui 별 확장자 — react: .tsx.j2, vue: .vue.j2
  └── manifest.yaml
```

`manifest.yaml` 최소 필드:

```yaml
name: D2
applicable_to: [crud, master_detail]   # entity kind 화이트리스트
required_columns: [pk]                 # 패턴이 요구하는 컬럼 종류
generated_files:                       # 출력 산출물 목록 (어댑터별 다름)
  - "{{ snake }}_form.tsx"
  - "{{ snake }}_form.css"
```

`generated_files` 가 어댑터별 다른 부분의 유일한 차이점 — 본체 (entity 컨텍스트, manifest 스키마) 는 모든 UI 어댑터 공유.

---

## 4. 입력 컨텍스트 — `endpoints.json` 소비

모든 UI 어댑터는 `endpoints.json` (Stage 3 산출물) 을 읽어 fetch 코드를 만든다:

```json
{
  "version": "0.1.4",
  "endpoints": {
    "customer": {
      "select_datalist_map": {"method": "POST", "path": "/uiadapter/customer/select_datalist_map"},
      "insert_data":          {"method": "POST", "path": "/uiadapter/customer/insert_data"},
      ...
    }
  }
}
```

어댑터별 차이:

| ui | fetch 메커니즘 | 응답 envelope 처리 |
|:-:|:-:|:-:|
| nexacro | `Transaction(svcid, ...)` (uiadapter 형식) | `ds_<name>` Dataset 자동 바인딩 |
| react | `fetch()` + SWR/React Query | `data.<entity>` 추출 |
| vue | `fetch()` + Pinia | `data.<entity>` 추출 |

**계약**: `endpoints.json` schema 는 모든 UI 어댑터에 안정적. v0.1.4+ 호환 깨짐 시 모든 어댑터 영향 → minor bump 필요.

---

## 5. 오버레이 슬롯 — Stage 5

위치: `business-fullstack-creater/scripts/stage5_overlay.py` (v0.4 Phase F + v0.4.2 prefix 외부화 완료)

현재 Stage 5 는 **nexacro 전용** 으로 하드코딩되어 있다. v0.5 H4 에서 어댑터화 필요:

### 5.1 현재 책임 (nexacro overlay 한정)

1. Java 패키지 rewrite (`com.example.<slug>` → `com.nexacro.uiadapter.<slug>`, v0.4.2 외부화 완료)
2. `frameLogin.xfdl` 의 `dsSample` Dataset 에 메뉴 row 주입
3. `typedefinition.xml` `<Services>` 에 entity 서비스 항목 머지

### 5.2 v0.5 H4 어댑터화 후 분할 ✅

H4 에서 dispatch 가 `if/elif` 가 아닌 **레지스트리** 로 일반화되었다:

```python
# scripts/stage5_overlay.py
def run_overlay(*, ui: str = "nexacro", **kwargs) -> dict:
    return ui_overlay_registry.dispatch(ui, **kwargs)

ui_overlay_registry.register("nexacro", _nexacro_overlay_run)
# scripts/react_overlay.py:
ui_overlay_registry.register("react", run)
```

→ 새 UI 추가 = 모듈 1개 + `register()` 1줄. `stage5_overlay.py` 본체는 무수정.

각 어댑터의 책임은 §5.1 처럼 명시. 모든 어댑터 공통:

- 1-shot `.bak` 백업 정책 (idempotent)
- conflict-scan-first (변경 전 모든 충돌 검출, 부분쓰기 금지)
- `OverlayResult` 구조 (`java_copied`, `xml_modified`, `conflicts`, …)

### 5.3 오버레이 어댑터 슬롯 (등록 인터페이스, v0.5 H4 도입 ✅)

H4 가 채택한 실제 시그니처 — Protocol 보다 가벼운 callable 규약:

```python
def adapter_run(
    *, out_dir, target_dir, domain_slug, domain_label, service_pascal,
    blueprint_entities, overlay_force=False,
    source_pkg_prefix="com.example", target_pkg_prefix="com.nexacro.uiadapter",
) -> dict: ...

ui_overlay_registry.register("<ui-name>", adapter_run)
```

반환 dict 의 공통 키 (모든 어댑터):
`java_copied`, `resources_copied`, `xfdl_copied`, `backed_up`,
`renamed_imports`, `menu_warning`, `typedef_added`, `conflicts`.
어댑터별 추가 키는 자유 (`react_api_written` 등).

---

## 6. 호환 버전

| 계약 버전 | Stage 4 release | 변경 내용 |
|:-:|:-:|:-|
| **1** | v0.1.0 | nexacro 단일 어댑터, pattern 분기 없음 |
| **1.1** | v0.3.0 Phase C | D2/F1/C1 pattern 시스템, manifest.yaml |
| **1.2** | v0.4.1 (Phase F) | Stage 5 overlay (nexacro 전용) |
| **1.3** | v0.4.2 | overlay package prefix 외부화 |
| **2** ✅ | v0.5.0 H4 | `--ui` 플래그, overlay 레지스트리 분할 (`ui_overlay_registry`), react 어댑터 스켈레톤 (fetch hooks) |

---

## 7. 어댑터별 회귀 테스트 의무

| 테스트 | 목적 |
|:-:|:-:|
| `test_<ui>_pattern_resolve.py` | pattern 해석 (bundled + global) |
| `test_<ui>_render_<pattern>.py` | 각 pattern 의 골든 fixture 매치 |
| `test_<ui>_endpoints_consume.py` | endpoints.json 의 모든 9 메서드 fetch 코드 생성 |
| `test_<ui>_overlay.py` *(오버레이 어댑터)* | conflict scan + .bak 백업 + idempotent |

---

## 8. Karpathy 정신 가드레일

- **패턴 카탈로그 공유**: 모든 UI 어댑터가 같은 pattern 이름 (D2/F1/C1) 사용 — 의미적 일관성. 누적된 patterns/ 가 어댑터 추가 시 즉시 활용됨.
- **endpoints.json 단일 진실 원천**: UI 가 바뀌어도 fetch 표면은 동일 (안정 인터페이스).
- **오버레이는 idempotent**: 같은 입력 두 번 적용 → 같은 결과 (Stage 5 골든 fixture 가 강제).
- **단방향**: UI 어댑터는 starter 프로젝트의 런타임 상태를 모름 (빌드 타임 파일 변환만).

---

## 9. 계약 위반 시그널

1. UI 어댑터가 자체 endpoints schema 정의 → endpoints.json 호환 깨짐
2. pattern manifest.yaml 키가 어댑터별 다름 → 패턴 공유 불가
3. Stage 5 overlay 가 conflict-scan 전에 파일 쓰기 → 부분쓰기 사고
4. .bak 백업 정책 위반 (다회 적용 시 .bak.bak 생성) → idempotent 위반

---

## 10. H4 환류 — Reference Implementation 결과

H4 에서 `react` 어댑터 스켈레톤이 reference impl 으로 등록되며 다음이 드러나 v2 계약에 반영:

| 항목 | 변경 | 영향 |
|:-:|:-|:-|
| dispatch 방식 | `if/elif ui == ...` (계획) → `ui_overlay_registry.register()` + `dispatch()` | 새 UI 추가 시 `stage5_overlay.py` 무수정 (모듈 1개 + register 1줄) |
| 어댑터 시그니처 | `Protocol` (계획) → 평이한 keyword-only callable | typing 의존 없음, 테스트 시 monkeypatch 용이 |
| 반환 dict | nexacro 만 정의 → **공통 키 8개 + 어댑터별 키 자유** | 호출부가 `report.get("react_api_written", [])` 등으로 안전하게 분기 |
| 충돌 정책 | nexacro 만 명시 → 모든 어댑터 conflict-scan + 1-shot `.bak` 강제 | react 테스트가 idempotent 백업 동작 검증 |
| react 산출물 범위 | "D2 pattern + fetch hook" (계획) → **fetch hook 만** (skeleton) | 풀 .tsx pattern 은 v0.6 — endpoints 계약 일반화 능력은 이미 실증 |

### 10.1 회귀 테스트 추가 (`tests/`)

- `test_ui_overlay_registry.py` — register/dispatch, 미등록 ui KeyError, 3rd-party 등록, run_overlay default 디스패치
- `test_react_overlay.py` — 엔티티당 1 모듈 emit, endpoint path 포함, conflict-scan abort, `overlay_force` 1-shot .bak, report shape, 레지스트리 경유 dispatch

`pytest` (creater 8 파일): 48 passed (기존 38 + H4 신규 10). 회귀 0.

### 10.2 CLI 진입점

| 위치 | 변경 |
|:-|:-|
| `business-fullstack-creater/scripts/scaffold_cli.py` | `--ui` choices=("nexacro","react"), default "nexacro" |
| `business-fullstack-creater/scripts/scaffold_orchestrator.py` | `ScaffoldArgs.ui` 필드 + `run_overlay(ui=args.ui, ...)` pass-through + scaffold-report.md 에 `ui` 행 |
| `business-fullstack-creater/scripts/stage5_overlay.py` | `run_overlay(*, ui="nexacro", **kwargs)` 디스패처. `_nexacro_overlay_run` 으로 내부 로직 분리. `import react_overlay` 시도 (옵션) |
| `business-fullstack-creater/scripts/ui_overlay_registry.py` *(신규)* | `REGISTRY` dict + `register()` / `dispatch()` / `registered()` |
| `business-fullstack-creater/scripts/react_overlay.py` *(신규)* | endpoints.json 읽어 `frontend/src/api/<entity>.ts` 생성 |

### 10.3 잔여 갭

| Gap | 후속 milestone |
|:-:|:-|
| react 본격 pattern 시스템 (D2/F1/C1 .tsx.j2 + manifest.yaml) | v0.6 — Stage 4 reuse 가능성 검토 |
| vue / svelte 어댑터 | v0.6 — H4 의 register() 한 줄 패턴 그대로 |
| react 어댑터의 SWR / React Query 등 fetch 백엔드 선택지 | v0.6 — manifest 로 외부화 |
| Stage 4 와 Stage 5 react adapter 의 책임 분리 (현재는 Stage 5 가 fetch 전부 담당) | v0.6 |
