---
type: design-spec
growth: 16
status: draft
created: 2026-05-20
authors: [aijasonmore]
baseline_tags:
  business-fullstack-creater: v0.6.0
  andrej-karpathy-rdb-skill: v0.4.0
  andrej-karpathy-rdb-ddl: v0.5.1
  andrej-karpathy-rdb-mybatis: v0.5.2
  andrej-karpathy-rdb-nexacro: v0.5.0
---

# Growth-16 — SHELL Pattern: Domain-Driven Nexacro Shell

## 1. 배경과 동기 (Why)

### 1-1. 사용자 의도 (verbatim, 보존)
> "반복되는 데이터를 효율적으로 관리하고 싶어서 andrej-karpathy의 지식 관리 방식을 적용하고 싶었다. ... 사용자가 요청하는 업무(도메인), 요소(entity)를 지식으로 쌓아서 결국 풍부한 Seeds를 만들어서 완성도 높은 결과물(war)를 제공하고 싶었다."

### 1-2. 트리거 (당세션 결정 맥락)
사용자 질문: "지금 frontend가 nexacro일 경우, 기존에 있는 `/nexacro-fullstack-starter` 를 통해서 만들어진 MDI방식의 UI를 사용한다. 이게 우리가 만드는 업무 domain에 딱 맞는것 같지는 않다."

조사 결과:
- `D:\AI\workspace\nexacroN-fullstack\.claude\rules\nexacro-fullstack-purpose.md` §7 — **"Out of Scope: 신규 도메인 추가 (e.g., 결제, 차트) — 현재 14-endpoint 범위 외"** 로 명시. 이 레포는 nexacro+Spring runner 매트릭스 시연용 고정 스코프 데모.
- `nxui/packageN/frame/*.xfdl` 8개는 도메인 인지 없는 순수 셸 스켈레톤 (frameMDI/frameLogin/frameLeft/frameMain/frameTop/frameBottom/frameWork/frameWorkTitle).
- 우리의 현재 `scripts/stage5_overlay.py` 는 **merge 모드만 지원** — starter 셸 위에 도메인 메뉴/typedef/xfdl 을 inject. starter 가 익숙한 팀에는 적합하지만, 도메인 단독 배포가 필요한 경우 starter 의 14-endpoint baseline 을 끌고 가야 함.

### 1-3. 문제 진술 (Problem)
- 도메인 단독으로 nexacro WAR 를 빌드/배포하려는 사용자는 starter 의 14-endpoint scaffolding 을 강제로 수입해야 함.
- starter 의 frame 셸은 widget/패턴 데모용 — 도메인 메뉴 구조와 다른 hard-coded 구조를 갖고 있어 배포 시 잉여 코드/리소스 동반.
- CLAUDE.md 3축 복리식 축적 원칙(Backend catalog / Middle templates / Frontend patterns) 에서 Frontend 축은 entity 단위 패턴(D2/F1/C1/L2/MD/TR/RO 7종) 만 누적 중 — **프로젝트 단위 셸 패턴이 없음**.

## 2. 목표와 비목표

### 2-1. 목표 (Goals)
G1. `karpathy-rdb-nexacro` 에 **SHELL 패턴**(8번째 패턴) 신규 도입 — variants: MDI / SDI 2종.
G2. `business-fullstack-creater/scripts/` 에 신규 UI overlay adapter `nexacro_shell_overlay.py` — `ui_overlay_registry.register("nexacro-shell", ...)`.
G3. CLI `--ui nexacro-shell --shell-mode {MDI|SDI}` 추가. 기본은 `--ui nexacro` (merge mode, 하위 호환).
G4. `_blueprint.yaml` 에 선택적 `shell:` 블록 — 도메인/메뉴/로그인 정책 선언. 미지정 시 합리적 기본 추론.
G5. 시드 도메인 1개(배송관리) 로 standalone WAR fixture 골든 테스트.
G6. nexacroN-fullstack 레포는 **읽기 전용** — 정책 §7 위반 없음.

### 2-2. 비목표 (Non-Goals)
NG1. 신규 Spring 백엔드 셸 — Stage 2/3 출력은 그대로 사용.
NG2. nexacroN-fullstack 의 `frame*.xfdl` 포팅/카피 — 라이선스/스코프 분리 유지. 신규 셸은 `karpathy-rdb-nexacro/patterns/SHELL/` 에서 처음부터 작성.
NG3. nexacrolib 자동 vendor — 사용자가 별도 라이브러리 경로 지정 (`--nexacrolib-from <path>`).
NG4. login/auth 비즈니스 — frameLogin 은 최소 form (`/uiadapter/login.do` 호출 골격)만.
NG5. 기존 `nexacro` adapter 의 동작 변경 — 모든 회귀 fixture 통과 유지.

