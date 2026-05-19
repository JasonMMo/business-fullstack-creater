# Service Adapter Contract (v0.5)

**Status:** v0.5 H3 (lane suffix v2 + jakarta/javax) — 2026-05-19
**Scope:** Middle-tier lane 어댑터 (Stage 3 = `andrej-karpathy-rdb-mybatis`)
**Reference impls:** `nexacro` (default), `vanilla` (v0.3 Phase B), `jakarta` (v0.5 H3), `javax` (v0.5 H3)

> "middle service: Stage 3 `--lane jakarta|javax|vanilla` 정식화 (v0.3의 vanilla lane을 contract 기반으로 정리)." — USER-GUIDE §6.4 v0.5

---

## 1. 목적

같은 blueprint·DDL 에서 **서로 다른 Java 생태계 변종** 의 Spring Boot 모듈을 동시 생성 가능하게 한다. 변종은 단지 import 차이뿐 아니라 controller 시그니처, response envelope, 예외 매핑까지 다를 수 있다. 이 변종 결정을 lane 어댑터로 외부화하여, Stage 3 의 codegen 본체는 lane-agnostic 로 유지한다.

---

## 2. lane 슬롯 — 단일 문자열 식별자

위치: `andrej-karpathy-rdb-mybatis/scripts/codegen.py:23`

```python
def render_entity_files(out_root, entity, base_package, lane: str = "nexacro") -> list:
```

`lane` 은 enum 이 아니라 자유 문자열 — 어댑터 추가 시 새 식별자 그냥 도입. 단, 다음 4 식별자는 **예약어**:

| lane | 도입 | 의미 |
|:-:|:-:|:-|
| `nexacro` | v0.1 | Nexacro UI 어댑터와 짝지어진 controller (uiadapter 응답 포맷) |
| `vanilla` | v0.3 Phase B | 표준 Spring `@RestController` + `ResponseEntity<List<T>>` (UI 어댑터 의존성 없음) |
| `jakarta` | v0.5 H3 ✅ | JPA `@Entity` + `jakarta.persistence.*` (Spring Boot 3+/JDK17+) |
| `javax`   | v0.5 H3 ✅ | JPA `@Entity` + `javax.persistence.*` (Spring Boot 2.x/JDK8·11) |

---

## 3. 어댑터 슬롯 — 템플릿 변종 + suffix 규칙

위치: `andrej-karpathy-rdb-mybatis/.claude/skills/karpathy-rdb-mybatis/templates/`

lane 분기는 **파일 suffix 컨벤션** (v2, H3 일반화):

```python
# codegen.py:32 — lane suffix v2
suffix = "" if lane == "nexacro" else f".{lane}"
env.get_template(f"domain/entity{suffix}.java.j2")
env.get_template(f"service/service-impl{suffix}.java.j2")
env.get_template(f"controller/controller{suffix}.java.j2")
```

### 3.1 **변형되는 파일** (lane 별로 다른 .j2 필요)

| 슬롯 | 기본 (nexacro) | vanilla | jakarta | javax |
|:-:|:-:|:-:|:-:|:-:|
| domain | `entity.java.j2` | `entity.vanilla.java.j2` | `entity.jakarta.java.j2` | `entity.javax.java.j2` |
| service impl | `service-impl.java.j2` | `service-impl.vanilla.java.j2` | `service-impl.jakarta.java.j2` | `service-impl.javax.java.j2` |
| controller | `controller.java.j2` | `controller.vanilla.java.j2` | `controller.jakarta.java.j2` | `controller.javax.java.j2` |

### 3.2 **공유되는 파일** (lane 무관, 1개 .j2 재사용)

- `mapper/mapper-interface.java.j2`
- `mapper/mapper.xml.j2`
- `service/service-interface.java.j2`

→ 어댑터가 인터페이스 시그니처를 바꾸려면 **모든 lane 동의 필요** (계약 major bump).

### 3.3 lane 식별자 ↔ suffix 매핑 규칙

```
suffix = "" if lane == "nexacro" else f".{lane}"
```

`nexacro` 만 default (suffix 없음) — 역사적 이유. 새 lane 추가 시 항상 suffix 사용 (`.vanilla`, `.jakarta`, `.javax`).

---

## 4. 어댑터 등록 절차

1. lane 식별자 결정 (예: `jakarta`) — 위 §2 예약어 외에는 자유
2. **3개 변형 템플릿** 작성 (`entity.jakarta.java.j2`, `service-impl.jakarta.java.j2`, `controller.jakarta.java.j2`)
3. `codegen.py:32` suffix 분기 규칙 확인 (현재는 `vanilla` 하드코딩 — H3 에서 일반화 필요. §6 참조)
4. `precompute.py` 가 lane 별 추가 컨텍스트 필요하면 분기 (e.g. `jakarta_import_prefix`)
5. `compile.py --lane jakarta` 의 `choices` 확장
6. `tests/test_codegen_<lane>.py` + golden fixture

---

## 5. 입력 컨텍스트 — `precompute.build_entity_context`

모든 lane 템플릿이 받는 컨텍스트:

```python
{
    "pascal": "Customer",          # entity name in PascalCase
    "snake": "customer",           # entity name in snake_case
    "table": "customer",           # DB table name
    "fields": [...],               # column metadata
    "pk_columns": [...],           # primary key columns
    "fk_columns": [...],           # foreign key columns
    "base_package": "com.example.order",
    "lane": "vanilla",             # lane echo (템플릿이 분기에 사용 가능)
    # ... 기타
}
```

lane 어댑터가 새 키 요구 시 `build_entity_context` 에 추가 — 다른 lane 의 default 값을 깨지 않도록 주의.

---

## 6. 호환 버전

