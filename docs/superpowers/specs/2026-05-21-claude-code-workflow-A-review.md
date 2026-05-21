# Claude Code Workflow A안 — 5축 자체 리뷰 (2026-05-21)

> 대상: `C:\Users\mo\.claude\plans\delightful-swimming-hanrahan.md` 의 후속 — Claude Code workflow A안 (`/cleanup-runner`, `/growth-start`, `/full-test`, `/contribute-back` 4 슬래시 커맨드)
> 실행 범위: Task 1~7 (subagent-driven-development, 두 단계 리뷰 — spec compliance → code quality)

## 산출물 인벤토리

| 영역 | 파일 |
|---|---|
| 슬래시 커맨드 | `.claude/commands/cleanup-runner.md`, `.claude/commands/growth-start.md`, `.claude/commands/full-test.md`, `.claude/commands/contribute-back.md` |
| 워크플로 모듈 | `scripts/workflow/learn_log.py`, `scripts/workflow/lane_runner_map.py`, `scripts/workflow/cleanup_runner.py`, `scripts/workflow/growth_start.py`, `scripts/workflow/full_test.py`, `scripts/workflow/contribute_back.py` |
| 테스트 | `tests/workflow/test_learn_log.py` (8), `test_lane_runner_map.py` (6), `test_cleanup_runner.py` (4), `test_growth_start.py` (3), `test_full_test.py` (6), `test_contribute_back.py` (3) — **합계 30/30 PASS** |
| 환류 | `CLAUDE.md` 풀테스트 섹션 + 체크리스트 섹션 자동실행 힌트 1줄씩, `learn-log.md` §6 Growth-34 |
| 정책 | `.claude/settings.local.json` 슬림 (60줄 → 22줄, 정책 패턴화) |

---

## 5축 점수표

| # | 축 | 점수 | 근거 |
|---|---|---|---|
| 1 | **반복 데이터 효율 관리** | 4/5 | learn-log.md §6 자동 갱신 + lane→runner 매핑 단일 진실원천(`lane_runner_map`). cleanup 4 단계 reproducible. 한계: 라이브 WAS(L4)는 placeholder 상태로 실제 HTTP 호출 미구현 — 다음 작업에서 채워야 함. |
| 2 | **도메인·엔티티 지식 누적** | 3/5 | `/contribute-back`이 도메인 변경을 catalog/template/pattern/dialect 4 카테고리로 자동 분류해 환류 누락 방지. 한계: 분류 룰이 경로 패턴 매칭이라 신규 디렉터리 구조에 약함 — B안에서 frontmatter/메타 기반 분류로 강화 필요. |
| 3 | **풍부한 Seeds** | 4/5 | `/growth-start`가 §6에 in_progress placeholder 즉시 박아 누락 시 시각화. CRLF 라인엔딩 보존 등 데이터 무결성 확보. 한계: Seeds 자체 생성은 본 A안 범위 밖 (Stage 2 dialect 어댑터 영역). |
| 4 | **완성도 높은 WAR** | 4/5 | `/full-test` 4계층 라벨링 규칙(decide_label)이 "그린/부분검증/JDBC까지/단위까지" 4 단계를 강제 → 4계층 실행 안 한 채 "그린" 라벨 붙는 위험 차단. 한계: L4 라이브 호출 placeholder. |
| 5 | **Karpathy 정신 (LLM = 컴파일러)** | 5/5 | 모든 자동화가 파일 기반(learn-log.md / settings.local.json / .claude/commands/*.md). 로컬 캐시·DB 없음. 슬래시 커맨드 = LLM 인터페이스, 파이썬 모듈 = 결정론적 컴파일러. 복리식 축적(learn-log §6)이 자동으로 늘어남. |

**평균: 4.0/5** — Gate 통과 기준(≥3/5) 충족.

---

## 사용자 의도 거울 평가

> "반복되는 데이터를 효율적으로 관리 / 도메인·엔티티를 지식으로 누적 / 풍부한 Seeds / 완성도 높은 WAR"

- **반복 데이터 관리**: ✅ 4 슬래시 커맨드로 cleanup·Growth 등록·풀테스트·환류 모두 1줄로 압축
- **지식 누적**: ✅ §6 자동화 + 환류 누락 시 "환류 미완" 자동 라벨 (실패 시 silent fallback 없음)
- **Seeds 풍부함**: ⚠️ 직접 기여는 없으나 contribute-back이 환류 누락을 막아 간접 보호
- **WAR 완성도**: ✅ 4계층 라벨링이 "그린"의 의미를 엄격하게 정의

---

## 회귀 검증

- `python -m pytest tests/workflow/ -v` → **30 passed in 0.17s** (0 failed, 0 errored)
- 작업 중 발견된 버그(Task 1 code-quality 리뷰): CRLF mangling, double read, silent update_label, regex too loose — 모두 즉시 수정 + 회귀 테스트 추가(`test_append_row_preserves_crlf`, `test_update_label_raises_on_missing_growth_num`, `test_update_label_raises_on_already_labelled`)
- spec 외 추가 기능(`contribute_back.py`의 `input("환류 완료했나요? (y/N) ")`) → 슬래시 커맨드 markdown "인터랙티브 Y/N 체크" 명세와 일치 확인 후 채택

---

## B안 트리거 조건 (다음 단계 진입 신호)

다음 중 하나라도 만족하면 B안(`/full-test`의 L4 라이브 호출 실구현 + `/contribute-back` frontmatter 기반 분류)을 시작:

1. `/full-test`를 5회 이상 실제 lane×domain 조합에 사용해, L4 placeholder가 그린/부분검증을 잘못 분류하는 사례 1건 이상 발생
2. `/contribute-back`이 새로 추가된 디렉터리(예: `adapters/`, `overlays/`) 변경을 "other"로 떨어뜨려 환류 누락이 1회라도 일어남
3. `lane_runner_map`에 vanilla → 자체 minimal-servlet runner가 추가됨 (현재 javax-host 검증 라벨 우회)

---

## 장기 보류 (C안)

- 메타 지식 추출(`scripts/meta_extract.py`) — Growth-35 시점에 실 프로젝트 3 개 이상 누적 후 재평가
- 마켓플레이스(`catalogs/preset-catalog.yaml` 별도 git 리포 분리) — 사용자 본인 외 협업자 등장 시