## 3. 아키텍처 (How)

### 3-1. 컴포넌트 다이어그램
```
karpathy-rdb-nexacro/.claude/skills/karpathy-rdb-nexacro/patterns/SHELL/
├── manifest.yaml            # kind: shell, variants: [MDI, SDI]
├── frame_main.xfdl.j2       # entry frame
├── frame_mdi.xfdl.j2        # MDI workspace (variant=MDI)
├── frame_sdi.xfdl.j2        # SDI single-view (variant=SDI)
├── frame_left.xfdl.j2       # 도메인→엔티티 트리 menu
├── frame_top.xfdl.j2        # 헤더 (도메인 라벨)
├── frame_login.xfdl.j2      # 최소 login form
├── typedefinition.xml.j2    # 도메인 entity 컬럼에서 합성
├── packageN.xadl.j2         # entry point
└── README.md

business-fullstack-creater/scripts/
├── nexacro_shell_overlay.py # NEW — _nexacro_shell_overlay_run
├── stage5_overlay.py        # UNCHANGED (merge mode 유지)
├── ui_overlay_registry.py   # UNCHANGED — 동적 dispatch 이미 지원
├── scaffold_orchestrator.py # MODIFY — --shell-mode pass-through
└── scaffold_cli.py          # MODIFY — --shell-mode flag 추가
```

### 3-2. UI overlay dispatch 흐름 (v0.5 H4 registry 활용)
```
scaffold_cli --ui nexacro-shell --shell-mode MDI
  → scaffold_orchestrator.run(ui="nexacro-shell", shell_mode="MDI", ...)
    → stage5_overlay.run_overlay(ui="nexacro-shell", shell_mode="MDI", ...)
      → ui_overlay_registry.dispatch("nexacro-shell", ...)
        → nexacro_shell_overlay._nexacro_shell_overlay_run(...)
          1. target_dir (빈 또는 minimal core/) 검증
          2. SHELL/manifest.yaml 로드 → variant=MDI 선택
          3. frame_*.xfdl.j2 렌더 → target_dir/nxui/packageN/frame/
          4. typedefinition.xml.j2 렌더 (도메인 entity → Service 행 + Dataset typedef)
          5. packageN.xadl.j2 렌더
          6. Stage 3/4 출력 카피 (기존 _collect_* helpers 재사용)
          7. menu_injector 대신 frame_left.xfdl 을 처음부터 메뉴 트리로 emit
          8. nexacrolib 경로 안내 또는 --nexacrolib-from 으로 심볼릭 카피
          9. report 반환 (기존 report 키 호환 + shell_emitted: True)
```

### 3-3. `_blueprint.yaml` 의 `shell:` 블록 (신규 선택적 필드)
```yaml
shell:
  kind: SHELL            # 고정값
  variant: MDI           # MDI | SDI | <사용자 등록 variant id>
  title: 배송관리 시스템
  login:
    enabled: true        # false면 frameLogin 생략 + frameMain 직진입
    template: minimal    # minimal | none | <등록된 login template id>
  menu:
    root_label: 업무 메뉴
    domains:
      - id: 배송관리
        label: 배송 관리
        sort: 10
        entities: [delivery, courier, delivery_tracking]
      # 미지정 시 _blueprint.yaml 의 entities 에서 domain 별로 자동 그룹핑
    extensions:                    # 성장 슬롯: 도메인 외 사용자 정의 메뉴 행
      - id: dashboard
        label: 대시보드
        sort: 5
        target: nxui/packageN/_custom_/dashboard.xfdl   # 사용자 작성 form
      - id: settings
        label: 설정
        sort: 999
        target: nxui/packageN/_custom_/settings.xfdl
  typedef:                         # 성장 슬롯: 14-endpoint 외 커스텀 service
    extra_services:
      - prefixid: report
        url: /uiadapter/report/
      - prefixid: external
        url: https://api.partner.example.com/
  frame_overrides:                 # 성장 슬롯: 사용자 frame 으로 교체
    frame_top: ./local_frames/my_top.xfdl     # project-local 우선
    # frame_left: ... (지정 시 SHELL 의 frame_left.xfdl.j2 무시)
  branding:
    header_text: My Company
    favicon: null
```

