---
name: business-fullstack-creater:diagnose
description: /full-test 진입 전 pre-flight 환경 점검 — 5축 레이어/카탈로그/runner/JDK ✓/!/✗ 매트릭스
argument-hint: [--json]
---

# /diagnose — pre-flight 환경 점검

Growth-52 (서비스 리뷰 2026-05-26): R3 `recovery_hint` 가 실패 *후* 다음 명령을
안내한다면, `/diagnose` 는 실패 *전* 환경 조건을 본다. 5축 레이어 repo, preset
카탈로그, nexacroN runner 디렉터리, JDK 가용성을 빠르게 확인하고 각 항목에
✓(OK)/!(WARN)/✗(FAIL) + 회복 명령 1줄을 제공한다.

비싼 빌드(mvn/pytest) 는 호출하지 않는다 — 파일/PATH 존재 + 1회 `java -version`
만으로 끝난다 (수초).

## 인자

- `--json` (선택): 구조화 출력 (다른 도구가 소비)

## 실행

```powershell
python scripts/workflow/diagnose.py            # 사람용 표
python scripts/workflow/diagnose.py --json     # JSON
```

## 출력 예

```
Pre-flight diagnose:
  OK  layer/skill                .../andrej-karpathy-rdb-skill
  OK  layer/ddl                  .../andrej-karpathy-rdb-ddl
  OK  preset-catalog             14 domains
  OK  learn-log                  §0 present
  !   runner/boot-jdk17-jakarta  stale generated overlay (com/example present)
    -> python scripts/workflow/cleanup_runner.py boot-jdk17-jakarta
  OK  jdk                        openjdk version "17.0.10"

9 PASS, 1 WARN — /full-test should run
```

## 종료 코드

- `0`: critical FAIL 없음 → `/full-test` 진입 가능
- `1`: 하나 이상 FAIL → 회복 hint 1줄을 따라 fix 후 재실행

## 검사 항목

| 항목 | 확인 |
|---|---|
| `layer/skill·ddl·mybatis·nexacro·runners` | 5 sibling repo 존재 |
| `preset-catalog` | `rdb-skill/.../presets/INDEX.md` 파싱 + 도메인 수 ≥10 |
| `learn-log` | §0 Layer Ownership Card 존재 |
| `runner/boot-jdk17-jakarta`, `boot-jdk8-javax` | 디렉터리 존재 + stale `com/example` overlay 없음 |
| `cross-layer-coherence` | learn-log §4 트랩 4건 정적 회귀 가드: G-47(mybatis `{{ uia_namespace }}`), G-48(`full_test` ↔ `discover_scaffold_lane`), G-50a(runner `application.yml` `context-path: /uiadapter`), G-50b(`lane_runner_map` REST `/uiadapter/api/`) |
| `jdk` | `java -version` 성공 + (선호 JDK17 권고) |

## 후속 동작

WARN/FAIL 항목의 hint 를 따른 뒤:

```
/full-test <lane> [domain]   # 4계층 풀테스트
```

또는 신규 사용자라면:

```
/orient                       # 프로젝트 1화면 요약
/list-domains                 # 14 preset 도메인 둘러보기
```
