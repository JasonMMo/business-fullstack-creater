# Adapter Contracts (v0.5)

> **"어댑터 계약 먼저, 어댑터 두 번째."** — USER-GUIDE §6.4 v0.5

이 디렉터리는 v0.5 어댑터화의 **계약 (contract) 문서** 를 보관한다. 새 어댑터 (DB 엔진, lane, UI 스택) 를 추가하려는 사용자 / AI 가 먼저 읽는 위치.

---

## 3 계약 (Tier별)

| Tier | 계약 | Stage | Reference impls | 슬롯 |
|:-:|:-:|:-:|:-:|:-:|
| Back-end DB | [backend-contract.md](./backend-contract.md) | Stage 2 (`rdb-ddl`) | postgres, hsqldb | `Dialect` dataclass + 5 .j2 templates |
| Middle service | [service-contract.md](./service-contract.md) | Stage 3 (`rdb-mybatis`) | nexacro, vanilla | `lane` 식별자 + 3 변형 templates |
| Front-end UI | [ui-contract.md](./ui-contract.md) | Stage 4 (`rdb-nexacro`) + Stage 5 overlay | nexacro (D2/F1/C1) | pattern + UIOverlayAdapter |

---

## 왜 계약을 먼저 쓰나

1. **누적이 가능해진다.** 각 어댑터가 독립으로 만들어지면서도 catalog/preset 누적 메커니즘은 직교적으로 동작. 어댑터 늘어남 ≠ catalog 분기 늘어남.
2. **다음 어댑터의 노력이 예측 가능해진다.** "MySQL 추가 = `Dialect` 인스턴스 1개 + 5 .j2 = ~1일" — 계약이 work envelope 을 박스화.
3. **회귀 자물쇠가 명확해진다.** 계약별 회귀 테스트 목록 (`§7`) 이 정의되어 PR 거절 기준이 사전 합의됨.
4. **Karpathy 정신 보존.** 계약은 모두 "파일 기반 + 단방향 + idempotent" 를 명시 요구 — 어댑터 늘어도 LLM 컴파일러 모델 유지.

---

## 호환 버전 관리 (3 계약 공통)

- **minor bump** (1 → 1.1): 선택 필드 추가, default 로 기존 어댑터 통과
- **major bump** (1.x → 2): 필수 필드/시그니처 변경, 모든 어댑터 마이그레이션

각 계약 문서 `§6` 표가 진실. 호환 깨지는 변경은 모든 어댑터의 회귀 fixture 가 강제 검출.

---

## v0.5 phase 진행표

| Phase | 산출물 | 상태 |
|:-:|:-|:-:|
| **H1** | 3 contract 문서 + 본 README | ✅ 2026-05-19 |
| **H2** | MySQL 어댑터 (backend contract 실증) | 대기 |
| **H3** | jakarta/javax lane + suffix 일반화 (service contract v2) | 대기 |
| **H4** | `--ui` flag + Stage 5 overlay 분할 + react 스켈레톤 (ui contract v2) | 대기 |

각 phase 는 v0.2~v0.4 와 동일하게 **Milestone Gate 5축 자체 리뷰** 통과 조건. 게이트 문서: `docs/superpowers/specs/2026-05-19-v0.5-phase-h<N>-mh<N>-gate.md`

---

## 어댑터 작성자 체크리스트

1. 해당 tier 의 계약 문서 (`§2 슬롯`, `§3 템플릿`, `§4 등록 절차`) 정독
2. 어댑터 식별자 결정 (예약어 충돌 회피)
3. 슬롯 구현 (Dialect / lane / UI 별)
4. 회귀 테스트 작성 (`§7` 표 전부)
5. golden fixture 등록
6. CLI choices 확장 (`--dialect` / `--lane` / `--ui`)
7. 계약 문서 `§5` 호환 버전 표에 행 추가 + 본 README 진행표 갱신