**확장 슬롯 정책**:
- `menu.extensions` 는 자동 메뉴 트리에 merge (sort 키로 정렬)
- `typedef.extra_services` 는 합성된 `<Services>` 노드에 append
- `frame_overrides` 는 frame 렌더 우선순위: **project local > skill local > global catalog**

`shell:` 블록이 없으면 다음 기본값 추론:
- variant: MDI
- login.enabled: true, template: minimal
- menu: blueprint entities 의 `domain` 배열에서 자동 그룹
- title: 첫 도메인 라벨 + " 시스템"

### 3-4. SHELL/manifest.yaml 스키마 (8번째 패턴)
```yaml
pattern: SHELL
kind: shell                    # 기존 entity-level pattern 과 구분
applies_to: project            # entity 가 아닌 project 단위
extensible: true               # 성장 슬롯: 사용자 등록 variant 허용
variants:
  - id: MDI
    display: Multi-Document Interface
    frames: [frame_main, frame_mdi, frame_left, frame_top, frame_login]
    builtin: true
  - id: SDI
    display: Single-Document Interface
    frames: [frame_main, frame_sdi, frame_left, frame_top, frame_login]
    builtin: true
  # 사용자 등록 variant 예시 (다음 프로젝트가 contribute 또는 local 등록)
  # - id: TAB
  #   display: Tabbed Workspace
  #   frames: [frame_main, frame_tab, frame_left, frame_top, frame_login]
  #   builtin: false
  #   source: project-local | skill-local | global-catalog
inputs:
  required: [blueprint.entities, blueprint.shell.menu]
  optional: [blueprint.shell.login, blueprint.shell.branding, blueprint.shell.frame_overrides]
outputs:
  - nxui/packageN/frame/*.xfdl
  - nxui/packageN/typedefinition.xml
  - nxui/packageN/packageN.xadl
version: 1
migration:
  # frame_signature 가 변경되어 v2 가 필요한 경우 정책
  policy: "blueprint.shell.manifest_version 명시 시 그 버전 강제, 미지정 시 최신"
  v1_to_v2_breaking:
    # 향후 v2 도입 시 채워질 호환 깨지는 frame 목록 (현재는 빈)
    - placeholder
```

**Variant 확장 절차** (사용자가 신규 variant 등록):
1. (local) `<project>/.karpathy-rdb-nexacro/patterns/SHELL/variants/<ID>/` 에 `frame_*.xfdl.j2` 작성 + manifest entry 추가
2. (global) `/karpathy-rdb-nexacro contribute --kind shell-variant <ID>` 로 skill 패턴에 환류 (Phase 후속)
3. dispatch 시 우선순위: **project local > skill local > global catalog**

### 3-5. Pattern_loader 확장
기존 `pattern_loader.resolve(name)` 은 entity-level pattern 만 다룸. SHELL 은 다음과 같이 구분:
- `pattern_loader.resolve_shell(variant: str)` — 신규 함수, manifest.yaml 로드 + variant 검증 + frame 목록 반환.
- variant 미발견 시 fallback: project local → skill local → global catalog 순회.
- 엔티티 pattern resolve 경로는 unchanged.

### 3-6. Entity ↔ Shell Wiring (성장 슬롯)

SHELL 은 entity 패턴(D2/F1/C1/L2/MD/TR/RO) 과 다음과 같이 연결:

| 트리거 | MDI 동작 | SDI 동작 |
|---|---|---|
| 사용자가 frame_left 메뉴에서 entity 클릭 | 신규 work tab 으로 entity 의 기본 패턴 xfdl open (frameMDI 영역) | frame_main 의 work 영역 swap (이전 form unload) |
| entity 의 기본 패턴 결정 | `blueprint.entities[*].pattern` (이미 존재) 그대로 사용 | 동일 |
| L2 master-detail 패턴 entity | 단일 work tab 안에서 leftPane + detail | 단일 work 영역 안에서 좌우 split |
| MD 멀티-detail | 탭 그리드 1개 + detail | 동일 |

**Wiring 정의 위치**: `SHELL/manifest.yaml` 에 `entity_open_strategy:` 신규 필드(향후 v2).
**현재 v1**: 하드코딩된 strategy = "open as work tab in MDI / replace work area in SDI". 사용자 override 는 `blueprint.shell.menu.entities[*].open_as` 로 (예: `open_as: dialog`).

