---
name: business-fullstack-creater:growth-start
description: Growth-N 시작 — 다음 번호 자동 부여 + learn-log §6 행 추가 + TaskCreate
argument-hint: <name>
---

# /growth-start — Growth 사이클 진입

CLAUDE.md "복리식 축적" 사이클의 시작점. 매번 반복되던 (번호부여 / §6 행 추가 / Task 생성) 을 1줄로.

## 인자

- `<name>` (필수): Growth 의 한 줄 요약. 한국어 가능. 예: `"vanilla lane 라이브 검증 확장"`

## 동작

1. `learn-log.md §6` 마지막 행에서 가장 큰 Growth 번호 N 추출 → `Growth-(N+1)` 부여
2. §6 표 끝에 추가: `| Growth-{N+1} | {YYYY-MM-DD} | {name} (in_progress) |`
3. (LLM) TaskCreate: `subject = "Growth-{N+1}: {name}"`, `status = in_progress`

## 실행 (Python wrapper)

```powershell
python scripts/workflow/growth_start.py "<name>"
```

출력 예:
```
Growth-33 started. learn-log §6 placeholder 추가됨.
```

이어서 LLM 은 위 출력을 받아 TaskCreate 를 호출한다.

## 실패 모드

- `<name>` 비어있음 → `ValueError: name is required`
- learn-log.md §6 헤더 없음 → `ValueError: section header not found`
- (silent fallback 금지)
