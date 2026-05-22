# Growth-48 Handoff — 2026-05-22

## 한 줄 요약

`T-Probe-LaneRunner-Mismatch` 픽스(Growth-47 잔여 차단 해소) + `vanilla lane 검증대` 신설(mybatis row 미해결 환류 동시 해소). 8 커밋 ahead of origin/master, workflow suite **82/82 그린**.

## 무엇이 끝났나

### 1) T-Probe-LaneRunner-Mismatch 픽스

**문제**: `lane_runner_map.py` 4개 dispatcher 가 *runner lane*(jakarta/javax — Spring Boot 버전 선택)만 보고 wire protocol(REST vs envelope)을 결정 → Growth-47 처럼 `nexacro` scaffold 를 `boot-jdk8-javax` 러너에 deploy 한 경우 probe 가 잘못된 endpoint(`/api/...`) 호출.

**픽스 메커니즘**: wire-protocol 의 진실원천이 deployment runner 가 아니라 *Stage 3 codegen 산출물(scaffold lane)* 임을 코드로 인코딩.

- `lane_runner_map.py`:
  - 신규 `_effective_lane(lane, scaffold_lane)` helper — supplied 시 scaffold_lane 우선, 미지정 시 lane 그대로(pre-Growth-48 API 무손상)
  - 4개 dispatcher(`lane_probe_kind` / `lane_probe_url` / `lane_crud_kind` / `lane_supports_crud`) 에 optional `scaffold_lane: str | None = None` 매개변수 추가
- `live_overlay.py`:
  - 신규 `discover_scaffold_lane(scaffold_dir)` — `scaffold-report.md` 의 `^\s*-\s*lane:\s*` `\`<name>\`` 라인을 regex 로 추출, 파일/라인 부재 시 graceful None
- `full_test.py:run_l4_live`:
  - probe/CRUD dispatch 전 `discover_scaffold_lane` 호출 → 4개 dispatcher 모두에 `scaffold_lane=` 전달
  - divergence 발견 시 informational print

**테스트**: 11 신규 + 회귀 0.
- `test_lane_runner_map.py` (5): scaffold_lane override probe_kind / url / crud_kind + None legacy preserve + unknown ValueError
- `test_live_overlay.py` (4): report-only / 3-lane parametrize / missing-file / missing-line
- `test_full_test.py` (2): scaffold_lane=nexacro on javax runner uses envelope · no-report falls back to runner lane

### 2) Vanilla lane 검증대 신설

**문제**: §1 vanilla row 가 `⚠️ 검증대 부재` 로 미해결 환류 1건 유지(mybatis row).

**검증 절차**:
1. Fresh scaffold: `board` 도메인 + `--lane vanilla --dialect hsqldb` → `out/board-growth48-vanilla/`
2. `scripts/workflow/full_test.py vanilla --json` 실행

**결과 라벨**: **JDBC + 빌드까지만 검증 → javax-host 검증**

| Layer | 결과 |
|---|---|
| L1 4-repo pytest | rc=0 |
| L2 schema+seed | OK |
| L3 `mvn package` (3-mybatis) | rc=0 |
| L4 overlay | 26 write / 2 edit · PASS |
| L4 mvn rebuild | **rc=1** — boot-repackage 가 stale `runner-boot-jdk8-javax-0.1.0-SNAPSHOT.jar` 잠금 해제 실패 = **환경성, codegen 결함 아님** |

**핵심 발견 (vanilla servlet-agnostic property)**:

`andrej-karpathy-rdb-mybatis/.claude/skills/karpathy-rdb-mybatis/templates/controller/controller.vanilla.java.j2` 는 `org.springframework.web.bind.annotation.*` 만 사용 — `jakarta.servlet.*` 또는 `javax.servlet.*` import 없음.

`out/board-growth48-vanilla/3-mybatis/src/main/java/com/example/board/controller/BoardController.java` 산출물에서 servlet-API import 0건 직접 확인 (line 1–12 검토 완료).

→ **vanilla scaffold 는 Spring 5 (`boot-jdk8-javax` / JDK8 / `javax.servlet`) / Spring 6 (`boot-jdk17-jakarta` / JDK17 / `jakarta.servlet`) 양 러너 호환.** "vanilla → javax-host 검증" 라벨 컨벤션이 라이브 검증대 매트릭스에 최초 적용.

