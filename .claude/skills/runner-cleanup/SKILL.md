---
name: runner-cleanup
description: L4 라이브 WAS 검증 종료 시 필수 cleanup 명령. java 프로세스 정지 → runner 원복 → overlay 산출물 제거. /full-test 가 자동 수행하나 수동 실행/실패 시 참조.
---

# Runner Cleanup (계층 4 종료 시)

`/full-test` 가 cleanup 단계를 자동 포함한다. 수동 실행 / cleanup 단계 실패 시 아래 명령으로 보정.

## 1. Java 프로세스 정지

```powershell
# CLAUDE.md 컨벤션: jdk-17 path 매칭으로만 정지 (PID 누락 방지)
Get-Process java -EA SilentlyContinue | Where-Object { $_.Path -like "*jdk-17*" } | Stop-Process -Force
```

javax 러너(JDK 8)는 패턴이 다르다. 명시적 PID 정지가 안전:
```powershell
Stop-Process -Id <PID> -Force
```

## 2. Runner Git 원복

```powershell
# jakarta 러너 예
git -C D:/AI/workspace/nexacroN-fullstack restore samples/runners/boot-jdk17-jakarta/

# javax 러너 예
git -C D:/AI/workspace/nexacroN-fullstack restore samples/runners/boot-jdk8-javax/
```

## 3. Overlay 산출 untracked 파일 제거

`apply_overlay` 가 쓴 파일은 git restore 가 잡지 못한다. 명시 경로로 제거:

```powershell
$root = "D:/AI/workspace/nexacroN-fullstack/samples/runners/<runner-name>/src/main/resources"
# 생성된 schema/data sql (overlay 가 <slug>-* prefix 로 씀)
Remove-Item -Force "$root/<slug>-schema.sql","$root/<slug>-data.sql" -EA SilentlyContinue
# 생성된 mapper xml (생성된 것만 — runner 자체 mapper 와 구별!)
Remove-Item -Force "$root/mybatis/mappers/<entity>-mapper.xml" -EA SilentlyContinue
```

⚠️ **mappers 폴더 통째 삭제 금지**: runner 자체 mapper(board, dept, file, large, testdata, user, wide 등)와 generated mapper 가 같은 폴더에 공존. 생성된 파일명만 명시적으로 지운다. 실수했으면 `git restore` 로 runner 자체 mapper 복원.

## 알려진 트랩

- **`cleanup_runner.py` PowerShell subexpression quoting** (Growth-42 부터 deferred): `full_test.py` 의 자동 cleanup 마지막 단계 `Remove untracked mappers` 가 FAIL. 위 명시 명령으로 수동 처리.
- **Application.java / application.yml 편집**: overlay 가 `_edit_application_java` / `_edit_application_yml` 로 in-place 수정. `git restore` 가 원복.

## 검증

cleanup 완료 후:
```powershell
git -C D:/AI/workspace/nexacroN-fullstack status --short samples/runners/<runner-name>/
```
출력 0줄 = clean.

## 연관 skill

- [[full-test-protocol]] · [[runner-matrix]]
