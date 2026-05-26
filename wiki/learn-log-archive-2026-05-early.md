# learn-log archive — 2026-05 early (Growth-26 ~ Growth-40)

> `learn-log.md` §6 본문에서 분리된 옛 Growth 항목. 풀테스트 4계층 인프라 구축 시기 (Growth-29~30 매트릭스, Growth-34~40 자동화 구현). 컨벤션은 `../learn-log.md` §7 참조.

## Growth 이력 (Growth-26 ~ Growth-40)

| Growth | 일자 | 살붙임 요약 |
|---|---|---|
| Growth-26~28 | 2026-05 | 재무 v4 (double-entry) + IDENTITY 트랩 환류 + jakarta 라이브 검증 |
| Growth-29~30 | 2026-05 | 풀테스트 4계층 절차 자체 리뷰 + 검증대 매트릭스 |
| Growth-31 | 2026-05-21 | jakarta lane × 영업관리 라이브 검증 (cross-domain) |
| Growth-32 | 2026-05-21 | javax lane × 영업관리 라이브 검증 + codegen bug 4건 |
| Growth-33 | 2026-05-21 | javax lane re-검증 (regenerated, no manual edits) — pytest/JDBC/Maven/Spring context PASS, 엔드포인트 응답은 runner Jackson dep 결함으로 500 → **"라이브 WAS 부분검증"**. codegen 결함 2건 환류 (#245 seed sentinel, #246 `@Mapper` 어노테이션). 새 gap G-Jackson 등록. |
| Growth-34 | 2026-05-21 | Claude Code workflow A안 (구현 완료) — `/cleanup-runner`, `/growth-start`, `/full-test`, `/contribute-back` 4 슬래시 커맨드 + `scripts/workflow/` 6 모듈 + 30 테스트(전부 그린). settings.local.json 슬림. CLAUDE.md 풀테스트/체크리스트 섹션에 자동 실행 힌트 1줄씩 환류. |
| Growth-35 | 2026-05-21 | B-plan L4 live WAS 실구현 — `live_overlay` (5-point overlay, idempotent) + `live_runner` (Spring Boot fat-jar 기동 + ready-poll, 180s timeout) + `live_probe` (nexacro envelope POST + 200/ErrorCode/row_count 판정, 30s timeout) 3 모듈 신규 + `full_test.run_l4_live` 가 placeholder 에서 overlay→`mvn package`→start→wait_until_ready→probe→stop orchestration 으로 교체. 22 신규 테스트(6 overlay + 8 runner + 8 probe) + 7 wiring 테스트 — 60/60 전 그린. **전제 컨벤션**: scaffold 디렉터리 이름 = Java sub-package 식별자(ASCII slug). |
| Growth-36 | 2026-05-21 | Scaffold ↔ runner 갭 해소 — Phase 1: `live_overlay.discover_scaffold` 가 Stage 3 실 출력과 legacy fixture 양쪽 자동 도출. Phase 2: lane-aware 프로브 dispatch — `lane_runner_map.lane_probe_kind/url` 추가, nexacro 는 envelope / jakarta·javax·vanilla 는 GET JSON. 신규 12 테스트 + 회귀 71 = 83/83 그린. |
| Growth-37 | 2026-05-21 | L2 placeholder → 실 JDBC smoke + L1 silent-pass guard — `_jdbc_smoke.java` (JDK 11+ single-file source-mode 런처, HSQLDB in-mem, 옵션 invariant `SELECT...=<int>`) + `jdbc_smoke.py` 래퍼(env `HSQLDB_JAR` fallback). `run_l1_pytest` 에 empty-skip guard 추가 — sibling repo 0개 silent True 차단. 신규 17 테스트 = 100/100 그린. |
| Growth-38 | 2026-05-21 | 풀테스트 견고성 3종 — (1) L3 pom 탐색 일반화: `_find_pom` 헬퍼, 탐색 순서 `5-overlay/pom.xml` → `3-mybatis/pom.xml` → root. (2) live_probe transient retry: connection refused/timeout 만 재시도, HTTPError 즉시 surface. (3) lane pre-validation: `resolve_runner(lane)` 즉시 호출. 신규 11 테스트 = 111/111 그린. |
| Growth-39 | 2026-05-21 | `/full-test --json` 머신리더블 출력 — `run()` 반환을 `FullTestResult` dataclass 로 승격, `__str__` → label 로 레거시 무손상. `--json` 시 print를 stderr 로 monkey-patch → stdout 은 단일 파싱 가능 JSON. 종료코드 0=L4_full PASS / 1=그 외 — CI rc 분기 가능. 신규 6 테스트 = 117/117 그린. |
| Growth-40 | 2026-05-21 | REST lane CRUD round-trip probe — `live_crud.crud_roundtrip_rest()` 가 baseline GET → POST insert → +1 verify → POST delete → baseline verify 5-step. `build_insert_template()` 가 `data.sql` MERGE 첫 행을 마이닝, PK 만 sentinel=999001 로 치환. SQL 리터럴 coercion (`CURRENT_TIMESTAMP/DATE/TIME` → ISO 문자열, bool/null/escape). `lane_supports_crud` gate 가 REST lane(jakarta/javax/vanilla)만 허용. 신규 33 테스트 = 150/150 그린. |
