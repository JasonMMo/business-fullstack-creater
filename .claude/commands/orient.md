---
name: business-fullstack-creater:orient
description: 신규 사용자 진입 — USER-GUIDE pitch + 5축 ownership card + 최근 Growth + 다음 명령 한 화면
---

# /orient — newcomer 진입 화면

Growth-52 (서비스 리뷰 2026-05-26): 클론 직후 사용자가 "여기서 무엇부터 만지면
되는지" 한 화면에 파악하도록 *이미 누적된 자산* 세 곳을 합성한다 — 별도 onboarding
문서 신설이 아니라 `/list-domains` 와 동일한 "자산 노출형 하네스" 패턴.

세 소스:

- `docs/USER-GUIDE.md` 첫 blockquote (프로젝트 한 줄 정의)
- `learn-log.md` §0 Layer Ownership Card (5축 + 현재 누적 트랩)
- `learn-log.md` §6 Growth 이력 마지막 행 (가장 최근 활동)

## 실행

```powershell
python scripts/workflow/orient.py
```

## 출력 예

```
business-fullstack-creater — orientation
================================================

  업무별 fullstack 코드 생성 파이프라인 ...

5축 (현재 누적 트랩):
  - skill (Stage 1)         0
  - ddl (Stage 2)           3 (HSQLDB IDENTITY 0-base, SQL:2008 LEAD, ...)
  - mybatis (Stage 3)       7 (...)
  - nexacro (Stage 4+5)     0
  - creater (Orchestrator)  4 (javax lane URL, JDK8 source/target, ...)

최근 Growth: Growth-51 (2026-05-26)
  서비스 리뷰 R1/R3/R4 환류 — 외부 사용자 첫인상 보강 ...

다음 명령:
  /diagnose       — 환경 pre-flight (JDK/runner/카탈로그 점검)
  /list-domains   — 14 preset 도메인 둘러보기
  /scaffold <도메인>  — 신규 프로젝트 생성
  /full-test <lane>   — 4계층 풀테스트 (실패 시 R3 recovery hint)
```

## 후속 동작

신규 사용자는 보통 이 순서로 진입:

```
/orient          # 1) 프로젝트 한 화면 요약 (now)
/diagnose        # 2) 환경 pre-flight
/list-domains    # 3) 14 preset 도메인 비교
/scaffold <도메인> --slug <ascii-slug>   # 4) 신규 프로젝트
/full-test <lane> [domain]               # 5) 4계층 풀테스트
```

## 출처

- `docs/USER-GUIDE.md` — 프로젝트 한 줄 정의 (첫 blockquote)
- `learn-log.md` §0 — 5축 ownership card (Phase A 토대)
- `learn-log.md` §6 — Growth 이력 표 (최근 활동)

세 파일이 갱신될 때마다 자동으로 최신 상태가 반영된다 — 별도 동기화 불필요.
