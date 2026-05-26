---
name: business-fullstack-creater:web-build
description: Static portal 재생성 — docs/index.html + domain pages + scaffold archives + assets
argument-hint: [--domain <slug>] [--check] [--json]
---

# /web-build — static portal 재생성

`docs/` 하위의 정적 포털(index.html, 도메인 페이지, scaffold 아카이브, CSS/JS assets)을
`web_index.py` 를 통해 재생성한다. 매 Growth 종료 시 `/contribute-back` 이 자동으로
이 명령을 실행한다.

## 실행

```powershell
python -m scripts.workflow.web_index
```

## 플래그

- `--domain <slug>` : 특정 도메인만 재생성 (예: `--domain customer`)
- `--check`         : 생성 없이 누락 파일 목록만 출력; 이상 있으면 exit 1
- `--json`          : BuildResult 를 JSON으로 stdout 출력 (CI 소비용)

## 출력 위치

| 경로 | 내용 |
|---|---|
| `docs/index.html` | 도메인 타일 그리드 포털 메인 |
| `docs/domain/<slug>.html` | 도메인별 상세 페이지 |
| `docs/scaffolds/<slug>/<lane>/` | scaffold ZIP + DDL.sql |
| `docs/assets/style.css` | 공통 스타일 |
| `docs/assets/preview.js` | 클립보드 / 탭 JS |

## 자동 트리거

`/contribute-back` 체크리스트 완료 후 자동 실행된다.
수동으로 포털을 갱신하려면 위 명령을 직접 실행한다.
