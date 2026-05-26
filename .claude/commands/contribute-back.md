# /contribute-back — 환류 누락 차단

CLAUDE.md "복리식 축적 체크리스트" 자동화. Growth 종료 시 사용.

## 인자

없음 (활성 Growth 자동 감지)

## 동작

1. 5개 레포에서 `git log --since=<활성 Growth 시작일> --name-only` 수집
   - 시작일 감지 실패 시 최근 7일
2. 변경 path 를 카테고리로 분류:
   - `presets/*.seed.md`, `catalogs/*.yaml` → catalog (rdb-skill/ddl)
   - `templates/*/*.j2` → template (rdb-mybatis)
   - `patterns/*/manifest.yaml` → pattern (rdb-nexacro)
   - `scripts/dialect*.py` → dialect (rdb-ddl)
   - 기타 → other (§5 / §6 freeform)
3. 카테고리별로 환류 위치 안내 + 인터랙티브 Y/N 체크
4. 미환류 1건 이상 시 Growth 행 라벨에 `(환류 미완)` 자동 부착 + stderr 경고

## 실행

```powershell
python scripts/workflow/contribute_back.py
```

## 결과 해석

- `환류 대상 없음.` → 변경 0건. 정상 종료.
- `=== 환류 후보 ===` 표시 → LLM 이 각 카테고리에 대해 사용자 확인.
- `[warn] 환류 미완 후보 있음` → §2~§5 에 1줄씩 환류 후 명령 재실행.

## Phase A Self-Check (2026-05-22)

LLM 이 카테고리별 인터랙티브 확인 후, 다음 한 줄을 추가로 묻는다:

> **이번 Growth 가 `learn-log.md` §0 Layer Ownership Card 의 어느 행(skill / ddl / mybatis / nexacro / creater)에 살을 붙였는가? 해당 행의 누적 트랩 수 또는 미해결 환류 텍스트를 갱신해야 하는가?**

답이 "예" 면 §0 표 갱신 + §4 (트랩) 또는 §5 (미해결) 의 해당 행 환류 후 명령 재실행. CLAUDE.md §핵심 운영 원칙 5축 표(변하지 않는 책임) 와 §0(매 Growth 활동 뷰) 의 한 쌍을 유지하는 가벼운 자기 점검.

## R4 Self-Check — /list-domains 카탈로그 동기화 (2026-05-26)

신규 preset 도메인이 환류된 경우 (`andrej-karpathy-rdb-skill/.claude/skills/karpathy-rdb/presets/*.seed.md` 신규/이름변경), LLM 은 다음을 추가로 묻는다:

> **이번 Growth 가 새 preset 도메인을 추가했거나 기존 도메인의 aliases/keywords/entities/한 줄 요약을 의미있게 바꾸었는가? 그렇다면 `andrej-karpathy-rdb-skill/.claude/skills/karpathy-rdb/presets/INDEX.md` 의 해당 절(도메인 heading + 4 필드)도 함께 갱신되었는가?**

답이 "예 + 미갱신" 이면 INDEX.md 환류 후 명령 재실행. `/list-domains` 슬래시 커맨드(creater) 가 `INDEX.md` 를 직접 읽어 14 도메인 카탈로그를 노출하므로, 신규 preset 이 INDEX.md 에 누락되면 외부 사용자가 새 도메인을 발견하지 못한다 — 복리식 축적의 사용자-노출 게이트.

검증: `python scripts/workflow/list_domains.py --json | jq '.[].name'` 으로 누락 여부 즉시 확인.