이 wiring 이 명시되어야 entity 패턴이 추가될 때 SHELL 패턴이 자동으로 그 entity 를 메뉴 + open 동작에 흡수할 수 있다 — **3축 복리식 성장에서 Frontend 축의 누적 효과**.

## 4. 변경 영향도 (Blast Radius)

| 레포 | 변경 | 회귀 위험 | 완화 |
|---|---|---|---|
| `karpathy-rdb-nexacro` | `patterns/SHELL/` 신규 + `pattern_loader.resolve_shell` | 낮음 (신규 함수) | 기존 7 패턴 resolve 회귀 fixture 그대로 통과 |
| `business-fullstack-creater/scripts/nexacro_shell_overlay.py` | 신규 파일 | 없음 | 신규 adapter, 기존 nexacro adapter 미수정 |
| `scripts/scaffold_orchestrator.py` | `--shell-mode` kwarg pass-through | 낮음 | 기본값 None, 기존 호출부 무영향 |
| `scripts/scaffold_cli.py` | `--shell-mode` 플래그 + `--nexacrolib-from` | 낮음 | optional, default None |
| `karpathy-rdb-skill` | blueprint-spec.md 에 `shell:` 블록 선택 필드 명시 | 매우 낮음 | 선택 필드, 기존 blueprint 그대로 통과 |
| `nexacroN-fullstack` | **변경 없음** | 0 | 정책 §7 보존 |

## 5. 데이터 흐름 (End-to-End)

### 5-1. Standalone 빌드 시나리오 (배송관리 1도메인)
```
1. 사용자: blueprint.yaml 작성 (배송관리 4 entity + shell.variant=MDI)
2. /scaffold --ui nexacro-shell --shell-mode MDI --target ./out-shipping
3. Stage 1~4 정상 실행 → out_dir 에 3-mybatis/, 4-nexacro/ 생성
4. Stage 5: nexacro_shell_overlay 디스패치
   - target_dir (빈) 에 nxui/packageN/ 트리 생성
   - SHELL/frame_*.xfdl.j2 렌더 → frame/ 배치
   - typedefinition.xml 합성 (entity 컬럼 → ColumnInfo Dataset typedef)
   - Stage 3 Java 출력 → src/main/java/<target_pkg>/배송관리/ 카피 (기존 _rewrite_java 재사용)
   - Stage 4 xfdl forms → nxui/packageN/배송관리/ 카피
5. 사용자: --nexacrolib-from <path> 로 nexacrolib 디렉터리 심볼릭 카피
6. mvn package → WAR 빌드 가능
```

### 5-2. Merge 빌드 시나리오 (변경 없음)
```
/scaffold --ui nexacro --target <nexacroN-fullstack clone>
→ 기존 stage5_overlay._nexacro_overlay_run 호출 (그대로 동작)
```

## 6. 위험과 완화

| ID | 위험 | 영향 | 완화 |
|---|---|---|---|
| R1 | frame_login.xfdl.j2 의 `/uiadapter/login.do` 와이어업 누락 | 로그인 실패 | 14-endpoint spec 의 #1 path 만 정확히 호출하는 최소 form 으로 한정. golden test 에서 transaction 호출 코드 검증 |
| R2 | typedefinition.xml 합성 시 nexacrolib 의 표준 Dataset 누락 | 런타임 에러 | manifest.yaml 에 `required_lib_datasets` 명시 + 합성 시 자동 포함. golden xml 비교 |
| R3 | nexacrolib 의존 — 사용자 환경 의존 | 빌드 실패 | `--nexacrolib-from` 미지정 시 명시적 에러 + README 에 vendor 경로 안내 |
| R4 | SHELL 패턴이 entity 패턴과 혼동 | resolve 충돌 | `kind: shell` + `applies_to: project` 로 구분. `resolve_shell` 별도 함수 |
| R5 | SDI variant 적용 가능 도메인이 명확하지 않음 | 활용도 저하 | Phase 1 에서는 MDI 우선 구현, SDI 는 manifest 만 + Phase 2 에서 골든 |
| R6 | 한국어 디렉터리명 (배송관리) → WAR 빌드 시 인코딩 이슈 | mvn 실패 | 이미 v0.4.2 G3 에서 검증됨 (Korean-domain golden 통과). 동일 path 처리 재사용 |
| R7 | nexacroN-fullstack starter 가 향후 정책 변경(예: 14→16 endpoint) 시 SHELL 의 typedef extra_services 와 충돌 | runtime endpoint 미스매치 | (a) `SHELL/manifest.yaml` 에 `compatible_starter_version: ">=1.x"` 명시. (b) starter freeze tag(v0.x) 와 SHELL manifest 의 호환성 매트릭스를 `docs/compat-matrix.md` 로 누적. (c) `--ui nexacro-shell` 은 starter 와 독립이므로 정책 변경의 직접 영향은 없으나, merge 회귀 fixture 가 starter 버전 변경을 감지하면 알람 |