| 계약 버전 | Stage 3 release | 변경 내용 |
|:-:|:-:|:-|
| **1** | v0.1.0 | `nexacro` lane 만 존재, suffix 무 |
| **1.1** | v0.3.0 Phase B | `vanilla` lane 추가, suffix 컨벤션 도입 |
| **1.2** | v0.4.x | `--lane` CLI flag + orchestrator pass-through |
| **2** ✅ | v0.5.0 H3 | suffix 일반화 (`"" if lane=="nexacro" else f".{lane}"`), `jakarta`/`javax` 추가, `build_domain_fields` 에 `column`/`is_pk`/`is_search` 키 추가(JPA 매핑용) |

### 6.1 H3 의 v2 변경 사항 (계획)

```python
# Before (v1.x)
suffix = ".vanilla" if lane == "vanilla" else ""

# After (v2)
suffix = "" if lane == "nexacro" else f".{lane}"
```

이 변경으로 `codegen.py` 가 lane 추가에 무관해짐 (templates 만 추가하면 동작).

---

## 7. 어댑터별 회귀 테스트 의무

| 테스트 | 목적 | 통과 기준 |
|:-:|:-:|:-:|
| `test_codegen_<lane>_render.py` | 3 변형 + 3 공유 = 6 템플릿 렌더 가능 | TemplateNotFound 0 |
| `test_codegen_<lane>_imports.py` | 생성된 Java 가 올바른 import (jakarta vs javax) | grep 정확 |
| `test_codegen_<lane>_golden.py` | 표준 `customer` blueprint → 골든 .java byte-exact | diff 0 |
| `test_codegen_<lane>_compile.py` *(옵션)* | `javac` 로 컴파일 통과 | exit 0 |

골든 fixture: `tests/golden/fixtures/lane/<name>/`

---

## 8. Karpathy 정신 가드레일

- **lane 추가가 다른 lane 출력에 영향 없음** — 기존 골든 fixture 무회귀가 강제
- **Stage 3 codegen.py 본체는 lane-agnostic** — 분기는 suffix 규칙 한 줄로 한정 (H3 후)
- **공유 인터페이스 안정성** — `service-interface.java.j2` 같이 공유되는 파일은 변경 시 모든 lane 동의 필요
- **단방향**: lane 어댑터는 외부 시스템 상태 없음, blueprint → Java 순수 변환

---

## 9. 계약 위반 시그널

1. 3 변형 템플릿 미만 → 렌더 에러
2. lane 코드가 `codegen.py` 분기에 새로 박힘 (suffix 규칙 외) → 코드리뷰 reject
3. 새 lane 의 공유 인터페이스 변경 → 다른 lane 골든 회귀
4. lane 별 import prefix 차이가 정확하지 않음 → `imports` 테스트 실패

---

## 10. H3 환류 — Reference Implementation 결과

H3 에서 `jakarta`/`javax` 4 lane 모두 reference impl 으로 등록되며 다음 사항이 드러나 v2 계약에 반영:

| 항목 | 변경 | 영향 |
|:-:|:-|:-|
| `suffix` 규칙 | `".vanilla" if lane=="vanilla" else ""` → `"" if lane=="nexacro" else f".{lane}"` | lane 추가 시 `codegen.py` 무수정 (templates 만 추가) |
| `build_domain_fields` | `field`/`java_type`/`getter`/`setter` → +`column`/`is_pk`/`is_search` | JPA `@Id`/`@Column`/`@Transient` 매핑 가능. 기존 nexacro/vanilla 템플릿은 새 키 무시(하위호환) |
| `build_save_branches(lane=)` | `vanilla` 만 I/U/D 문자열 → `vanilla`/`jakarta`/`javax` 모두 I/U/D 문자열 | nexacro 만 `DataSet.ROW_TYPE_*` 상수 유지 |
| `endpoint_base` | `vanilla=/api/{name}`, 그 외 `/ {name}` → `nexacro=/{name}`, 그 외 `/api/{name}` | jakarta/javax controller 도 `@RequestMapping("/api/{name}")` 표준 사용 |
| search field 표현 | (없음) → `@Transient` (JPA lanes 한정) | `searchCondition`/`searchKeyword`/`searchUseYn` 가 DB 컬럼이 아닌 검색 파라미터 |

### 10.1 회귀 테스트 추가 (`tests/`)

- `test_codegen_lane_suffix.py` — 4 lane 모두 6 파일 렌더
- `test_codegen_lane_jakarta.py` — `jakarta.persistence.*` import, `@Entity`/`@Table`/`@Id`/`@Transient`, REST controller, I/U/D 분기
- `test_codegen_lane_javax.py` — 동일하지만 `javax.persistence.*`

`pytest`: 72 passed (기존 59 + 신규 13). 회귀 0.

### 10.2 CLI 진입점

| 위치 | 변경 |
|:-|:-|
| `andrej-karpathy-rdb-mybatis/scripts/compile.py:24` | `choices=["nexacro","vanilla","jakarta","javax"]` |
| `business-fullstack-creater/scripts/scaffold_cli.py:61` | `choices=("nexacro","vanilla","jakarta","javax")` |
| `business-fullstack-creater/scripts/scaffold_orchestrator.py:16` | 주석 lane Union 갱신 |

### 10.3 잔여 갭

| Gap | 후속 milestone |
|:-:|:-|
| jakarta/javax service-impl 에 `@Transactional` 미부착 | H4 (또는 v0.5.1) — 옵션 컨텍스트 키 |
| JPA 사용 시 mapper XML 과의 역할 분담 (둘 다 emit 됨) | v0.6 — JPA lane 에서 mapper.xml 생략 옵션 |
| controller 응답 envelope 표준화 (현재 `List<Map>` 로 통일) | v0.6 — `ResponseEntity<DTO>` 옵션 |
