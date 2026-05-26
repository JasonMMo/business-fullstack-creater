---
name: business-fullstack-creater:list-domains
description: Preset 카탈로그 14 도메인 한줄 노출 — /scaffold 전 도메인 선택용
argument-hint: [--verbose] [--json]
---

# /list-domains — preset 도메인 카탈로그 노출

R4 (서비스 리뷰 2026-05-26): `/scaffold` 진입 전 사용자가 어떤 preset 도메인을 쓸지
한눈에 비교할 수 있도록 catalog 를 노출한다. 별도 wiki 페이지를 열지 않고 한 줄
요약 + (옵션) aliases/entities 만으로 도메인 선택 결정.

## 인자

- `--verbose` (선택): aliases + entities 도 포함 (3줄 per 도메인)
- `--json` (선택): JSON 구조화 출력

## 실행

```powershell
python scripts/workflow/list_domains.py            # 기본: 한줄 표
python scripts/workflow/list_domains.py --verbose  # aliases + entities 포함
python scripts/workflow/list_domains.py --json     # 구조화 (다른 도구가 소비)
```

## 출력 예 (기본)

```
14 preset domains:
  결재       한국 SI 표준 — 순차/병렬/혼합 결재 라인 + RO 이력 + 위임/회수
  게시판     다중 카테고리 + 익명/회원 글 + 트리형 댓글 + 첨부 N개
  고객관리   B2C/B2B 고객 + 다중 주소 + 응대 이력 + 분류 트리
  ...
```

## 후속 동작

원하는 도메인을 골라 다음 명령으로 진입:

```powershell
python scripts/scaffold_cli.py --domain "<도메인>" --slug <ascii-slug> --package com.example.<slug> --out ./<slug>-scaffold
```

또는 슬래시 커맨드:

```
/scaffold <도메인명>
```

## 출처

`andrej-karpathy-rdb-skill/.claude/skills/karpathy-rdb/presets/INDEX.md` — 14 도메인의
aliases/keywords/entities/한줄 매칭 메타데이터. 새 preset 기여 시 `/contribute-back`
체크리스트 의 INDEX.md 항목이 갱신을 강제한다.