## 7. 결정과 트레이드오프 (Decisions)

### D1. 신규 adapter vs 기존 adapter 모드 확장
- **선택**: 신규 adapter (`nexacro-shell`)
- **이유**: v0.5 H4 의 registry 패턴이 이미 다중 adapter 를 가정. merge/standalone 의 코드 경로가 50%+ 다름(target 가정 자체가 다름). 분리 시 회귀 면적 0.
- **대안 기각**: `--shell-mode` kwarg 를 기존 `_nexacro_overlay_run` 에 추가 → 단일 함수가 너무 비대해지고, "기존 동작 절대 불변" 보장이 어려워짐.

### D2. SHELL 을 패턴으로 vs 별도 컨셉으로
- **선택**: 패턴(`patterns/SHELL/`)
- **이유**: CLAUDE.md 3축 중 Frontend 축이 `patterns/` 누적이 정석. 8번째 패턴으로 들어가야 복리식 축적 원칙 위배 없음. `kind: shell` 로 entity 패턴과 구분.
- **대안 기각**: `templates/shell/` 신규 디렉터리 → 패턴 디렉터리 vs 템플릿 디렉터리 분기가 생겨 일관성 깨짐.

### D3. blueprint 의 `shell:` 블록 위치
- **선택**: `_blueprint.yaml` 최상위 선택 필드
- **이유**: 도메인/엔티티와 같은 진실의 근원(Stage 1) 위치 일관성. CLI 플래그(`--shell-mode`)는 blueprint 의 default override.
- **대안 기각**: 별도 `shell.yaml` 파일 → Karpathy 단일 소스 원칙 위배.

### D4. variants 2종 한정 (MDI/SDI)
- **선택**: 초판 2종
- **이유**: 실 사용자 요청은 MDI 가 대다수. SDI 는 단일 도메인 대시보드용. tab/wizard 류는 향후 (v0.7+).

### D5. nexacrolib 자동 vendor 거부
- **선택**: 사용자 명시 경로 (`--nexacrolib-from`) 만 지원
- **이유**: 라이선스/배포 경계. nexacroN-fullstack 도 `nxui/packageN/nexacrolib/` 에 vendor 하지만 그것은 starter 의 책임. 우리는 메타 도구.

## 8. Phase 분할 (Implementation Plan Preview)

상세 plan 은 `2026-05-20-growth-16-shell-pattern-plan.md` 에서 정의. 본 spec 은 phase 윤곽만:

| Phase | 산출물 | Gate | 미니 5축 예측 (1·2·3·4·5) |
|---|---|---|---|
| P1 | SHELL/manifest.yaml + frame_*.xfdl.j2 (MDI) + pattern_loader.resolve_shell | pytest: resolve_shell 단위 + 7 패턴 회귀 0 | 3·3·5·2·5 (자산 신규, WAR 미완) |
| P2 | nexacro_shell_overlay.py + ui_overlay_registry 등록 + 단위 테스트 | pytest: overlay 단위 + 기존 nexacro adapter 회귀 0 | 4·3·4·3·5 |
| P3 | scaffold_orchestrator + scaffold_cli --shell-mode wiring | pytest: CLI 인자 파싱 + 기존 --ui nexacro 회귀 0 | 4·3·3·3·5 |
| P4 | 배송관리 1도메인 standalone golden E2E (xfdl/typedef/packageN.xadl byte diff) | mvn package WAR 빌드 성공 (옵션) | 5·5·4·5·5 |
| P5 | SDI variant manifest 등록 + golden | pytest: SDI 골든 통과 | 5·5·5·5·5 |
| P6 | blueprint-spec.md (`shell:` 블록) + USER-GUIDE.md + 5축 자체 리뷰 | 평균 ≥ 4 PASS | 5·5·5·4·5 |

