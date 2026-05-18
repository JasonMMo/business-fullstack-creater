---
name: business-fullstack-creater:scaffold
description: Orchestrate 4-stage code generation (wiki → DDL → MyBatis → Nexacro forms) for a domain
argument-hint: <도메인명>
---

# /scaffold — 4-stage 자동 큐레이션

당신은 **4-stage 오케스트레이터** 다. 사용자로부터 6가지 값을 수집한 뒤 Python CLI 를 실행하여 wiki → DDL → MyBatis → Nexacro form 산출물을 한 번에 생성한다.

## 사용자 prompt 순서

아래 항목을 순서대로 확인한다. 인자로 미리 전달된 값은 confirm 후 건너뛴다.

| # | 항목 | 기본값 | 비고 |
|---|------|--------|------|
| 1 | **도메인명** | (인자 또는 질문) | 예: `주문관리` |
| 2 | **Wiki 입력 모드** | `preset` | `preset` 또는 `wiki` 선택 |
| 3 | **Lane** | `nexacro` | `nexacro` 또는 `vanilla` |
| 4 | **기본 Form Pattern** | `D2` | `D2` / `F1` / `C1` 중 택1 |
| 5 | **Spring base package** | `com.example.<slug>` | 예: `com.example.order` |
| 6 | **출력 디렉터리** | `./<slug>-scaffold/` | 절대 또는 상대 경로 |

### Wiki 모드 분기

- **preset 모드**: `--preset <name>` 추가 필요. preset 이름을 묻는다 (기본 = 도메인명과 동일).
- **wiki 모드**: `--wiki <path>` 추가 필요. 이미 준비된 wiki 디렉터리 절대 경로를 묻는다.

## 검증

실행 전 아래를 확인한다.
- `wiki-mode=preset` → `--preset` 값이 있어야 한다.
- `wiki-mode=wiki` → `--wiki` 경로가 존재해야 한다.
- `--package` 는 필수 (Java 패키지 규칙: `com.example.*`).
- `--out` 은 필수.

## CLI 실행

수집된 값을 요약 표시하고 사용자 confirm 후 실행한다.

```bash
# preset 모드 예시
python scripts/scaffold_cli.py \
  --domain "주문관리" \
  --wiki-mode preset \
  --preset "주문관리" \
  --lane nexacro \
  --default-pattern D2 \
  --package com.example.order \
  --out ./order-scaffold

# wiki 모드 예시
python scripts/scaffold_cli.py \
  --domain "주문관리" \
  --wiki-mode wiki \
  --wiki /path/to/my-wiki \
  --lane nexacro \
  --default-pattern D2 \
  --package com.example.order \
  --out ./order-scaffold

# 부분 실행 (stage 1까지만)
python scripts/scaffold_cli.py \
  --domain "주문관리" \
  --wiki-mode preset --preset "주문관리" \
  --package com.example.order \
  --out ./order-scaffold \
  --stop-after-stage 1
```

## 결과 해석

성공 시 출력:
```
OK. Report: ./order-scaffold/scaffold-report.md
```

`scaffold-report.md` 를 열어 각 stage 소요 시간 및 산출물 위치를 확인한다.

```
<out>/
  1-wiki/         # _schema.md, entities/, _blueprint.yaml, compile-report.md
  2-ddl/          # ddl_*.sql, ddl-report.md
  3-mybatis/      # src/main/java/..., mapper.xml, endpoints.json
  4-nexacro/      # nxui/_form_/*.xfdl, generation-report.md
  scaffold-report.md
```

## 실패 처리

`FAILED at <stage>: ...` 메시지가 출력되면:
1. `scaffold-report.md` 에서 실패 stage 와 오류 메시지를 확인한다.
2. 해당 stage 단독 CLI 를 직접 실행하여 문제를 격리한다 (각 stage 리포의 `scripts/` 참조).
3. 수정 후 `/scaffold` 를 재실행하거나 `--stop-after-stage` 로 구간을 좁혀 재시도한다.

## 사전 조건

- `config/stage-paths.yaml` 이 있거나, sibling 디렉터리에 4개 stage 리포가 존재해야 한다:
  - `../andrej-karpathy-rdb-skill`
  - `../andrej-karpathy-rdb-ddl`
  - `../andrej-karpathy-rdb-mybatis`
  - `../andrej-karpathy-rdb-nexacro`
- 각 stage 리포는 v0.3.0 이상 호환 기준.
