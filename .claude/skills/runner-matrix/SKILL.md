---
name: runner-matrix
description: lane(jakarta/javax/vanilla/nexacro)별 디폴트·보조 러너 매핑 + 검증 라벨 컨벤션. L4 라이브 WAS 검증 시 어떤 러너를 쓸지 결정할 때 참조.
---

# 라이브 WAS 검증대 (lane × runner)

Growth-30 매트릭스 확정. `nexacroN-fullstack/samples/runners/` 아래 7개 러너가 존재. 각 lane 마다 디폴트 + 보조 러너 지정.

| lane | 디폴트 러너 | 보조 러너 |
|---|---|---|
| **jakarta** | `boot-jdk17-jakarta` (Spring Boot 3.3) | `mvc-jdk17-jakarta`, `egov5-boot-jdk17-jakarta` |
| **javax** | `boot-jdk8-javax` (Spring Boot 2.x) | `mvc-jdk8-javax`, `egov4-boot-jdk8-javax`, `egov4-mvc-jdk8-javax` |
| **nexacro** | `boot-jdk17-jakarta` (jakarta-for-nexacro) | — |
| **vanilla** | (직접 러너 없음 — `javax` 러너에 임포트 또는 minimal-servlet 러너 미정) | — |

> **현재 검증 상태(✅/⏳/⚠️)는 `learn-log.md` §1 참조.** 이 표는 lane→runner 매핑 규약(변하지 않는 절차)만 담는다.

## 선택 규칙

- lane 산출물은 디폴트 러너에서 첫 검증 → 통과 시 lane 전체 라이브 그린
- 보조 러너는 lane-내 변종(MVC vs Boot, eGov 통합 여부) 검증 필요 시 사용
- vanilla lane 은 "javax 러너에 servlet 임포트로 동작 확인" 까지가 현실적 한계 — 그 결과는 **"vanilla → javax-host 검증"** 라벨로 기록 (Growth-48 신설, Growth-50 첫 풀그린)

## 컨텍스트 경로 컨벤션 (Growth-50 등재)

모든 nexacroN-fullstack runner 가 `application.yml` 에 `server.servlet.context-path: /uiadapter` 설정. 따라서:
- nexacro envelope: `POST /uiadapter/<entity>/save_datalist_map.do`
- REST (jakarta/javax/vanilla): `GET /uiadapter/api/<entity>` ← `/api/<entity>` 아님 (T-Probe-CtxPath-Missing 트랩)

## scaffold lane vs runner lane (Growth-48)

wire-protocol(REST vs envelope)은 **scaffold lane** (Stage 3 codegen 산출) 이 결정. `--lane` 인자는 러너 선택. 두 값이 다르면 (예: nexacro scaffold → javax runner) `scaffold-report.md` 의 `- lane: <name>` 라인이 dispatch override.

## 연관 skill

- 4계층 절차 — [[full-test-protocol]]
- L4 종료 cleanup — [[runner-cleanup]]