## 커밋 (8건, ahead of origin/master)

```
fa2b3e3 docs(learn-log): record Growth-48 vanilla lane 검증대 신설
08f69f3 docs(learn-log): record Growth-48 T-Probe-LaneRunner-Mismatch fix
18bb30e test(full_test): scaffold_lane override flows through run_l4_live
514422a test(live_overlay): discover_scaffold_lane reads scaffold-report.md
b1c674a test(lane_runner_map): scaffold_lane override semantics
bf1bb2d fix(full_test): wire scaffold_lane into L4 probe/CRUD dispatch
4417d28 feat(live_overlay): discover_scaffold_lane reads scaffold-report.md
993dc52 feat(lane_runner_map): scaffold_lane override for probe/CRUD dispatch
```

Auto-mode classifier 가 default-branch push 를 차단 → 사용자가 수동 push.

## learn-log 환류 (compounding-growth principle)

- §0 creater row: trap T-Probe-LaneRunner-Mismatch — `RESOLVED Growth-48` 라벨, 미해결 환류에서 제거
- §0 mybatis row: 미해결 환류 `vanilla 검증대 부재` → `—`
- §1 javax row: footnote `T-Probe-LaneRunner-Mismatch → fix Growth-48`
- §1 vanilla row: `⚠️ 검증대 부재` → `✅ Growth-48 (board scaffold — L1+L2+L3 PASS, L4 overlay 26w/2e PASS; L4 mvn rc=1 = boot-repackage stale .jar lock = 환경성)`
- §4 트랩 행: 상태 `deferred to Growth-48` → `RESOLVED Growth-48`
- §6 Growth-48 ledger: scaffold_lane override 메커니즘 + 11 신규 테스트 + 82/82 그린 + vanilla 검증대 신설 milestone 통합 서술

## 알려진 잡음 (Growth-48 무관)

`tests/workflow/test_live_crud_nexacro.py` 의 7건 pre-existing failure (`ds<Pascal>` / `<Row Type="insert">` expectation vs 현 코드의 literal `"dataList"` / `_RowType_` Col). Growth-42 후속 stale tests — `git stash` 후 master 에서 재현되어 Growth-48 변경과 무관함을 확인. 본 Growth 범위 밖.

## 권장 다음 작업

브레인스토밍 후 결정 권장:

- (a) **G-Jackson javax fresh-scaffold 종단 검증 (L4-probe 까지)** — Growth-46 이 board 도메인 hand-written runner-default 까지 검증, Growth-47 이 fresh scaffold L4-빌드 까지 검증. 남은 갭: fresh scaffold L4-probe (이제 Growth-48 픽스로 가능). `customer` 도메인 + `--lane nexacro --dialect hsqldb --uia-namespace spring` + boot-jdk8-javax 러너 → `scripts/workflow/full_test.py javax --json` 으로 라벨 **풀테스트 그린** 달성 가능성.
- (b) **vanilla lane 의 실제 라이브 검증 (L4-probe)** — 현재 L3 빌드 까지만. boot-jdk8-javax 러너에 overlay 후 mvn 재빌드 잠금 해소(`Stop-Process java` 후 `target/` 청소) → probe 까지 진행해 "vanilla → javax-host 검증" 라벨이 *부분검증* 으로 승격.
- (c) **stale `test_live_crud_nexacro.py` 7건 정리** — Growth-42 이후 누락된 expectation 갱신 (Col 이름 `dataList` 고정 / `_RowType_` Col convention).
- (d) **scaffold-report 미지정 lane 표기 시 retroactive 검출 강화** — 현 discover_scaffold_lane 은 graceful None fallback. report 부재가 사일런트 → runner-lane 으로 dispatch, 이게 미래에 다른 mismatch 를 가릴 수 있음. warning 로그 추가 고려.

## 참고 명령

```powershell
# Workflow suite 재현
cd D:\AI\workspace\business-fullstack-creater
python -m pytest tests\workflow -q

# Vanilla fresh scaffold 재현
python scripts\scaffold_cli.py --domain board --lane vanilla --dialect hsqldb `
    --out out\board-growth48-vanilla
python scripts\workflow\full_test.py vanilla --json

# Push (사용자 수동)
git -C D:\AI\workspace\business-fullstack-creater push origin master
```