각 Phase 종료 시 5축 자체 리뷰(미니) 수행 — 평균 < 3 발견 시 다음 Phase 진입 전 멈추고 보고. Per-file commit 필수.

## 9. 5축 자체 리뷰 예측 (CLAUDE.md 기준)

| 축 | 점수 | 근거 |
|---|---|---|
| 1. 반복 데이터 효율 관리 | 5 | blueprint 한 곳에서 frame/menu/typedef 모두 emit, 도메인 메타 중복 0 |
| 2. 도메인·엔티티 지식 누적 | 5 | 12 도메인 preset 이 셸에 자동 반영, 도메인 추가 시 메뉴 자동 풍부화 |
| 3. 풍부한 Seeds | 4 | SHELL 패턴 디렉터리 자체가 신규 자산, MDI/SDI 2 variant |
| 4. 완성도 높은 WAR | 4 | standalone WAR 빌드 가능 (R3 의 nexacrolib 경로 의존 -1) |
| 5. Karpathy 정신 | 5 | 파일 기반, manifest + 템플릿, 명시적 dispatch, 자동 머지 없음 |

**예상 평균 4.6 / PASS 임계 3.0 — 진행 권장**

## 10. 검증 기준 (Acceptance)

V1. SHELL/manifest.yaml + frame_*.xfdl.j2 (최소 5종) 작성, `resolve_shell("MDI")` 가 frame 목록 반환.
V2. `nexacro_shell_overlay._nexacro_shell_overlay_run` 단위 테스트: 빈 target_dir → 7 파일 emit.
V3. `ui_overlay_registry.dispatch("nexacro-shell", ...)` 이 신규 adapter 호출.
V4. `scaffold_cli --ui nexacro-shell --shell-mode MDI` 종단 실행 시 exit 0 + scaffold-report.md 생성.
V5. 배송관리 1도메인 골든 fixture: 생성된 xfdl/typedef 가 골든 byte 일치.
V6. 기존 `--ui nexacro` 회귀 fixture 100% PASS (변경 0 보장).
V7. nexacroN-fullstack 레포 변경 0 (git diff empty).
V8. 5축 자체 리뷰 평균 ≥ 3.

## 11. 후속 (Future Work, out of scope)

- F1. SHELL-TAB / SHELL-WIZARD variants
- F2. OAuth/SSO frameLogin 템플릿 (현재는 minimal `/uiadapter/login.do`)
- F3. 다국어 메뉴 라벨 (현재는 도메인 라벨 단일)
- F4. Theme/branding 풀 지원 (현재는 header_text + favicon 만)
- F5. React shell pattern (`ui="react-shell"`) — 동일 SHELL/manifest.yaml 의 frame 정의를 React 페이지로 렌더
- F6. **`/karpathy-rdb-nexacro contribute --kind shell` 의 글로벌 카탈로그 승급 경로**:
  - 사용자가 신규 SHELL variant 또는 frame_override 를 project-local 에 작성
  - `contribute --kind shell-variant <ID>` 또는 `contribute --kind frame-override <name>` 으로 skill 패턴 디렉터리로 환류
  - skill 누적이 일정 임계치(예: 동일 variant 가 3 프로젝트 이상에서 등장) 도달 시 글로벌 카탈로그로 promote
  - 이 경로가 있어야 SHELL 패턴이 "한번 만들고 끝" 이 아닌 **3축 복리식 성장의 Frontend 축 실체** 가 됨
  - Phase 후속(별도 spec) 으로 다룸 — 본 spec scope 아님

## 12. 참조

- 정렬 리뷰: `docs/superpowers/specs/2026-05-15-karpathy-alignment-review.md`
- nexacroN-fullstack 정책: `D:\AI\workspace\nexacroN-fullstack\.claude\rules\nexacro-fullstack-purpose.md`
- 14-endpoint 계약: 위 정책 §2
- UI overlay registry: `D:\AI\workspace\business-fullstack-creater\scripts\ui_overlay_registry.py`
- 기존 nexacro adapter: `D:\AI\workspace\business-fullstack-creater\scripts\stage5_overlay.py:134-379`
- 패턴 디렉터리: `D:\AI\workspace\andrej-karpathy-rdb-nexacro\.claude\skills\karpathy-rdb-nexacro\patterns\<NAME>\manifest.yaml`
