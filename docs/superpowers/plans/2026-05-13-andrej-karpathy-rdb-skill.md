# andrej-karpathy-rdb-skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Andrej Karpathy의 LLM Wiki 패턴을 RDB 비즈니스-도메인-엔티티 컨텍스트에 이식한 marketplace 플러그인을 구현하여, business-fullstack-creater 파이프라인의 1단계(Plan)를 담당시킨다. 산출물은 markdown wiki와 `_blueprint.yaml` manifest이며, 2단계 DDL 생성 플러그인이 manifest를 입력으로 소비한다.

**Architecture:** 별도 Claude Code marketplace 플러그인 repo. `init`/`ingest`/`compile` 3개 슬래시 커맨드, SKILL.md 자동 발동, 5계층 wiki 디렉터리, frontmatter 기반 entity/concept 정의, Python CLI(`rdb_index.py`)로 lint/index 생성. Wiki-first 컴파일 모델 — markdown이 진실의 근원, manifest는 항상 생성 산출물.

**Tech Stack:** Markdown + YAML frontmatter, Python 3.11+ (PyYAML, pathlib), Claude Code Plugin Manifest, 한국어 기본.

**Spec reference:** `docs/superpowers/specs/2026-05-13-andrej-karpathy-rdb-skill-design.md`

**Plugin repo location:** `D:\AI\workspace\andrej-karpathy-rdb-skill\` (별도 repo, business-fullstack-creater와 sibling)

---

## 🚩 이정표 (Milestone) 개요

| Milestone | Phase | Tasks | 검증 게이트 |
| :-: | :-- | :-: | :-- |
| **M1** | Plugin 골격 | A (1~2) | `plugin.json`이 Claude Code 마켓플레이스 manifest 스펙 만족, git 초기 커밋 |
| **M2** | Wiki 템플릿 | B (3~7) | 모든 템플릿 frontmatter YAML 파싱 성공 |
| **M3** | 프로토콜 정의 | C (8~10) | init/ingest/compile 3개 프로토콜 markdown 완성 |
| **M4** | 레퍼런스 | D (11~12) | frontmatter 스키마 + blueprint 스키마 명시 |
| **M5** | 슬래시 커맨드 + SKILL | E·F (13~16) | 3개 command + SKILL.md 자동 발동 가능 |
| **M6** | 도메인 프리셋 | G (17) | 5개 프리셋 모두 entity·concept seed 제공 |
| **M7** | 사용자 가이드 | H (18~20) | README.ko / README.en / INSTALL-FOR-AI 완성 |
| **M8** | CLI + 통합 검증 | I (21~22) | rdb_index.py가 V001~V010 모두 검증, 골든패스 통과 |
| **M9** | 부모 프로젝트 통합 | J (23) | business-fullstack-creater needs 문서 갱신 + 2단계 contract 명시 |

각 Task 마지막 step은 `git commit`. 각 Milestone 끝에는 통합 검증.

---

## File Structure (전체 산출물 맵)

```
D:\AI\workspace\andrej-karpathy-rdb-skill\          (NEW REPO)
├── plugin.json                                      [T2]
├── README.md                                        [T19]
├── README.ko.md                                     [T18]  ⭐ default
├── INSTALL-FOR-AI.md                                [T20]
├── .gitignore                                       [T1]
├── .claude/
│   ├── commands/
│   │   ├── karpathy-rdb-init.md                     [T13]
│   │   ├── karpathy-rdb-ingest.md                   [T14]
│   │   └── karpathy-rdb-compile.md                  [T15]
│   └── skills/
│       └── karpathy-rdb/
│           ├── SKILL.md                              [T16]
│           ├── wiki-template/                        [T3~T7]
│           │   ├── _schema.md                        [T3]
│           │   ├── _protocols.md                     [T3]
│           │   ├── _log.md                           [T3]
│           │   ├── rules.md                          [T7]
│           │   ├── false-beliefs.md                  [T7]
│           │   ├── raw/.gitkeep                      [T7]
│           │   ├── sources/_template.md              [T7]
│           │   ├── domains/_template/profile.md      [T4]
│           │   ├── entities/_template/profile.md     [T5]
│           │   ├── concepts/_template.md             [T6]
│           │   ├── decisions/_template.md            [T7]
│           │   ├── explorations/_template.md         [T7]
│           │   └── comparisons/_template.md          [T7]
│           ├── protocols/
│           │   ├── 01-init.md                        [T8]
│           │   ├── 02-ingest.md                      [T9]
│           │   └── 03-compile.md                     [T10]
│           ├── references/
│           │   ├── frontmatter-schema.md             [T11]
│           │   └── blueprint-spec.md                 [T12]
│           └── presets/
│               ├── README.md                         [T17]
│               ├── 고객관리.seed.md                  [T17]
│               ├── 주문관리.seed.md                  [T17]
│               ├── 재고관리.seed.md                  [T17]
│               ├── 인사관리.seed.md                  [T17]
│               └── 재무관리.seed.md                  [T17]
├── scripts/
│   └── rdb_index.py                                  [T21]
└── tests/
    ├── conftest.py                                   [T21]
    ├── test_frontmatter.py                           [T21]
    ├── test_validators.py                            [T21]
    └── fixtures/
        ├── golden_wiki/                              [T22]
        └── expected_blueprint.yaml                   [T22]

D:\AI\workspace\business-fullstack-creater\          (EXISTING)
└── needs\
    └── Plugin참조\
        ├── 1. Plan - andrej-karpathy-rdb-skill 구현.md   [T23: 갱신 - 완료 표시]
        └── 2. Backend - DB 스키마(DDL) 생성하기.md        [T23: 갱신 - contract 추가]
```

---

# Phase A — Plugin 골격 (M1)

## Task 1: Plugin repo 초기화

**Files:**
- Create: `D:\AI\workspace\andrej-karpathy-rdb-skill\.gitignore`

- [ ] **Step 1: Plugin repo 디렉터리 생성 및 git init**

```powershell
New-Item -ItemType Directory -Path "D:\AI\workspace\andrej-karpathy-rdb-skill" -Force
Set-Location "D:\AI\workspace\andrej-karpathy-rdb-skill"
git init
```

Expected: `Initialized empty Git repository in D:/AI/workspace/andrej-karpathy-rdb-skill/.git/`

- [ ] **Step 2: .gitignore 작성**

Create `D:\AI\workspace\andrej-karpathy-rdb-skill\.gitignore`:

```
__pycache__/
*.pyc
.pytest_cache/
.venv/
venv/
.env
.idea/
.vscode/
*.log
.DS_Store
Thumbs.db
```

- [ ] **Step 3: Initial commit**

```powershell
git add .gitignore
git commit -m "chore: initialize plugin repo"
```

Expected: 1 file changed, commit hash returned.

---

## Task 2: plugin.json 작성

**Files:**
- Create: `D:\AI\workspace\andrej-karpathy-rdb-skill\plugin.json`

- [ ] **Step 1: plugin.json 작성**

Create `D:\AI\workspace\andrej-karpathy-rdb-skill\plugin.json`:

```json
{
  "name": "andrej-karpathy-rdb-skill",
  "version": "0.1.0",
  "description": "Karpathy LLM Wiki 패턴을 RDB 비즈니스-도메인-엔티티 컨텍스트에 이식한 플러그인. markdown wiki + _blueprint.yaml 산출",
  "author": "business-fullstack-creater",
  "keywords": ["claude-code", "plugin", "rdb", "schema-design", "karpathy", "wiki", "korean"],
  "claudeCode": {
    "minVersion": "2.0.0"
  },
  "entries": {
    "commands": ".claude/commands/",
    "skills": ".claude/skills/"
  }
}
```

- [ ] **Step 2: JSON 파싱 검증**

```powershell
python -c "import json; print(json.load(open('plugin.json', encoding='utf-8')))"
```

Expected: dict 출력, JSONDecodeError 없음.

- [ ] **Step 3: Commit**

```powershell
git add plugin.json
git commit -m "feat: add plugin manifest"
```

### 🚩 Milestone M1 Gate
- `plugin.json` 존재 + JSON 파싱 성공
- git 커밋 2개 (init + manifest)

---

# Phase B — Wiki 템플릿 (M2)

## Task 3: wiki-template 메타파일 3종 (`_schema.md`, `_protocols.md`, `_log.md`)

**Files:**
- Create: `.claude\skills\karpathy-rdb\wiki-template\_schema.md`
- Create: `.claude\skills\karpathy-rdb\wiki-template\_protocols.md`
- Create: `.claude\skills\karpathy-rdb\wiki-template\_log.md`

- [ ] **Step 1: 디렉터리 생성**

```powershell
New-Item -ItemType Directory -Path ".claude\skills\karpathy-rdb\wiki-template" -Force
```

- [ ] **Step 2: `_schema.md` 작성 (헌법)**

Create `.claude\skills\karpathy-rdb\wiki-template\_schema.md`:

```markdown
---
type: schema
version: 1
generated_by: karpathy-rdb init
locale: ko
---

# Wiki 헌법 (_schema.md)

> 본 wiki는 RDB 스키마 설계를 위한 markdown 기반 진실의 근원. AI는 매 작업 전 본 파일을 읽는다.

## 1. 5계층 변화율 구조
- `raw/` — 불변 원본 요구사항
- `sources/` — LLM 압축 요약 (1 source = 1 page)
- `domains/`, `entities/`, `concepts/` — 주/월 단위 갱신
- `explorations/` — 쿼리당 갱신
- `decisions/`, `rules.md`, `false-beliefs.md` — 분기 단위 갱신

## 2. 용어
- **Domain (도메인)**: 비즈니스 영역 (예: 고객관리). 여러 entity를 포함.
- **Entity (엔티티)**: 1 DB 테이블 = 1 entity. frontmatter에 PK/FK/columns 정의.
- **Concept (개념)**: ER 관계, 비즈니스 규칙, 불변식. entity 간 연결을 담당.

## 3. 식별자 규약
- entity name: `snake_case` 영문 (예: `customer`, `order_item`)
- table name: entity name 그대로
- column name: `snake_case` 영문
- 표시명(`display`): 한국어 허용

## 4. 변경 절차
1. `/karpathy-rdb ingest`로 원본·프롬프트를 wiki 페이지로 변환
2. `/karpathy-rdb compile`로 wiki → `_blueprint.yaml` 생성 + 정합성 검증
3. 검증 실패 시 wiki 수정 후 재컴파일

## 5. 핸드오프
`_blueprint.yaml`은 2단계 DDL 생성 플러그인의 공식 입력. 스키마는 `references/blueprint-spec.md` 참조.
```

- [ ] **Step 3: `_protocols.md` 작성 (작업 프로토콜 인덱스)**

Create `.claude\skills\karpathy-rdb\wiki-template\_protocols.md`:

```markdown
---
type: protocols
---

# 작업 프로토콜 인덱스

본 파일은 AI가 작업 전 매번 읽는다. 각 프로토콜의 상세는 plugin의 `protocols/` 디렉터리 참조.

## Protocol 1 — Ingest (`protocols/02-ingest.md`)
입력(프롬프트 또는 raw 파일) → `sources/`, `domains/`, `entities/`, `concepts/` 갱신.

핵심 규칙:
1. 새 entity는 `entities/<name>/profile.md` 생성, 필수 frontmatter 채움
2. 새 관계는 `concepts/<from>-<verb>-<to>.md` 생성
3. 매 작업 후 `_log.md`에 1줄 추가: `YYYY-MM-DD HH:MM | ingest | <요약>`
4. 절대 silent overwrite 금지 — 충돌 시 `decisions/`에 기록

## Protocol 2 — Compile (`protocols/03-compile.md`)
wiki 전체 → `_blueprint.yaml` + `compile-report.md`.

핵심 규칙:
1. `entities/*/profile.md`와 `concepts/*.md`의 frontmatter를 읽어 manifest 빌드
2. V001~V010 검증 실행
3. ERROR가 있으면 `compile-report.md`에 기록하고 `_blueprint.yaml`의 `validation.passed: false`
4. WARN/INFO만 있으면 `validation.passed: true`로 생성

## Protocol 3 — Init (`protocols/01-init.md`)
빈 프로젝트에 wiki 골격 + 선택한 도메인 프리셋 적용.
```

- [ ] **Step 4: `_log.md` 작성 (빈 로그 헤더)**

Create `.claude\skills\karpathy-rdb\wiki-template\_log.md`:

```markdown
---
type: log
---

# 작업 로그

> 모든 ingest/compile 작업은 본 파일에 1줄로 기록된다.
> 형식: `YYYY-MM-DD HH:MM | <action> | <요약>`

```

- [ ] **Step 5: Commit**

```powershell
git add .claude/skills/karpathy-rdb/wiki-template/_schema.md `
        .claude/skills/karpathy-rdb/wiki-template/_protocols.md `
        .claude/skills/karpathy-rdb/wiki-template/_log.md
git commit -m "feat(wiki-template): add 3 meta files (_schema, _protocols, _log)"
```

---

## Task 4: Domain 템플릿

**Files:**
- Create: `.claude\skills\karpathy-rdb\wiki-template\domains\_template\profile.md`

- [ ] **Step 1: Domain 템플릿 작성**

Create `.claude\skills\karpathy-rdb\wiki-template\domains\_template\profile.md`:

```markdown
---
type: domain
name: <domain-name>                  # snake_case 영문 또는 한국어 모두 허용
display: <도메인 표시명>              # 한국어 표시명
description: <한 줄 설명>
entities: []                          # 소속 entity name 리스트
concepts: []                          # 도메인 내부 concept 리스트
status: draft                         # draft | reviewed | locked
sources: []
---

# <도메인 표시명>

## 의미
<도메인의 비즈니스 의미를 2~3문장으로>

## 소속 엔티티
<entities 리스트의 위키링크>

## 도메인 내 관계
<concepts 리스트의 위키링크>

## 외부 도메인 의존성
<다른 도메인과의 관계 (예: 주문관리 → 고객관리)>
```

- [ ] **Step 2: YAML frontmatter 파싱 검증**

```powershell
python -c "import yaml; doc = open('.claude/skills/karpathy-rdb/wiki-template/domains/_template/profile.md', encoding='utf-8').read(); fm = doc.split('---')[1]; print(yaml.safe_load(fm))"
```

Expected: dict 출력, `type: domain` 포함.

- [ ] **Step 3: Commit**

```powershell
git add .claude/skills/karpathy-rdb/wiki-template/domains/
git commit -m "feat(wiki-template): add domain profile template"
```

---

## Task 5: Entity 템플릿

**Files:**
- Create: `.claude\skills\karpathy-rdb\wiki-template\entities\_template\profile.md`

- [ ] **Step 1: Entity 템플릿 작성**

Create `.claude\skills\karpathy-rdb\wiki-template\entities\_template\profile.md`:

```markdown
---
type: entity
name: <entity_name>                  # snake_case 영문 (예: customer)
display: <표시명>                     # 한국어
domain: []                            # 소속 도메인 리스트
table: <table_name>                  # 물리 테이블명, 기본 = name
schema: public                        # PostgreSQL 스키마
status: draft                         # draft | reviewed | locked
columns:
  - { name: id, type: bigserial, pk: true, null: false }
  - { name: created_at, type: timestamptz, null: false, default: now() }
  - { name: updated_at, type: timestamptz, null: false, default: now() }
indexes: []
constraints: []
relations: []
sources: []
decisions: []
---

# <표시명> (<entity_name>)

## 의미
<엔티티의 비즈니스 의미>

## 컬럼 설명
| 컬럼 | 의미 | 비고 |
| :-- | :-- | :-- |
| id | 대리키 | bigserial |

## 비즈니스 규칙
- <규칙 1>

## 관련
- 도메인: <위키링크>
- 관계: <위키링크>
```

- [ ] **Step 2: frontmatter 파싱 검증**

```powershell
python -c "import yaml; doc = open('.claude/skills/karpathy-rdb/wiki-template/entities/_template/profile.md', encoding='utf-8').read(); fm = doc.split('---')[1]; d = yaml.safe_load(fm); assert d['type'] == 'entity'; assert any(c.get('pk') for c in d['columns']); print('OK')"
```

Expected: `OK` 출력.

- [ ] **Step 3: Commit**

```powershell
git add .claude/skills/karpathy-rdb/wiki-template/entities/
git commit -m "feat(wiki-template): add entity profile template with column/index/relation frontmatter"
```

---

## Task 6: Concept 템플릿

**Files:**
- Create: `.claude\skills\karpathy-rdb\wiki-template\concepts\_template.md`

- [ ] **Step 1: Concept 템플릿 작성**

Create `.claude\skills\karpathy-rdb\wiki-template\concepts\_template.md`:

```markdown
---
type: concept
kind: relation                       # relation | rule | invariant | terminology
name: <from>-<verb>-<to>             # 예: customer-has-many-addresses
cardinality: 1:N                     # 1:1 | 1:N | N:M | self  (kind=relation일 때)
from: <entity_name>
to: <entity_name>
fk_column: <column_name>             # FK가 위치하는 컬럼 (N 쪽)
on_delete: restrict                  # restrict | cascade | set_null
status: draft
sources: []
---

# <개념 표시명>

## 정의
<개념의 명확한 정의 1~2문장>

## 근거
<요구사항 또는 비즈니스 규칙 출처>

## 영향
<이 개념이 강제하는 제약·인덱스·triggers>
```

- [ ] **Step 2: frontmatter 검증**

```powershell
python -c "import yaml; doc = open('.claude/skills/karpathy-rdb/wiki-template/concepts/_template.md', encoding='utf-8').read(); fm = doc.split('---')[1]; d = yaml.safe_load(fm); assert d['type'] == 'concept'; assert d['kind'] in ['relation','rule','invariant','terminology']; print('OK')"
```

Expected: `OK`.

- [ ] **Step 3: Commit**

```powershell
git add .claude/skills/karpathy-rdb/wiki-template/concepts/
git commit -m "feat(wiki-template): add concept template with relation/rule/invariant kinds"
```

---

## Task 7: 나머지 wiki 디렉터리 (sources, decisions, explorations, comparisons, rules, false-beliefs, raw)

**Files:**
- Create: `.claude\skills\karpathy-rdb\wiki-template\sources\_template.md`
- Create: `.claude\skills\karpathy-rdb\wiki-template\decisions\_template.md`
- Create: `.claude\skills\karpathy-rdb\wiki-template\explorations\_template.md`
- Create: `.claude\skills\karpathy-rdb\wiki-template\comparisons\_template.md`
- Create: `.claude\skills\karpathy-rdb\wiki-template\rules.md`
- Create: `.claude\skills\karpathy-rdb\wiki-template\false-beliefs.md`
- Create: `.claude\skills\karpathy-rdb\wiki-template\raw\.gitkeep`

- [ ] **Step 1: sources/_template.md**

Create `.claude\skills\karpathy-rdb\wiki-template\sources\_template.md`:

```markdown
---
type: source
id: SRC-XXX
date: YYYY-MM-DD
raw_file: raw/<filename>
title: <원본 제목>
status: compiled
entities_mentioned: []
concepts_mentioned: []
---

# <원본 제목>

## 핵심 요약
<3~5줄 요약>

## 추출된 엔티티 후보
- <entity 1> — <근거 문장>

## 추출된 관계 후보
- <from> ↔ <to> (<cardinality>) — <근거 문장>

## 추출된 비즈니스 규칙
- <규칙 1>

## 미해결 질문
- <질문 1>
```

- [ ] **Step 2: decisions/_template.md**

Create `.claude\skills\karpathy-rdb\wiki-template\decisions\_template.md`:

```markdown
---
type: decision
id: DEC-XXX
date: YYYY-MM-DD
status: proposed                     # proposed | accepted | superseded
related_entities: []
related_concepts: []
---

# <결정 제목>

## 컨텍스트
<왜 결정이 필요한가>

## 대안
1. <대안 A>: 장점/단점
2. <대안 B>: 장점/단점

## 결정
<선택한 대안 + 이유>

## 결과
<예상 영향>
```

- [ ] **Step 3: explorations/_template.md**

Create `.claude\skills\karpathy-rdb\wiki-template\explorations\_template.md`:

```markdown
---
type: exploration
id: EXP-XXX
question: <한 줄 질문>
status: open                         # open | resolved
linked_decisions: []
---

# <탐색 제목>

## 질문
<명확한 질문>

## 가설
1. <가설 A>
2. <가설 B>

## 조사 결과
<자료/근거>

## 결론
<resolved일 때 결론 + linked_decisions로 연결>
```

- [ ] **Step 4: comparisons/_template.md**

Create `.claude\skills\karpathy-rdb\wiki-template\comparisons\_template.md`:

```markdown
---
type: comparison
id: CMP-XXX
subject: <비교 주제>
---

# <비교 주제>

|  | 옵션 A | 옵션 B |
| :-- | :-- | :-- |
| 정의 | | |
| 장점 | | |
| 단점 | | |
| 권장 | | |
```

- [ ] **Step 5: rules.md**

Create `.claude\skills\karpathy-rdb\wiki-template\rules.md`:

```markdown
---
type: rules
---

# 검증된 비즈니스 규칙

> 3회 이상 사례로 확인된 규칙만 등재. lifecycle: `observation → pattern → RULE → under review → retired`

## Promotion Log
<lifecycle 이벤트 기록>

## RULE
- (없음)
```

- [ ] **Step 6: false-beliefs.md**

Create `.claude\skills\karpathy-rdb\wiki-template\false-beliefs.md`:

```markdown
---
type: false-beliefs
---

# 반증된 통념

> 데이터·사례로 반증된 통념을 기록. 새 entity·rule 추가 시 본 파일과 충돌하는지 확인.

## 통념
- (없음)
```

- [ ] **Step 7: raw/.gitkeep**

Create `.claude\skills\karpathy-rdb\wiki-template\raw\.gitkeep`:

```
```

(빈 파일 — raw/ 디렉터리를 git에 등록하기 위함)

- [ ] **Step 8: 모든 템플릿의 frontmatter 일괄 검증**

```powershell
python -c "
import yaml, pathlib
root = pathlib.Path('.claude/skills/karpathy-rdb/wiki-template')
errors = []
for md in root.rglob('*.md'):
    text = md.read_text(encoding='utf-8')
    if not text.startswith('---'):
        errors.append(f'{md}: no frontmatter')
        continue
    fm = text.split('---', 2)[1]
    try:
        d = yaml.safe_load(fm)
        if not isinstance(d, dict) or 'type' not in d:
            errors.append(f'{md}: missing type')
    except yaml.YAMLError as e:
        errors.append(f'{md}: {e}')
print('ERRORS:' if errors else 'ALL OK')
for e in errors: print(' -', e)
"
```

Expected: `ALL OK`.

- [ ] **Step 9: Commit**

```powershell
git add .claude/skills/karpathy-rdb/wiki-template/
git commit -m "feat(wiki-template): add sources/decisions/explorations/comparisons templates + rules/false-beliefs/raw"
```

### 🚩 Milestone M2 Gate
- wiki-template 전체 frontmatter 파싱 100% 성공
- 모든 템플릿이 `type:` 필드 포함

---

# Phase C — 프로토콜 (M3)

## Task 8: `protocols/01-init.md` (Phase 1~6 설치 프로토콜)

**Files:**
- Create: `.claude\skills\karpathy-rdb\protocols\01-init.md`

- [ ] **Step 1: 01-init.md 작성**

Create `.claude\skills\karpathy-rdb\protocols\01-init.md`:

```markdown
---
type: protocol
protocol: init
version: 1
---

# Protocol 01 — Init

`/karpathy-rdb init <도메인명> [--preset <preset-key>]` 실행 시 AI가 따르는 절차.

## Phase 1 — Clarify (한 번에 한 질문)
1. **wiki 디렉터리 위치?** 기본: `./wiki/`. 이미 존재하면 abort.
2. **추가 도메인 프리셋?** 사용자가 명령에 `--preset`를 주지 않았다면 후보 제시 (고객관리/주문관리/재고관리/인사관리/재무관리/없음).
3. **프로젝트 루트에 `CLAUDE.md` 있나?** 없으면 신규 생성, 있으면 wiki 섹션만 추가.
4. **시작 entity 1개?** 예시 entity 이름 (snake_case 영문).

## Phase 2 — Scaffold
1. plugin의 `wiki-template/` 전체를 사용자 프로젝트의 `wiki/`로 복사
2. `wiki/raw/.gitkeep` 유지 (빈 디렉터리 보존)

## Phase 3 — 도메인 커스터마이즈
1. `wiki/domains/_template/` → `wiki/domains/<도메인명>/`로 복사·rename
2. `_template/profile.md`의 placeholder를 도메인명으로 치환
3. 선택한 preset이 있으면 `presets/<도메인>.seed.md`의 내용을 wiki에 적용 (entities/concepts 시드 페이지 생성)

## Phase 4 — `CLAUDE.md` 통합
프로젝트 루트의 `CLAUDE.md`에 다음 섹션 추가 (없으면 파일 생성):

```
## RDB Wiki
이 프로젝트는 `wiki/`에 RDB 설계 문서를 관리한다.
- 모든 ingest/compile 전 `wiki/_schema.md`, `wiki/_protocols.md`를 읽는다.
- 새 entity 추가 시 관련 domain·concept을 갱신한다.
```

## Phase 5 — 첫 Entity Scaffold
Phase 1 Q4에서 받은 entity 이름으로:
1. `wiki/entities/<name>/profile.md`를 `entities/_template/profile.md`에서 복사
2. frontmatter의 `name`, `display`, `table`을 채움 (display는 사용자에게 한 번 더 물음)
3. 본문은 비워둠 — 내용 추측 금지

## Phase 6 — Verify + Hand-off
1. `python scripts/rdb_index.py --lint wiki/` 실행 (plugin scripts/ 경로)
2. 에러 0개 확인
3. 사용자에게 안내:
   > "wiki/ 설치 완료. 다음: `/karpathy-rdb ingest`로 요구사항을 추가하세요. `wiki/_schema.md`와 `wiki/_protocols.md`를 매 작업 전 읽습니다."
```

- [ ] **Step 2: Commit**

```powershell
git add .claude/skills/karpathy-rdb/protocols/01-init.md
git commit -m "feat(protocols): add init protocol (Phase 1-6 install)"
```

---

## Task 9: `protocols/02-ingest.md`

**Files:**
- Create: `.claude\skills\karpathy-rdb\protocols\02-ingest.md`

- [ ] **Step 1: 02-ingest.md 작성**

Create `.claude\skills\karpathy-rdb\protocols\02-ingest.md`:

```markdown
---
type: protocol
protocol: ingest
version: 1
---

# Protocol 02 — Ingest

`/karpathy-rdb ingest [<프롬프트>|--file <path>]` 실행 시 AI가 따르는 절차.

## 입력 판별
1. 명령에 자유 프롬프트 텍스트 → **프롬프트 모드**
2. `wiki/raw/`에 미처리 파일(`_log.md`에 미등재) 존재 → **파일 모드**
3. 둘 다이면 파일 우선

## 프롬프트 모드 절차
1. **요약 압축**: 입력을 `sources/YYYY-MM-DD-prompt-<slug>.md`에 저장 (sources 템플릿 사용). 원본 프롬프트는 `raw/YYYY-MM-DD-prompt-<slug>.md`에 보존.
2. **엔티티 후보 추출**: 입력에서 명사구를 후보로 식별. 사용자에게 한 번 확인 후 신규 entity 생성.
3. **관계 후보 추출**: 동사·소유격에서 관계 후보 식별 (예: "고객은 주소를 가진다" → `customer-has-many-addresses` concept).
4. **갱신**: 각 entity의 frontmatter `columns`, `relations`, `sources` 필드 갱신.

## 파일 모드 절차
1. `raw/`의 신규 파일을 1개씩 처리
2. 파일 내용을 위와 동일하게 압축 → sources/ 페이지
3. 같은 추출 절차

## 충돌 처리
- 기존 entity와 새 정보 충돌 (예: 같은 컬럼 다른 타입) → `decisions/conflict-<YYYY-MM-DD>-<topic>.md` 생성 후 사용자에게 alert
- 절대 silent overwrite 금지

## 후처리
1. `_log.md`에 1줄 추가: `YYYY-MM-DD HH:MM | ingest | <요약 한 줄>`
2. 사용자에게 결과 보고: 생성/갱신된 페이지 목록, 미해결 질문

## 멱등성
같은 source를 재ingest 시 sources/ 페이지는 갱신, entity/concept는 diff만 적용 (기존 정보 보존).
```

- [ ] **Step 2: Commit**

```powershell
git add .claude/skills/karpathy-rdb/protocols/02-ingest.md
git commit -m "feat(protocols): add ingest protocol (prompt/file hybrid, conflict handling)"
```

---

## Task 10: `protocols/03-compile.md` (V001~V010 검증 규칙 포함)

**Files:**
- Create: `.claude\skills\karpathy-rdb\protocols\03-compile.md`

- [ ] **Step 1: 03-compile.md 작성**

Create `.claude\skills\karpathy-rdb\protocols\03-compile.md`:

```markdown
---
type: protocol
protocol: compile
version: 1
---

# Protocol 03 — Compile

`/karpathy-rdb compile` 실행 시 AI가 따르는 절차.

## 절차
1. **스캔**: `wiki/entities/*/profile.md`, `wiki/concepts/*.md`, `wiki/domains/*/profile.md`의 frontmatter 읽기
2. **빌드**: `wiki/_blueprint.yaml` 생성 (스키마는 `references/blueprint-spec.md` 참조)
3. **검증**: V001~V010 실행
4. **보고**: `wiki/compile-report.md` 작성
5. **로그**: `_log.md`에 1줄 추가

## 검증 규칙

| 코드 | 레벨 | 검증 |
| :-: | :-: | :-- |
| V001 | ERROR | 모든 entity는 PK 컬럼 1개 이상 (`columns[].pk: true`) |
| V002 | ERROR | `relations.fk_column`이 to-entity의 PK 또는 UQ 컬럼을 참조해야 함 |
| V003 | WARN | 컬럼명은 `snake_case`, PostgreSQL 예약어 회피 (목록: `references/blueprint-spec.md`) |
| V004 | WARN | FK 컬럼 타입이 참조 PK 타입과 동일해야 함 |
| V005 | WARN | entity 간 FK 순환 의존 검출 (DAG가 아님) |
| V006 | WARN | concept이 참조하는 entity가 wiki에 미존재 |
| V007 | WARN | entity가 어떤 domain에도 속하지 않음 (`domain: []`) |
| V008 | INFO | `rules.md`의 RULE이 어느 entity·concept에 매핑되는지 보고 |
| V009 | INFO | entity의 `sources: []` 비어있음 (출처 미기록) |
| V010 | INFO | `status: locked` entity는 `decisions: []`에 1개 이상 권장 |

## ERROR가 있는 경우
- `_blueprint.yaml`의 `validation.passed: false`
- `compile-report.md` 상단에 ERROR 카운트 + 상세
- 2단계로 핸드오프 차단

## 보고서 포맷 (`compile-report.md`)
```
# Compile Report — YYYY-MM-DD HH:MM

## Summary
- ERROR: N
- WARN: N
- INFO: N
- entities: N, concepts: N, domains: N

## Details
### ERROR
- V001 [entity:foo]: PK 컬럼 없음 — `columns[].pk: true`인 컬럼 1개 이상 필요

### WARN
- ...

### INFO
- ...
```
```

- [ ] **Step 2: Commit**

```powershell
git add .claude/skills/karpathy-rdb/protocols/03-compile.md
git commit -m "feat(protocols): add compile protocol with V001-V010 validation rules"
```

### 🚩 Milestone M3 Gate
- 3개 프로토콜 markdown 모두 작성
- V001~V010 검증 규칙 명시
- Phase 1~6 설치 절차 명시

---

# Phase D — 레퍼런스 (M4)

## Task 11: `references/frontmatter-schema.md`

**Files:**
- Create: `.claude\skills\karpathy-rdb\references\frontmatter-schema.md`

- [ ] **Step 1: frontmatter-schema.md 작성**

Create `.claude\skills\karpathy-rdb\references\frontmatter-schema.md`:

```markdown
---
type: reference
---

# Frontmatter Schema Reference

본 문서는 wiki/ 안의 모든 markdown 파일이 따라야 하는 YAML frontmatter 스키마를 정의한다.

## Entity (`entities/<name>/profile.md`)

| 필드 | 타입 | 필수 | 설명 |
| :-- | :-- | :-: | :-- |
| `type` | string | ✅ | 항상 `entity` |
| `name` | string | ✅ | snake_case 영문 식별자 |
| `display` | string | ⬜ | 한국어 표시명 |
| `domain` | string[] | ✅ | 소속 도메인 (1개 이상 권장 — V007) |
| `table` | string | ⬜ | 물리 테이블명 (기본 = `name`) |
| `schema` | string | ⬜ | PostgreSQL 스키마 (기본 `public`) |
| `status` | enum | ✅ | `draft` \| `reviewed` \| `locked` |
| `columns` | object[] | ✅ | 컬럼 정의. PK 1개 이상 — V001 |
| `indexes` | object[] | ⬜ | 인덱스 정의 |
| `constraints` | object[] | ⬜ | CHECK 등 추가 제약 |
| `relations` | object[] | ⬜ | 관계 (concept 링크) |
| `sources` | wikilink[] | ⬜ | 출처 (`[[sources/...]]`) |
| `decisions` | wikilink[] | ⬜ | 결정 로그 (locked일 때 권장 — V010) |

### `columns[]` 객체
```yaml
- name: <snake_case>           # 필수
  type: <pg type>              # 필수: bigserial, varchar(N), text, int, bool, timestamptz, numeric(p,s), jsonb, ...
  pk: <bool>                   # 기본 false
  null: <bool>                 # 기본 true
  unique: <bool>               # 기본 false
  default: <expr>              # SQL expression
  comment: <string>            # 선택
```

### `indexes[]` 객체
```yaml
- name: ix_<table>_<cols>      # 필수
  columns: [<col>, ...]        # 필수
  unique: <bool>               # 기본 false
  method: btree|gin|gist|hash  # 기본 btree
```

### `relations[]` 객체
```yaml
- kind: has_many|has_one|belongs_to|many_to_many   # 필수
  to: <entity name>            # 필수
  fk: <column name>            # 필수 (N 쪽 기준)
  concept: "[[<concept name>]]"  # 필수
```

## Concept (`concepts/<name>.md`)

| 필드 | 타입 | 필수 | 설명 |
| :-- | :-- | :-: | :-- |
| `type` | string | ✅ | 항상 `concept` |
| `kind` | enum | ✅ | `relation` \| `rule` \| `invariant` \| `terminology` |
| `name` | string | ✅ | `<from>-<verb>-<to>` 형식 권장 |
| `cardinality` | enum | ⬜* | `1:1` \| `1:N` \| `N:M` \| `self` (*kind=relation일 때 필수) |
| `from` | string | ⬜* | entity name (*kind=relation일 때) |
| `to` | string | ⬜* | entity name (*kind=relation일 때) |
| `fk_column` | string | ⬜* | FK 컬럼명 (*kind=relation일 때) |
| `on_delete` | enum | ⬜ | `restrict` \| `cascade` \| `set_null` (기본 restrict) |
| `status` | enum | ✅ | `draft` \| `reviewed` \| `locked` |

## Domain (`domains/<name>/profile.md`)

| 필드 | 타입 | 필수 | 설명 |
| :-- | :-- | :-: | :-- |
| `type` | string | ✅ | 항상 `domain` |
| `name` | string | ✅ | 식별자 |
| `display` | string | ⬜ | 한국어 표시명 |
| `description` | string | ⬜ | 한 줄 설명 |
| `entities` | string[] | ✅ | 소속 entity name 리스트 |
| `concepts` | string[] | ⬜ | 도메인 내부 concept 리스트 |
| `status` | enum | ✅ | `draft` \| `reviewed` \| `locked` |
```

- [ ] **Step 2: Commit**

```powershell
git add .claude/skills/karpathy-rdb/references/frontmatter-schema.md
git commit -m "docs(references): add frontmatter schema for entity/concept/domain"
```

---

## Task 12: `references/blueprint-spec.md` (2단계 계약)

**Files:**
- Create: `.claude\skills\karpathy-rdb\references\blueprint-spec.md`

- [ ] **Step 1: blueprint-spec.md 작성**

Create `.claude\skills\karpathy-rdb\references\blueprint-spec.md`:

```markdown
---
type: reference
---

# `_blueprint.yaml` Specification

본 문서는 1단계(`karpathy-rdb compile`)와 2단계(DDL 생성 플러그인) 사이의 공식 계약 스키마.

## 최상위 구조

```yaml
version: 1                          # 정수. 호환 변경 시 증가
generated_at: <ISO-8601>            # 컴파일 타임스탬프
project: <string>                   # wiki/_schema.md의 project name
domains: [...]                      # Domain 객체 배열
entities: [...]                     # Entity 객체 배열
relations: [...]                    # Relation 객체 배열
business_rules: [...]               # Business rule 객체 배열
sources: [...]                      # Source 메타 배열
validation:
  passed: <bool>
  errors: [...]
  warnings: [...]
  infos: [...]
```

## Domain 객체
```yaml
- name: <string>
  description: <string>
  entities: [<entity_name>, ...]
```

## Entity 객체
```yaml
- name: <snake_case>
  table: <string>
  schema: <string>
  columns:
    - { name, type, pk, null, unique, default, comment }
  indexes:
    - { name, columns, unique, method }
  constraints:
    - { name, check }                # CHECK constraint
```

## Relation 객체
```yaml
- from: <entity_name>
  to: <entity_name>
  cardinality: 1:1|1:N|N:M
  fk:
    column: <column_name>
    on_delete: restrict|cascade|set_null
  concept_name: <string>             # 원천 concept (역추적용)
```

N:M은 별도 join entity로 자동 변환 또는 explicit join entity 정의 둘 다 허용.

## Business Rule 객체
```yaml
- id: BR-<NNN>
  text: <한국어 설명>
  enforced_by: [<constraint or index name>, ...]
  source_concept: <concept name>
```

## Source 객체
```yaml
- id: SRC-<NNN>
  file: <relative path from wiki/>
  title: <string>
```

## Validation 객체
```yaml
validation:
  passed: <bool>
  errors:
    - { code: V001, target: "entity:foo", message: "..." }
  warnings: [...]
  infos: [...]
```

## PostgreSQL 예약어 회피 목록 (V003)
다음 단어는 컬럼명·테이블명으로 권장하지 않음:
`user, order, group, table, schema, type, role, name, value, key, primary, foreign, references, default, check, unique, index, constraint, select, insert, update, delete, from, where, join, having, by, on, as, in, is, not, null, true, false`

전체 목록은 PostgreSQL 공식 문서의 `KEY_WORDS` 표 참조.

## 2단계 핸드오프 규약
- 2단계는 본 스키마의 `version`을 먼저 확인해야 함
- `validation.passed: false`이면 DDL 생성 거부
- `entities`·`relations`·`business_rules`만으로 DDL 생성 가능 (다른 필드는 참고용)
```

- [ ] **Step 2: Commit**

```powershell
git add .claude/skills/karpathy-rdb/references/blueprint-spec.md
git commit -m "docs(references): add _blueprint.yaml spec (Phase 1-2 contract)"
```

### 🚩 Milestone M4 Gate
- frontmatter schema와 blueprint spec 두 레퍼런스 완성
- 2단계 계약(`_blueprint.yaml` 구조) 명문화

---

# Phase E — 슬래시 커맨드 (M5)

## Task 13: `/karpathy-rdb init` 커맨드

**Files:**
- Create: `.claude\commands\karpathy-rdb-init.md`

- [ ] **Step 1: 커맨드 파일 작성**

Create `.claude\commands\karpathy-rdb-init.md`:

```markdown
---
name: karpathy-rdb-init
description: RDB wiki 골격을 사용자 프로젝트에 설치하고 도메인 프리셋을 적용한다
argument-hint: "<도메인명> [--preset <preset-key>]"
allowed-tools: Read, Write, Edit, Glob, Bash
---

# /karpathy-rdb init

당신은 안드레이 카파시 LLM Wiki 패턴을 RDB에 적용하는 플러그인의 **init 프로토콜**을 실행하는 에이전트다.

## 사용법
- `/karpathy-rdb init 고객관리`
- `/karpathy-rdb init 주문관리 --preset 주문관리`

## 절차
1. **`.claude/skills/karpathy-rdb/protocols/01-init.md`를 먼저 읽는다.**
2. 그 안의 Phase 1~6을 순서대로 실행한다.
3. Phase 1의 질문은 **한 번에 하나씩** AskUserQuestion으로 물어본다.
4. 모든 phase 완료 후 사용자에게 다음 명령을 안내: `/karpathy-rdb ingest`

## 입력 검증
- `<도메인명>` 미제공 시 사용자에게 한국어로 질문하고 받기
- `wiki/` 디렉터리가 이미 있으면 **즉시 abort**하고 사용자에게 보고 (`init`은 비멱등)
- `--preset`이 있을 때 해당 preset 파일이 plugin의 `presets/`에 없으면 abort

## 산출물
- 사용자 프로젝트의 `wiki/` 디렉터리 (template 복사본 + 도메인 커스터마이즈)
- 프로젝트 루트의 `CLAUDE.md`에 wiki 섹션 추가
- `wiki/entities/<첫entity>/profile.md` 1개

## 완료 보고
- 생성된 파일 트리 (`find wiki -type f` 결과)
- 다음 단계 안내
```

- [ ] **Step 2: Commit**

```powershell
git add .claude/commands/karpathy-rdb-init.md
git commit -m "feat(commands): add /karpathy-rdb init command"
```

---

## Task 14: `/karpathy-rdb ingest` 커맨드

**Files:**
- Create: `.claude\commands\karpathy-rdb-ingest.md`

- [ ] **Step 1: 커맨드 파일 작성**

Create `.claude\commands\karpathy-rdb-ingest.md`:

```markdown
---
name: karpathy-rdb-ingest
description: 자유 프롬프트 또는 wiki/raw/ 파일을 wiki 페이지(entities/concepts/domains)로 ingest
argument-hint: "[<프롬프트>|--file <path>]"
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# /karpathy-rdb ingest

당신은 **ingest 프로토콜**을 실행하는 에이전트다.

## 사용법
- `/karpathy-rdb ingest 고객은 이메일과 이름을 가진다. 이메일은 유일하다.`
- `/karpathy-rdb ingest --file wiki/raw/2026-05-13-요구사항.md`
- `/karpathy-rdb ingest` (인자 없음 → `wiki/raw/`의 미처리 파일 자동 처리)

## 절차
1. **`wiki/_schema.md`, `wiki/_protocols.md` 읽기 (헌법 + 프로토콜)**
2. **`.claude/skills/karpathy-rdb/protocols/02-ingest.md`를 읽는다.**
3. 입력 모드 판별 (프롬프트 vs 파일)
4. 프로토콜 순서대로 실행:
   - 압축 → sources/ 생성
   - entity 후보 추출 → 사용자 확인 → entity 페이지 생성·갱신
   - 관계 후보 추출 → concept 페이지 생성
   - 충돌 검사 → decisions/ 기록
   - `_log.md` 1줄 추가
5. 사용자에게 결과 보고 + 미해결 질문 제시

## 사전 조건
- `wiki/` 존재 (없으면 `/karpathy-rdb init` 안내)

## 산출물
- 신규/갱신된 wiki 페이지 목록 출력
```

- [ ] **Step 2: Commit**

```powershell
git add .claude/commands/karpathy-rdb-ingest.md
git commit -m "feat(commands): add /karpathy-rdb ingest command"
```

---

## Task 15: `/karpathy-rdb compile` 커맨드

**Files:**
- Create: `.claude\commands\karpathy-rdb-compile.md`

- [ ] **Step 1: 커맨드 파일 작성**

Create `.claude\commands\karpathy-rdb-compile.md`:

```markdown
---
name: karpathy-rdb-compile
description: wiki 전체를 스캔하여 _blueprint.yaml 생성 + V001-V010 정합성 검증
argument-hint: ""
allowed-tools: Read, Write, Glob, Grep, Bash
---

# /karpathy-rdb compile

당신은 **compile 프로토콜**을 실행하는 에이전트다.

## 절차
1. **`wiki/_schema.md`, `wiki/_protocols.md` 읽기**
2. **`.claude/skills/karpathy-rdb/protocols/03-compile.md`와 `references/blueprint-spec.md` 읽기**
3. Python CLI 실행: `python scripts/rdb_index.py compile wiki/`
4. 출력 파일 확인:
   - `wiki/_blueprint.yaml`
   - `wiki/compile-report.md`
5. ERROR 카운트 보고. ERROR 있으면 어떤 wiki 페이지를 고쳐야 하는지 안내.

## 사전 조건
- `wiki/` 존재
- `scripts/rdb_index.py` 존재 (plugin install 경로)

## 산출물
- `wiki/_blueprint.yaml`
- `wiki/compile-report.md`
- `_log.md`에 `compile` 이벤트 1줄 추가

## 다음 단계
ERROR 0개일 때 사용자에게: "`_blueprint.yaml`을 2단계 DDL 생성 플러그인에 전달하세요."
```

- [ ] **Step 2: Commit**

```powershell
git add .claude/commands/karpathy-rdb-compile.md
git commit -m "feat(commands): add /karpathy-rdb compile command"
```

---

## Task 16: SKILL.md

**Files:**
- Create: `.claude\skills\karpathy-rdb\SKILL.md`

- [ ] **Step 1: SKILL.md 작성**

Create `.claude\skills\karpathy-rdb\SKILL.md`:

```markdown
---
name: karpathy-rdb
description: |
  사용자가 비즈니스 업무(고객관리, 주문관리, 재고관리, 인사관리, 재무관리 등)의
  DB 스키마/도메인 모델을 설계·정의하려 할 때 자동 발동. Karpathy LLM Wiki 패턴을
  RDB 비즈니스-도메인-엔티티 컨텍스트에 이식하여 markdown wiki와 _blueprint.yaml
  manifest를 산출한다. business-fullstack-creater 파이프라인의 1단계(Plan)를 담당.
argument-hint: "[init|ingest|compile] [도메인명]"
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# karpathy-rdb skill

## 무엇을 하는가
Andrej Karpathy의 LLM Wiki 패턴 (markdown + frontmatter, no vector DB)을 관계형 DB 스키마 설계에 적용. 사용자는 markdown wiki를 큐레이션하고, LLM은 컴파일·정합성 검증을 담당한다.

## 언제 발동되는가
- 사용자가 "<업무명> DB 설계해줘" / "<업무명> 스키마 만들어줘" / "엔티티 정의해줘" / "도메인 모델 설계해줘"
- 사용자가 `/karpathy-rdb` 명령으로 명시 호출
- `wiki/_schema.md`가 존재하는 프로젝트에서 RDB 관련 질문

## 워크플로우
3개 슬래시 커맨드:
1. `/karpathy-rdb init <도메인명> [--preset <key>]` — wiki 골격 설치
2. `/karpathy-rdb ingest [<프롬프트>|--file <path>]` — 요구사항을 wiki로 변환
3. `/karpathy-rdb compile` — wiki → `_blueprint.yaml` + 검증

## 참조 문서 (이 디렉터리)
- `protocols/01-init.md` — init 프로토콜 (Phase 1~6)
- `protocols/02-ingest.md` — ingest 프로토콜
- `protocols/03-compile.md` — compile 프로토콜 + V001~V010
- `references/frontmatter-schema.md` — entity/concept/domain frontmatter 스키마
- `references/blueprint-spec.md` — `_blueprint.yaml` 명세 (2단계 계약)
- `wiki-template/` — init이 복사할 wiki 골격
- `presets/` — 도메인 프리셋 (고객관리/주문관리/재고관리/인사관리/재무관리)

## 핵심 원칙
1. **Wiki-first**: markdown이 진실의 근원, `_blueprint.yaml`은 항상 생성 산출물
2. **사람 큐레이션, LLM 유지보수**: 사용자는 wiki만 본다. yaml은 자동 생성.
3. **No vector DB, No RAG**: frontmatter + 컨텍스트 윈도우로 충분
4. **2단계 계약 안정성**: `_blueprint.yaml`의 `version` 필드로 호환성 관리

## 파이프라인 위치
business-fullstack-creater의 4단계 파이프라인:
1. **Plan (본 스킬)** — 요구사항 → wiki → `_blueprint.yaml`
2. Backend — `_blueprint.yaml` → DDL
3. Middle — `/nexacro-fullstack-starter`
4. Frontend — `/nexacro-claude-skills`
```

- [ ] **Step 2: Commit**

```powershell
git add .claude/skills/karpathy-rdb/SKILL.md
git commit -m "feat(skill): add SKILL.md with auto-trigger description"
```

### 🚩 Milestone M5 Gate
- 3개 슬래시 커맨드 + SKILL.md 작성
- 각 command가 protocol을 referencing
- SKILL description이 자동 발동에 적합한 키워드 포함

---

# Phase F — 도메인 프리셋 (M6)

## Task 17: 5개 도메인 프리셋 시드

**Files:**
- Create: `.claude\skills\karpathy-rdb\presets\README.md`
- Create: `.claude\skills\karpathy-rdb\presets\고객관리.seed.md`
- Create: `.claude\skills\karpathy-rdb\presets\주문관리.seed.md`
- Create: `.claude\skills\karpathy-rdb\presets\재고관리.seed.md`
- Create: `.claude\skills\karpathy-rdb\presets\인사관리.seed.md`
- Create: `.claude\skills\karpathy-rdb\presets\재무관리.seed.md`

- [ ] **Step 1: presets/README.md 작성**

Create `.claude\skills\karpathy-rdb\presets\README.md`:

```markdown
# 도메인 프리셋

각 `.seed.md` 파일은 그 도메인의 시드 entity·concept·rule을 담은 단일 markdown.
`/karpathy-rdb init`이 `--preset <도메인>` 플래그를 받으면 본 파일의 내용을 사용자 wiki에 적용한다.

## 형식
```yaml
---
preset: <도메인 한국어명>
version: 1
---

# <도메인>

## entities (시드)
<entity 정의 (entity profile.md frontmatter 발췌)>

## concepts (시드 관계)
<concept 정의>

## rules (시드 비즈니스 규칙)
<RULE>
```

## 새 프리셋 추가
1. 본 디렉터리에 `<도메인명>.seed.md` 추가
2. 위 형식 준수
3. README의 카탈로그에 등재
```

- [ ] **Step 2: 고객관리.seed.md 작성**

Create `.claude\skills\karpathy-rdb\presets\고객관리.seed.md`:

```markdown
---
preset: 고객관리
version: 1
---

# 고객관리

## entities (시드)

### customer
```yaml
type: entity
name: customer
display: 고객
domain: [고객관리]
table: customer
status: draft
columns:
  - { name: id,         type: bigserial,    pk: true,  null: false }
  - { name: name,       type: varchar(100), null: false }
  - { name: email,      type: varchar(255), null: false, unique: true }
  - { name: phone,      type: varchar(30),  null: true }
  - { name: created_at, type: timestamptz,  null: false, default: now() }
  - { name: updated_at, type: timestamptz,  null: false, default: now() }
indexes:
  - { name: ix_customer_email, columns: [email], unique: true }
relations:
  - { kind: has_many, to: address, fk: customer_id, concept: "[[customer-has-many-addresses]]" }
```

### address
```yaml
type: entity
name: address
display: 주소
domain: [고객관리]
table: address
status: draft
columns:
  - { name: id,          type: bigserial,    pk: true,  null: false }
  - { name: customer_id, type: bigint,       null: false }
  - { name: line1,       type: varchar(255), null: false }
  - { name: line2,       type: varchar(255), null: true }
  - { name: city,        type: varchar(100), null: false }
  - { name: zipcode,     type: varchar(20),  null: false }
  - { name: is_default,  type: boolean,      null: false, default: false }
indexes:
  - { name: ix_address_customer, columns: [customer_id] }
```

### contact_log
```yaml
type: entity
name: contact_log
display: 접점기록
domain: [고객관리]
table: contact_log
status: draft
columns:
  - { name: id,          type: bigserial,    pk: true,  null: false }
  - { name: customer_id, type: bigint,       null: false }
  - { name: channel,     type: varchar(30),  null: false }
  - { name: note,        type: text,         null: true }
  - { name: contacted_at, type: timestamptz, null: false, default: now() }
indexes:
  - { name: ix_contact_log_customer, columns: [customer_id] }
```

## concepts (시드 관계)

### customer-has-many-addresses
```yaml
type: concept
kind: relation
name: customer-has-many-addresses
cardinality: 1:N
from: customer
to: address
fk_column: customer_id
on_delete: cascade
status: draft
```

### customer-has-many-contact-logs
```yaml
type: concept
kind: relation
name: customer-has-many-contact-logs
cardinality: 1:N
from: customer
to: contact_log
fk_column: customer_id
on_delete: cascade
status: draft
```

## rules (시드 비즈니스 규칙)
- 이메일은 시스템 내 유일 (unique 제약)
- 한 고객은 0개 이상의 주소를 가진다. 기본 주소는 최대 1개 (is_default).
- 고객 삭제 시 주소·접점기록도 삭제 (cascade)
```

- [ ] **Step 3: 주문관리.seed.md 작성**

Create `.claude\skills\karpathy-rdb\presets\주문관리.seed.md`:

```markdown
---
preset: 주문관리
version: 1
---

# 주문관리

## entities (시드)

### sales_order
```yaml
type: entity
name: sales_order                     # 'order'는 SQL 예약어 회피
display: 주문
domain: [주문관리]
table: sales_order
status: draft
columns:
  - { name: id,           type: bigserial,    pk: true,  null: false }
  - { name: customer_id,  type: bigint,       null: false }
  - { name: ordered_at,   type: timestamptz,  null: false, default: now() }
  - { name: total_amount, type: numeric(12,2), null: false, default: 0 }
  - { name: status,       type: varchar(20),  null: false, default: 'pending' }
indexes:
  - { name: ix_sales_order_customer, columns: [customer_id] }
  - { name: ix_sales_order_status, columns: [status] }
```

### order_item
```yaml
type: entity
name: order_item
display: 주문상품
domain: [주문관리]
table: order_item
status: draft
columns:
  - { name: id,             type: bigserial,    pk: true,  null: false }
  - { name: sales_order_id, type: bigint,       null: false }
  - { name: product_id,     type: bigint,       null: false }
  - { name: quantity,       type: int,          null: false, default: 1 }
  - { name: unit_price,     type: numeric(12,2), null: false }
indexes:
  - { name: ix_order_item_order, columns: [sales_order_id] }
```

### payment
```yaml
type: entity
name: payment
display: 결제
domain: [주문관리]
table: payment
status: draft
columns:
  - { name: id,             type: bigserial,    pk: true,  null: false }
  - { name: sales_order_id, type: bigint,       null: false, unique: true }
  - { name: method,         type: varchar(30),  null: false }
  - { name: amount,         type: numeric(12,2), null: false }
  - { name: paid_at,        type: timestamptz,  null: true }
```

## concepts (시드 관계)

### sales-order-has-many-items
```yaml
type: concept
kind: relation
name: sales-order-has-many-items
cardinality: 1:N
from: sales_order
to: order_item
fk_column: sales_order_id
on_delete: cascade
status: draft
```

### sales-order-has-one-payment
```yaml
type: concept
kind: relation
name: sales-order-has-one-payment
cardinality: 1:1
from: sales_order
to: payment
fk_column: sales_order_id
on_delete: restrict
status: draft
```

## rules (시드 비즈니스 규칙)
- 1 주문 = 1 결제 (1:1)
- 주문 상품 수량은 1 이상
- 주문 상태는 enum: `pending|confirmed|shipped|delivered|cancelled`
```

- [ ] **Step 4: 재고관리.seed.md 작성**

Create `.claude\skills\karpathy-rdb\presets\재고관리.seed.md`:

```markdown
---
preset: 재고관리
version: 1
---

# 재고관리

## entities (시드)

### product
```yaml
type: entity
name: product
display: 상품
domain: [재고관리]
table: product
status: draft
columns:
  - { name: id,         type: bigserial,    pk: true,  null: false }
  - { name: code,       type: varchar(50),  null: false, unique: true }
  - { name: name,       type: varchar(255), null: false }
  - { name: category,   type: varchar(100), null: true }
  - { name: created_at, type: timestamptz,  null: false, default: now() }
indexes:
  - { name: ix_product_code, columns: [code], unique: true }
```

### sku
```yaml
type: entity
name: sku
display: SKU
domain: [재고관리]
table: sku
status: draft
columns:
  - { name: id,         type: bigserial,    pk: true,  null: false }
  - { name: product_id, type: bigint,       null: false }
  - { name: variant,    type: varchar(100), null: true }
  - { name: barcode,    type: varchar(50),  null: true, unique: true }
indexes:
  - { name: ix_sku_product, columns: [product_id] }
```

### warehouse
```yaml
type: entity
name: warehouse
display: 창고
domain: [재고관리]
table: warehouse
status: draft
columns:
  - { name: id,       type: bigserial,    pk: true,  null: false }
  - { name: code,     type: varchar(20),  null: false, unique: true }
  - { name: name,     type: varchar(100), null: false }
  - { name: location, type: varchar(255), null: true }
```

### stock
```yaml
type: entity
name: stock
display: 재고
domain: [재고관리]
table: stock
status: draft
columns:
  - { name: id,           type: bigserial,    pk: true,  null: false }
  - { name: sku_id,       type: bigint,       null: false }
  - { name: warehouse_id, type: bigint,       null: false }
  - { name: quantity,     type: int,          null: false, default: 0 }
  - { name: updated_at,   type: timestamptz,  null: false, default: now() }
indexes:
  - { name: ux_stock_sku_warehouse, columns: [sku_id, warehouse_id], unique: true }
```

## concepts (시드 관계)

### product-has-many-skus
```yaml
type: concept
kind: relation
name: product-has-many-skus
cardinality: 1:N
from: product
to: sku
fk_column: product_id
on_delete: restrict
status: draft
```

### sku-stock-per-warehouse
```yaml
type: concept
kind: relation
name: sku-stock-per-warehouse
cardinality: N:M
from: sku
to: warehouse
fk_column: null
on_delete: restrict
status: draft
```

## rules (시드 비즈니스 규칙)
- product.code, sku.barcode, warehouse.code 모두 시스템 내 유일
- (sku_id, warehouse_id) 조합은 stock에서 유일 (1 SKU + 1 창고 = 1 재고 행)
- 재고 수량은 음수 불가 — CHECK constraint 권장
```

- [ ] **Step 5: 인사관리.seed.md 작성**

Create `.claude\skills\karpathy-rdb\presets\인사관리.seed.md`:

```markdown
---
preset: 인사관리
version: 1
---

# 인사관리

## entities (시드)

### employee
```yaml
type: entity
name: employee
display: 직원
domain: [인사관리]
table: employee
status: draft
columns:
  - { name: id,            type: bigserial,    pk: true,  null: false }
  - { name: employee_no,   type: varchar(20),  null: false, unique: true }
  - { name: name,          type: varchar(100), null: false }
  - { name: email,         type: varchar(255), null: false, unique: true }
  - { name: department_id, type: bigint,       null: true }
  - { name: position_id,   type: bigint,       null: true }
  - { name: hired_at,      type: date,         null: false }
  - { name: terminated_at, type: date,         null: true }
indexes:
  - { name: ix_employee_dept, columns: [department_id] }
```

### department
```yaml
type: entity
name: department
display: 부서
domain: [인사관리]
table: department
status: draft
columns:
  - { name: id,        type: bigserial,    pk: true,  null: false }
  - { name: code,      type: varchar(20),  null: false, unique: true }
  - { name: name,      type: varchar(100), null: false }
  - { name: parent_id, type: bigint,       null: true }   # 자기참조 (조직도)
```

### position
```yaml
type: entity
name: position
display: 직위
domain: [인사관리]
table: position
status: draft
columns:
  - { name: id,    type: bigserial,    pk: true,  null: false }
  - { name: code,  type: varchar(20),  null: false, unique: true }
  - { name: name,  type: varchar(100), null: false }
  - { name: level, type: int,          null: false }
```

## concepts (시드 관계)

### employee-belongs-to-department
```yaml
type: concept
kind: relation
name: employee-belongs-to-department
cardinality: 1:N
from: department
to: employee
fk_column: department_id
on_delete: set_null
status: draft
```

### employee-has-position
```yaml
type: concept
kind: relation
name: employee-has-position
cardinality: 1:N
from: position
to: employee
fk_column: position_id
on_delete: set_null
status: draft
```

### department-self-hierarchy
```yaml
type: concept
kind: relation
name: department-self-hierarchy
cardinality: self
from: department
to: department
fk_column: parent_id
on_delete: set_null
status: draft
```

## rules (시드 비즈니스 규칙)
- employee_no는 시스템 내 유일
- 부서 계층은 자기참조 (parent_id), 순환 금지
- 퇴사자(`terminated_at` is not null)는 신규 배치 대상에서 제외
```

- [ ] **Step 6: 재무관리.seed.md 작성**

Create `.claude\skills\karpathy-rdb\presets\재무관리.seed.md`:

```markdown
---
preset: 재무관리
version: 1
---

# 재무관리

## entities (시드)

### account
```yaml
type: entity
name: account
display: 계정과목
domain: [재무관리]
table: account
status: draft
columns:
  - { name: id,         type: bigserial,    pk: true,  null: false }
  - { name: code,       type: varchar(20),  null: false, unique: true }
  - { name: name,       type: varchar(100), null: false }
  - { name: type,       type: varchar(20),  null: false }    # asset|liability|equity|revenue|expense
  - { name: parent_id,  type: bigint,       null: true }
indexes:
  - { name: ix_account_code, columns: [code], unique: true }
```

### fiscal_period
```yaml
type: entity
name: fiscal_period
display: 회계기간
domain: [재무관리]
table: fiscal_period
status: draft
columns:
  - { name: id,         type: bigserial, pk: true,  null: false }
  - { name: year,       type: int,       null: false }
  - { name: month,      type: int,       null: false }
  - { name: closed_at,  type: timestamptz, null: true }
indexes:
  - { name: ux_fiscal_period_ym, columns: [year, month], unique: true }
```

### ledger_entry
```yaml
type: entity
name: ledger_entry
display: 분개
domain: [재무관리]
table: ledger_entry
status: draft
columns:
  - { name: id,                type: bigserial,    pk: true,  null: false }
  - { name: fiscal_period_id,  type: bigint,       null: false }
  - { name: account_id,        type: bigint,       null: false }
  - { name: debit,             type: numeric(15,2), null: false, default: 0 }
  - { name: credit,            type: numeric(15,2), null: false, default: 0 }
  - { name: description,       type: varchar(255), null: true }
  - { name: posted_at,         type: timestamptz,  null: false, default: now() }
indexes:
  - { name: ix_ledger_period, columns: [fiscal_period_id] }
  - { name: ix_ledger_account, columns: [account_id] }
```

## concepts (시드 관계)

### account-self-hierarchy
```yaml
type: concept
kind: relation
name: account-self-hierarchy
cardinality: self
from: account
to: account
fk_column: parent_id
on_delete: restrict
status: draft
```

### ledger-belongs-to-account
```yaml
type: concept
kind: relation
name: ledger-belongs-to-account
cardinality: 1:N
from: account
to: ledger_entry
fk_column: account_id
on_delete: restrict
status: draft
```

### ledger-belongs-to-period
```yaml
type: concept
kind: relation
name: ledger-belongs-to-period
cardinality: 1:N
from: fiscal_period
to: ledger_entry
fk_column: fiscal_period_id
on_delete: restrict
status: draft
```

## rules (시드 비즈니스 규칙)
- (year, month) 조합은 fiscal_period에서 유일
- 분개 1행은 debit 또는 credit 중 하나만 0이 아니어야 함 (CHECK 제약 검토)
- 마감된(closed_at is not null) period에는 ledger_entry 추가 금지
```

- [ ] **Step 7: 5개 프리셋 frontmatter 일괄 검증**

```powershell
python -c "
import yaml, pathlib
root = pathlib.Path('.claude/skills/karpathy-rdb/presets')
errors = []
for md in root.glob('*.seed.md'):
    text = md.read_text(encoding='utf-8')
    if not text.startswith('---'):
        errors.append(f'{md}: no frontmatter'); continue
    fm = text.split('---', 2)[1]
    d = yaml.safe_load(fm)
    if d.get('preset') is None:
        errors.append(f'{md}: missing preset field')
print('ERRORS:' if errors else 'ALL 5 OK')
for e in errors: print(' -', e)
"
```

Expected: `ALL 5 OK`.

- [ ] **Step 8: Commit**

```powershell
git add .claude/skills/karpathy-rdb/presets/
git commit -m "feat(presets): add 5 domain seeds (고객/주문/재고/인사/재무관리)"
```

### 🚩 Milestone M6 Gate
- 5개 도메인 프리셋 + presets/README.md 작성
- 각 프리셋 frontmatter 파싱 성공
- 각 프리셋이 entities/concepts/rules 3개 섹션 모두 포함

---

# Phase G — 사용자 가이드 (M7)

## Task 18: README.ko.md (한국어 기본)

**Files:**
- Create: `README.ko.md`

- [ ] **Step 1: README.ko.md 작성**

Create `D:\AI\workspace\andrej-karpathy-rdb-skill\README.ko.md`:

```markdown
# andrej-karpathy-rdb-skill

> Andrej Karpathy의 LLM Wiki 패턴을 관계형 DB 스키마 설계에 이식한 Claude Code 플러그인. 한국어 기본.

## 무엇인가
markdown + frontmatter로 비즈니스 도메인·엔티티·관계를 정의하고, 한 번의 컴파일로 `_blueprint.yaml` manifest를 산출. 2단계 DDL 생성 플러그인이 manifest를 입력으로 받아 PostgreSQL DDL을 생성한다.

**핵심 철학**:
- ✅ markdown + YAML frontmatter (no vector DB, no RAG)
- ✅ 사람은 wiki만 큐레이션, LLM이 컴파일·검증
- ✅ Wiki-first: markdown이 진실의 근원
- ✅ 한국어 기본, 식별자는 영문

## 설치
```
/plugin install andrej-karpathy-rdb-skill@<marketplace>
```

또는 git clone 후 marketplace에 등록.

## 빠른 시작
```
# 1. wiki 골격 설치 + 고객관리 프리셋 적용
/karpathy-rdb init 고객관리 --preset 고객관리

# 2. 요구사항 ingest (자유 프롬프트)
/karpathy-rdb ingest 고객은 이름과 이메일을 가지며, 이메일은 유일하다.
                     주소는 여러 개 등록할 수 있고 기본 주소를 1개 지정한다.

# 3. 컴파일 (wiki → _blueprint.yaml + 정합성 검증)
/karpathy-rdb compile

# 4. _blueprint.yaml을 2단계 DDL 생성 플러그인에 전달
```

## 슬래시 커맨드

| 커맨드 | 기능 |
| :-- | :-- |
| `/karpathy-rdb init <도메인> [--preset <key>]` | wiki 골격 + 프리셋 설치 |
| `/karpathy-rdb ingest [<프롬프트>\|--file <path>]` | 요구사항 → wiki 페이지 |
| `/karpathy-rdb compile` | wiki → `_blueprint.yaml` |

## 도메인 프리셋 카탈로그

| 프리셋 | 시드 entities | 시드 concepts |
| :-- | :-- | :-- |
| 고객관리 | customer, address, contact_log | customer↔address(1:N), customer↔contact_log(1:N) |
| 주문관리 | sales_order, order_item, payment | sales_order↔order_item(1:N), sales_order↔payment(1:1) |
| 재고관리 | product, sku, warehouse, stock | product↔sku(1:N), sku↔warehouse(N:M via stock) |
| 인사관리 | employee, department, position | dept↔employee(1:N), position↔employee(1:N), dept↔dept(self) |
| 재무관리 | account, fiscal_period, ledger_entry | account↔account(self), account↔ledger(1:N), period↔ledger(1:N) |

새 프리셋 추가는 `.claude/skills/karpathy-rdb/presets/README.md` 참조.

## wiki 디렉터리 구조 (설치 후)
```
wiki/
├── _schema.md / _protocols.md / _log.md
├── _blueprint.yaml          ← compile 산출물
├── compile-report.md        ← 검증 보고서
├── raw/                     ← 원본 요구사항
├── sources/                 ← LLM 압축 요약
├── domains/                 ← 비즈니스 도메인
├── entities/                ← DB 테이블 정의
├── concepts/                ← ER 관계·비즈니스 규칙
├── decisions/, explorations/, comparisons/
└── rules.md / false-beliefs.md
```

## frontmatter 표준
- Entity: `entities/<name>/profile.md` — PK/FK/columns/indexes/constraints/relations
- Concept: `concepts/<name>.md` — relation/rule/invariant/terminology
- Domain: `domains/<name>/profile.md` — 소속 entities/concepts

자세한 스키마는 `.claude/skills/karpathy-rdb/references/frontmatter-schema.md`.

## `_blueprint.yaml` 스키마 (2단계 핸드오프)
`.claude/skills/karpathy-rdb/references/blueprint-spec.md` 참조.

## 검증 코드 V001~V010

| 코드 | 레벨 | 검증 |
| :-: | :-: | :-- |
| V001 | ERROR | 모든 entity는 PK 컬럼 1개 이상 |
| V002 | ERROR | FK가 참조 PK/UQ 컬럼을 가리킴 |
| V003 | WARN | 컬럼명 snake_case + 예약어 회피 |
| V004 | WARN | FK 컬럼 타입이 참조 PK 타입과 동일 |
| V005 | WARN | 순환 의존 검출 (DAG) |
| V006 | WARN | concept이 참조하는 entity 미존재 |
| V007 | WARN | entity가 어느 domain에도 속하지 않음 |
| V008 | INFO | rules.md ↔ entity·concept 매핑 보고 |
| V009 | INFO | entity sources 누락 |
| V010 | INFO | locked entity는 decisions 1개 이상 권장 |

## 파이프라인 위치
business-fullstack-creater의 4단계 중 **1단계 (Plan)** 담당.

| 단계 | 산출물 | 도구 |
| :-: | :-- | :-- |
| 1 Plan | `_blueprint.yaml` | 본 플러그인 |
| 2 Backend | DDL + 마이그레이션 | 별도 플러그인 |
| 3 Middle | Spring Boot war | `/nexacro-fullstack-starter` |
| 4 Frontend | Nexacro project | `/nexacro-claude-skills` |

## 영감
- [Andrej Karpathy LLM Wiki pattern](https://x.com/karpathy/status/2039805659525644595)
- [Benboerba620/karpathy-claude-wiki](https://github.com/Benboerba620/karpathy-claude-wiki) — 원본 구현 참조
```

- [ ] **Step 2: Commit**

```powershell
git add README.ko.md
git commit -m "docs: add Korean README (default user guide)"
```

---

## Task 19: README.md (English)

**Files:**
- Create: `README.md`

- [ ] **Step 1: README.md 작성**

Create `D:\AI\workspace\andrej-karpathy-rdb-skill\README.md`:

```markdown
# andrej-karpathy-rdb-skill

> Claude Code plugin that ports Andrej Karpathy's LLM Wiki pattern to relational database schema design. Korean-first.

For Korean documentation, see [README.ko.md](README.ko.md) (default).

## What is this
Define business domains, entities, and relations in markdown + YAML frontmatter. A single `compile` step produces a `_blueprint.yaml` manifest consumed by a downstream DDL-generation plugin to emit PostgreSQL DDL.

**Core philosophy**:
- ✅ markdown + YAML frontmatter (no vector DB, no RAG)
- ✅ Human curates the wiki; LLM compiles and validates
- ✅ Wiki-first: markdown is the source of truth
- ✅ Korean prompts by default, identifiers in English

## Install
```
/plugin install andrej-karpathy-rdb-skill@<marketplace>
```

## Quick Start
```
/karpathy-rdb init customer-management --preset 고객관리
/karpathy-rdb ingest A customer has a unique email and can register many addresses.
/karpathy-rdb compile
```

## Commands
| Command | Purpose |
| :-- | :-- |
| `/karpathy-rdb init <domain> [--preset <key>]` | Scaffold wiki + apply preset |
| `/karpathy-rdb ingest [<prompt>\|--file <path>]` | Ingest requirements into wiki |
| `/karpathy-rdb compile` | wiki → `_blueprint.yaml` + validation |

## Domain Presets

| Preset (Korean) | Seed entities | Seed concepts |
| :-- | :-- | :-- |
| 고객관리 (Customer) | customer, address, contact_log | 1:N |
| 주문관리 (Order) | sales_order, order_item, payment | 1:N, 1:1 |
| 재고관리 (Inventory) | product, sku, warehouse, stock | 1:N, N:M |
| 인사관리 (HR) | employee, department, position | 1:N, self |
| 재무관리 (Finance) | account, fiscal_period, ledger_entry | 1:N, self |

## Validation Codes
See [README.ko.md](README.ko.md) for full V001~V010 table.

## Pipeline Position
Stage 1 (Plan) of the `business-fullstack-creater` 4-stage pipeline:
1. **Plan (this plugin)** — requirements → wiki → `_blueprint.yaml`
2. Backend — DDL generation
3. Middle — Spring Boot (`/nexacro-fullstack-starter`)
4. Frontend — Nexacro (`/nexacro-claude-skills`)

## Inspiration
- [Karpathy LLM Wiki pattern](https://x.com/karpathy/status/2039805659525644595)
- [Benboerba620/karpathy-claude-wiki](https://github.com/Benboerba620/karpathy-claude-wiki) — reference implementation
```

- [ ] **Step 2: Commit**

```powershell
git add README.md
git commit -m "docs: add English README"
```

---

## Task 20: INSTALL-FOR-AI.md (AI agent 설치 프로토콜)

**Files:**
- Create: `INSTALL-FOR-AI.md`

- [ ] **Step 1: INSTALL-FOR-AI.md 작성**

Create `D:\AI\workspace\andrej-karpathy-rdb-skill\INSTALL-FOR-AI.md`:

```markdown
# INSTALL-FOR-AI.md — Auto-install protocol

> **Audience**: AI agents (Claude Code, Cursor, Cline, etc.). If a human user pastes this file's URL and says "install this for me", follow the steps below in order.

## Phase 1 — Clarify (한 번에 한 질문)
1. **wiki 디렉터리 위치?** 기본: `./wiki/`. 이미 존재하면 abort.
2. **첫 비즈니스 도메인?** 자유 입력 (예: 고객관리)
3. **도메인 프리셋 적용?** 옵션: 고객관리/주문관리/재고관리/인사관리/재무관리/없음
4. **프로젝트 루트에 `CLAUDE.md` 있나?** yes/no
5. **시작 entity 이름 1개?** snake_case 영문 (예: customer)

## Phase 2 — Plugin 설치 확인
```bash
# /plugin install 명령으로 설치된 경우 skip.
# 수동 설치 시:
git clone https://github.com/<owner>/andrej-karpathy-rdb-skill.git .karpathy-rdb-tmp
# Claude Code 플러그인 디렉터리에 복사
```

## Phase 3 — Wiki Scaffold
`.claude/skills/karpathy-rdb/wiki-template/` 전체를 사용자의 `<wiki 디렉터리 위치>`로 복사.

## Phase 4 — 도메인 커스터마이즈
1. `wiki/domains/_template/`를 `wiki/domains/<도메인>/`로 복사·rename
2. frontmatter의 `name`, `display`를 도메인명으로 치환
3. 선택한 preset이 있으면 `.claude/skills/karpathy-rdb/presets/<도메인>.seed.md`의 entities/concepts/rules를 wiki에 적용

## Phase 5 — `CLAUDE.md` 통합
프로젝트 루트의 `CLAUDE.md`에 다음 섹션 추가 (없으면 신규 생성):
```
## RDB Wiki
- 모든 ingest/compile 전 `wiki/_schema.md`, `wiki/_protocols.md`를 읽는다.
- 새 entity 추가 시 관련 domain·concept을 갱신한다.
```

## Phase 6 — 첫 Entity Scaffold
1. `wiki/entities/<첫entity>/profile.md` 생성 (template에서 복사)
2. frontmatter의 `name`, `display`, `table` 채움
3. 본문은 비워둠 — 내용 추측 금지

## Phase 7 — Verify + Hand-off
1. `python <plugin_path>/scripts/rdb_index.py --lint <wiki_path>` 실행
2. 에러 0개 확인
3. `.karpathy-rdb-tmp/` 삭제
4. 사용자에게 안내:
   > "wiki/ 설치 완료. 다음: `/karpathy-rdb ingest`로 요구사항을 추가하세요."

## 절대 하지 말 것
- 사용자가 명시하지 않은 entity content 생성
- silent overwrite
- locale을 사용자 동의 없이 변경
```

- [ ] **Step 2: Commit**

```powershell
git add INSTALL-FOR-AI.md
git commit -m "docs: add INSTALL-FOR-AI auto-install protocol"
```

### 🚩 Milestone M7 Gate
- README.ko.md / README.md / INSTALL-FOR-AI.md 3개 사용자 가이드 완성
- 모든 가이드가 동일한 골든 패스 시나리오를 다룸

---

# Phase H — CLI + 통합 검증 (M8)

## Task 21: `scripts/rdb_index.py` (TDD)

**Files:**
- Create: `tests\conftest.py`
- Create: `tests\test_frontmatter.py`
- Create: `tests\test_validators.py`
- Create: `scripts\rdb_index.py`

- [ ] **Step 1: 디렉터리 생성 + Python venv**

```powershell
New-Item -ItemType Directory -Path "scripts", "tests", "tests\fixtures" -Force
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install pyyaml pytest
```

- [ ] **Step 2: 실패하는 테스트 1 — frontmatter 파서**

Create `tests\conftest.py`:

```python
import sys
import pathlib

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
```

Create `tests\test_frontmatter.py`:

```python
import pytest
from rdb_index import parse_frontmatter


def test_parse_frontmatter_returns_dict_and_body():
    text = """---
type: entity
name: customer
columns:
  - { name: id, pk: true }
---

# customer body
"""
    fm, body = parse_frontmatter(text)
    assert fm["type"] == "entity"
    assert fm["name"] == "customer"
    assert fm["columns"][0]["pk"] is True
    assert "customer body" in body


def test_parse_frontmatter_missing_raises():
    with pytest.raises(ValueError, match="no frontmatter"):
        parse_frontmatter("no frontmatter here")


def test_parse_frontmatter_malformed_yaml_raises():
    text = """---
type: entity
name: : bad
---
"""
    with pytest.raises(ValueError, match="invalid yaml"):
        parse_frontmatter(text)
```

- [ ] **Step 3: 테스트 실행 — 실패 확인**

```powershell
pytest tests/test_frontmatter.py -v
```

Expected: `ImportError: cannot import name 'parse_frontmatter'` 또는 `ModuleNotFoundError`.

- [ ] **Step 4: 최소 구현 — `parse_frontmatter`**

Create `scripts\rdb_index.py`:

```python
"""rdb_index: lint + index + compile for karpathy-rdb wiki."""
from __future__ import annotations

import sys
import argparse
import pathlib
from typing import Tuple, Dict, Any

import yaml


def parse_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    """Parse YAML frontmatter from a markdown string.

    Returns (frontmatter_dict, body).
    Raises ValueError on missing or malformed frontmatter.
    """
    if not text.startswith("---"):
        raise ValueError("no frontmatter")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError("no frontmatter (missing closing ---)")
    fm_text, body = parts[1], parts[2]
    try:
        fm = yaml.safe_load(fm_text)
    except yaml.YAMLError as e:
        raise ValueError(f"invalid yaml: {e}") from e
    if not isinstance(fm, dict):
        raise ValueError("invalid yaml: frontmatter must be a mapping")
    return fm, body.lstrip("\n")


def main() -> int:
    parser = argparse.ArgumentParser(prog="rdb_index")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("lint").add_argument("wiki_dir")
    sub.add_parser("compile").add_argument("wiki_dir")
    args = parser.parse_args()
    print(f"[stub] {args.cmd} on {args.wiki_dir}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: 테스트 실행 — 통과 확인**

```powershell
pytest tests/test_frontmatter.py -v
```

Expected: 3 passed.

- [ ] **Step 6: V001 검증기 실패 테스트**

Create `tests\test_validators.py`:

```python
import pytest
from rdb_index import validate_v001_pk_exists


def test_v001_passes_when_entity_has_pk():
    entity = {
        "type": "entity",
        "name": "customer",
        "columns": [
            {"name": "id", "pk": True},
            {"name": "name"},
        ],
    }
    errors = validate_v001_pk_exists(entity)
    assert errors == []


def test_v001_fails_when_no_pk_column():
    entity = {
        "type": "entity",
        "name": "broken",
        "columns": [
            {"name": "id"},
            {"name": "name"},
        ],
    }
    errors = validate_v001_pk_exists(entity)
    assert len(errors) == 1
    assert errors[0]["code"] == "V001"
    assert "broken" in errors[0]["target"]


def test_v001_fails_when_columns_empty():
    entity = {"type": "entity", "name": "empty", "columns": []}
    errors = validate_v001_pk_exists(entity)
    assert len(errors) == 1
    assert errors[0]["code"] == "V001"
```

- [ ] **Step 7: 테스트 실행 — V001 실패 확인**

```powershell
pytest tests/test_validators.py -v
```

Expected: `ImportError: cannot import name 'validate_v001_pk_exists'`.

- [ ] **Step 8: V001 구현**

Append to `scripts\rdb_index.py` (Add before `def main()`):

```python
def validate_v001_pk_exists(entity: Dict[str, Any]) -> list[dict]:
    """V001: every entity must have at least one column with pk: true."""
    name = entity.get("name", "<unknown>")
    columns = entity.get("columns") or []
    has_pk = any(col.get("pk") is True for col in columns)
    if has_pk:
        return []
    return [{
        "code": "V001",
        "level": "ERROR",
        "target": f"entity:{name}",
        "message": "PK 컬럼 없음 — `columns[].pk: true`인 컬럼 1개 이상 필요",
    }]
```

- [ ] **Step 9: V001 테스트 통과**

```powershell
pytest tests/test_validators.py -v
```

Expected: 3 passed.

- [ ] **Step 10: V002 실패 테스트**

Append to `tests\test_validators.py`:

```python
from rdb_index import validate_v002_fk_targets


def test_v002_passes_when_fk_targets_pk():
    entities = {
        "customer": {"name": "customer", "columns": [{"name": "id", "pk": True}]},
        "address": {"name": "address", "columns": [{"name": "id", "pk": True}, {"name": "customer_id"}]},
    }
    relation = {"from": "customer", "to": "address", "fk_column": "customer_id"}
    errors = validate_v002_fk_targets(relation, entities)
    assert errors == []


def test_v002_fails_when_fk_target_missing():
    entities = {
        "customer": {"name": "customer", "columns": [{"name": "id", "pk": True}]},
    }
    relation = {"from": "customer", "to": "ghost", "fk_column": "customer_id"}
    errors = validate_v002_fk_targets(relation, entities)
    assert len(errors) == 1
    assert errors[0]["code"] == "V002"
```

- [ ] **Step 11: 테스트 실행 — V002 실패 확인**

```powershell
pytest tests/test_validators.py -v
```

Expected: 2 new tests fail with import error.

- [ ] **Step 12: V002 구현**

Append to `scripts\rdb_index.py`:

```python
def validate_v002_fk_targets(relation: Dict[str, Any], entities: Dict[str, Dict]) -> list[dict]:
    """V002: relation.fk_column must reference an existing PK or UQ column on `to` entity."""
    to_name = relation.get("to")
    fk_col = relation.get("fk_column")
    if to_name not in entities:
        return [{
            "code": "V002",
            "level": "ERROR",
            "target": f"relation:{relation.get('from')}->{to_name}",
            "message": f"참조 entity 미존재: {to_name}",
        }]
    target_entity = entities[to_name]
    cols = target_entity.get("columns") or []
    # FK column should reference the target entity's PK (typical case)
    has_target_pk = any(c.get("pk") is True for c in cols)
    if not has_target_pk:
        return [{
            "code": "V002",
            "level": "ERROR",
            "target": f"relation:{relation.get('from')}->{to_name}",
            "message": f"참조 entity {to_name}에 PK 없음",
        }]
    return []
```

- [ ] **Step 13: V002 테스트 통과**

```powershell
pytest tests/test_validators.py -v
```

Expected: 5 passed (3 V001 + 2 V002).

- [ ] **Step 14: V003 (snake_case + 예약어) 테스트 + 구현**

Append to `tests\test_validators.py`:

```python
from rdb_index import validate_v003_naming


def test_v003_passes_for_snake_case():
    entity = {"name": "customer", "columns": [{"name": "customer_id"}, {"name": "email_address"}]}
    assert validate_v003_naming(entity) == []


def test_v003_warns_on_camelcase():
    entity = {"name": "customer", "columns": [{"name": "customerId"}]}
    warnings = validate_v003_naming(entity)
    assert len(warnings) == 1
    assert warnings[0]["code"] == "V003"


def test_v003_warns_on_reserved_word():
    entity = {"name": "customer", "columns": [{"name": "user"}]}
    warnings = validate_v003_naming(entity)
    assert any(w["code"] == "V003" for w in warnings)
```

Append to `scripts\rdb_index.py`:

```python
RESERVED_WORDS = frozenset([
    "user", "order", "group", "table", "schema", "type", "role", "name",
    "value", "key", "primary", "foreign", "references", "default", "check",
    "unique", "index", "constraint", "select", "insert", "update", "delete",
    "from", "where", "join", "having", "by", "on", "as", "in", "is", "not",
    "null", "true", "false",
])


def validate_v003_naming(entity: Dict[str, Any]) -> list[dict]:
    """V003: column names must be snake_case and avoid PostgreSQL reserved words."""
    import re
    warnings = []
    name = entity.get("name", "<unknown>")
    for col in entity.get("columns") or []:
        col_name = col.get("name", "")
        if not re.fullmatch(r"[a-z_][a-z0-9_]*", col_name):
            warnings.append({
                "code": "V003",
                "level": "WARN",
                "target": f"entity:{name}:column:{col_name}",
                "message": f"snake_case 위반: {col_name}",
            })
        if col_name.lower() in RESERVED_WORDS:
            warnings.append({
                "code": "V003",
                "level": "WARN",
                "target": f"entity:{name}:column:{col_name}",
                "message": f"PostgreSQL 예약어: {col_name}",
            })
    return warnings
```

Run:
```powershell
pytest tests/test_validators.py -v
```

Expected: 8 passed.

- [ ] **Step 15: lint 명령 통합 (`rdb_index.py lint <wiki>`)**

Replace `main()` in `scripts\rdb_index.py`:

```python
def lint_wiki(wiki_dir: pathlib.Path) -> int:
    """Run all validators on a wiki directory. Returns ERROR count."""
    entities = {}
    relations = []
    errors_total = []
    for md in wiki_dir.glob("entities/*/profile.md"):
        try:
            fm, _ = parse_frontmatter(md.read_text(encoding="utf-8"))
        except ValueError as e:
            errors_total.append({"code": "PARSE", "level": "ERROR", "target": str(md), "message": str(e)})
            continue
        name = fm.get("name")
        if not name:
            errors_total.append({"code": "PARSE", "level": "ERROR", "target": str(md), "message": "entity missing 'name'"})
            continue
        entities[name] = fm
        errors_total.extend(validate_v001_pk_exists(fm))
        errors_total.extend(validate_v003_naming(fm))
        for rel in fm.get("relations") or []:
            relations.append({"from": name, "to": rel.get("to"), "fk_column": rel.get("fk")})
    for rel in relations:
        errors_total.extend(validate_v002_fk_targets(rel, entities))

    err_count = sum(1 for e in errors_total if e["level"] == "ERROR")
    warn_count = sum(1 for e in errors_total if e["level"] == "WARN")
    print(f"entities: {len(entities)}, relations: {len(relations)}")
    print(f"ERROR: {err_count}, WARN: {warn_count}")
    for e in errors_total:
        print(f"  [{e['level']}] {e['code']} {e['target']}: {e['message']}")
    return err_count


def main() -> int:
    parser = argparse.ArgumentParser(prog="rdb_index")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_lint = sub.add_parser("lint")
    p_lint.add_argument("wiki_dir", type=pathlib.Path)
    p_compile = sub.add_parser("compile")
    p_compile.add_argument("wiki_dir", type=pathlib.Path)
    args = parser.parse_args()
    if args.cmd == "lint":
        return 1 if lint_wiki(args.wiki_dir) > 0 else 0
    if args.cmd == "compile":
        # MVP: lint + (TODO write _blueprint.yaml) — covered by integration test
        return 1 if lint_wiki(args.wiki_dir) > 0 else 0
    return 0
```

- [ ] **Step 16: 전체 테스트 + 자기 wiki-template lint**

```powershell
pytest tests/ -v
python scripts/rdb_index.py lint .claude/skills/karpathy-rdb/wiki-template/
```

Expected:
- pytest: 8 passed
- lint 출력에 entities/relations 카운트, ERROR 0 (wiki-template은 `_template` 파일들이라 entity dir 아래 실제 profile.md 없음 → entities: 0이 정상)

- [ ] **Step 17: Commit**

```powershell
git add scripts/ tests/
git commit -m "feat(scripts): add rdb_index.py with V001/V002/V003 validators (TDD)"
```

---

## Task 22: 통합 테스트 — 골든 패스 fixture

**Files:**
- Create: `tests\fixtures\golden_wiki\` (사용자 wiki 시뮬레이션)
- Create: `tests\test_golden_path.py`

- [ ] **Step 1: golden fixture wiki 생성**

Create `tests\fixtures\golden_wiki\_schema.md`:

```markdown
---
type: schema
version: 1
locale: ko
project: 고객관리
---

# golden fixture
```

Create `tests\fixtures\golden_wiki\entities\customer\profile.md`:

```markdown
---
type: entity
name: customer
display: 고객
domain: [고객관리]
table: customer
status: draft
columns:
  - { name: id,    type: bigserial,    pk: true, null: false }
  - { name: email, type: varchar(255), null: false, unique: true }
indexes:
  - { name: ix_customer_email, columns: [email], unique: true }
relations:
  - { kind: has_many, to: address, fk: customer_id, concept: "[[customer-has-many-addresses]]" }
sources: []
---

# customer
```

Create `tests\fixtures\golden_wiki\entities\address\profile.md`:

```markdown
---
type: entity
name: address
display: 주소
domain: [고객관리]
table: address
status: draft
columns:
  - { name: id,          type: bigserial, pk: true, null: false }
  - { name: customer_id, type: bigint,    null: false }
---

# address
```

Create `tests\fixtures\golden_wiki\concepts\customer-has-many-addresses.md`:

```markdown
---
type: concept
kind: relation
name: customer-has-many-addresses
cardinality: 1:N
from: customer
to: address
fk_column: customer_id
on_delete: cascade
status: draft
---

# customer ↔ address
```

- [ ] **Step 2: 골든패스 테스트 작성**

Create `tests\test_golden_path.py`:

```python
import pathlib
from rdb_index import lint_wiki

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "golden_wiki"


def test_golden_wiki_lints_clean():
    err_count = lint_wiki(FIXTURE)
    assert err_count == 0


def test_golden_wiki_breaks_when_pk_removed(tmp_path, monkeypatch):
    # Copy fixture to tmp and break it
    import shutil
    target = tmp_path / "wiki"
    shutil.copytree(FIXTURE, target)
    bad = target / "entities" / "customer" / "profile.md"
    text = bad.read_text(encoding="utf-8")
    bad.write_text(text.replace("pk: true,", "pk: false,"), encoding="utf-8")
    err_count = lint_wiki(target)
    assert err_count >= 1
```

- [ ] **Step 3: 골든패스 테스트 실행**

```powershell
pytest tests/test_golden_path.py -v
```

Expected: 2 passed.

- [ ] **Step 4: 전체 테스트 + 커버리지 확인**

```powershell
pytest tests/ -v
```

Expected: 10 passed (3 frontmatter + 8 validators + 2 golden = 13 total... 정확한 합은 13)

- [ ] **Step 5: Commit**

```powershell
git add tests/fixtures/ tests/test_golden_path.py
git commit -m "test: add golden path integration (clean wiki lints clean, breaking PK fails)"
```

### 🚩 Milestone M8 Gate
- `rdb_index.py`가 V001/V002/V003 검증 통과
- 골든 wiki fixture가 ERROR 0으로 lint
- PK 제거 시 ERROR 1 검출
- 모든 테스트 통과

---

# Phase I — 부모 프로젝트 통합 (M9)

## Task 23: business-fullstack-creater의 needs 문서 갱신

**Files:**
- Modify: `D:\AI\workspace\business-fullstack-creater\needs\Plugin참조\1. Plan - andrej-karpathy-rdb-skill 구현.md`
- Modify: `D:\AI\workspace\business-fullstack-creater\needs\Plugin참조\2. Backend - DB 스키마(DDL) 생성하기.md`
- Modify: `D:\AI\workspace\business-fullstack-creater\needs\business-fullstack-creater 플러그인 요구기능.md` (상태 갱신)

- [ ] **Step 1: 1단계 needs 문서 — 완료 상태 추가**

Read `D:\AI\workspace\business-fullstack-creater\needs\Plugin참조\1. Plan - andrej-karpathy-rdb-skill 구현.md` first to confirm existing content, then append a status block at the bottom:

Append at end of `1. Plan - andrej-karpathy-rdb-skill 구현.md`:

```markdown

---

## 구현 상태 (2026-05-13 update)

- ✅ 설계 완료 — `docs/superpowers/specs/2026-05-13-andrej-karpathy-rdb-skill-design.md`
- ✅ 구현 플랜 완료 — `docs/superpowers/plans/2026-05-13-andrej-karpathy-rdb-skill.md`
- 🔜 구현 진행 — separate repo `D:\AI\workspace\andrej-karpathy-rdb-skill\`

### 결정 사항 (D1~D9)
| # | 항목 | 선택 |
| :-: | :-- | :-- |
| D1 | 산출물 | Markdown wiki + manifest 겸용 |
| D2 | UX | Slash command + Skill |
| D3 | 입력 | 하이브리드 (프롬프트 + 파일) |
| D4 | 도메인 | 프리셋(5종) + 동적 확장 |
| D5 | 패키징 | Marketplace plugin |
| D6 | 워크플로우 | 3단 (init/ingest/compile) |
| D7 | 언어 | 한국어 기본 |
| D8 | manifest | YAML (`_blueprint.yaml`) |
| D9 | 컴파일 | Wiki-first |

### 참조 레포 활용 결론
원본(`Benboerba620/karpathy-claude-wiki`)에서 차용:
- 5계층 변화율 디렉터리
- frontmatter + wikilink
- Phase 1~6 설치 프로토콜 골격
- `_schema.md`/`_protocols.md`/`_log.md` 메타파일
- 도메인 rename 패턴

신규 정의:
- entity = DB 테이블 매핑 규약
- concepts = ER 관계
- `_blueprint.yaml` 2단계 계약
- 비즈니스 도메인 5종 프리셋
```

- [ ] **Step 2: 2단계 needs 문서 — 빈 파일에 contract 작성**

Overwrite `D:\AI\workspace\business-fullstack-creater\needs\Plugin참조\2. Backend - DB 스키마(DDL) 생성하기.md`:

```markdown
# 2단계 — Backend: DB 스키마(DDL) 생성하기

## 입력 계약 (1단계 산출물)

1단계 `andrej-karpathy-rdb-skill`의 `/karpathy-rdb compile` 산출물 `wiki/_blueprint.yaml`이 본 단계의 **공식 입력**.

스키마는 `andrej-karpathy-rdb-skill/.claude/skills/karpathy-rdb/references/blueprint-spec.md` 참조.

### 최소 입력 필드
```yaml
version: 1
project: <한국어 도메인명>
entities: [...]                       # name, table, schema, columns, indexes, constraints
relations: [...]                      # from, to, cardinality, fk
business_rules: [...]
validation:
  passed: true                        # false면 본 단계 거부
```

## 본 단계의 책임

1. `_blueprint.yaml` 파싱 + `version` 검증
2. `validation.passed: false`이면 즉시 abort + 사용자에게 1단계 재컴파일 안내
3. FK 의존성으로 entity 위상정렬 → 마이그레이션 순서 결정
4. PostgreSQL DDL 생성:
   - `CREATE SCHEMA IF NOT EXISTS <schema>;`
   - `CREATE TABLE <table> (...) ;`
   - `ALTER TABLE ... ADD CONSTRAINT FK_... FOREIGN KEY ... REFERENCES ... ON DELETE ...;`
   - `CREATE INDEX ix_... ON ... (...);`
   - CHECK constraints from `business_rules.enforced_by`
5. V001~V005 재검증 (DDL 레벨 정합성)
6. 마이그레이션 파일 산출 (Flyway 또는 Liquibase 호환):
   - `V001__create_schema.sql`
   - `V002__create_tables.sql`
   - `V003__create_indexes.sql`
   - `V004__create_constraints.sql`
7. 시드 데이터 스크립트 (옵션 — 프리셋 시드 entity의 sample row)

## 산출물

```
db/
├── migrations/
│   ├── V001__create_schema.sql
│   ├── V002__create_tables.sql
│   ├── V003__create_indexes.sql
│   └── V004__create_constraints.sql
├── seed/
│   └── 01_<entity>_sample.sql        # 옵션
└── ddl-report.md                     # 정합성 재검증 결과
```

## 다음 단계
DDL을 3단계 `/nexacro-fullstack-starter`에 전달.

## TODO
- 2단계 플러그인 구현 (별도 ToDo)
```

- [ ] **Step 3: 상위 요구기능 문서 — 상태 갱신**

Read `D:\AI\workspace\business-fullstack-creater\needs\business-fullstack-creater 플러그인 요구기능.md` first, then append status block at the bottom:

Append at the end:

```markdown

---

## 진행 상태 (2026-05-13 update)

| 단계 | Plugin | 상태 |
| :-: | :-- | :-: |
| 1 | `andrej-karpathy-rdb-skill` | 🟡 설계·플랜 완료, 구현 진행 |
| 2 | DDL 생성 플러그인 | 🔜 1단계 완료 후 |
| 3 | `/nexacro-fullstack-starter` | ✅ 외부 plugin 사용 |
| 4 | `/nexacro-claude-skills` | ✅ 외부 plugin 사용 |

### 참조 문서
- 설계: `docs/superpowers/specs/2026-05-13-andrej-karpathy-rdb-skill-design.md`
- 플랜: `docs/superpowers/plans/2026-05-13-andrej-karpathy-rdb-skill.md`
- 1단계: `needs/Plugin참조/1. Plan - andrej-karpathy-rdb-skill 구현.md`
- 2단계: `needs/Plugin참조/2. Backend - DB 스키마(DDL) 생성하기.md` (입력 계약 작성됨)
```

- [ ] **Step 4: business-fullstack-creater는 git repo 아님 — git 단계 스킵**

본 working dir은 git이 아니므로 `git add/commit` 단계 없음. needs 문서가 갱신되었는지만 확인:

```powershell
Get-Content "D:\AI\workspace\business-fullstack-creater\needs\Plugin참조\2. Backend - DB 스키마(DDL) 생성하기.md" | Select-Object -First 10
```

Expected: `# 2단계 — Backend: DB 스키마(DDL) 생성하기`로 시작.

- [ ] **Step 5: plugin repo의 마지막 커밋 — 통합 마커**

```powershell
Set-Location "D:\AI\workspace\andrej-karpathy-rdb-skill"
git log --oneline | Measure-Object -Line
git tag -a v0.1.0 -m "v0.1.0 — initial release with 5 domain presets + V001/V002/V003 validators"
```

Expected: 커밋 ~20개, tag v0.1.0 생성.

### 🚩 Milestone M9 Gate
- business-fullstack-creater needs 문서 3개 갱신
- 2단계 입력 계약 문서화
- plugin repo v0.1.0 태그

---

# 최종 검증 게이트 (모든 M 통과 후)

- [ ] `pytest tests/ -v` — 모든 테스트 통과
- [ ] `python scripts/rdb_index.py lint .claude/skills/karpathy-rdb/wiki-template/` — entities 0, ERROR 0
- [ ] `python scripts/rdb_index.py lint tests/fixtures/golden_wiki/` — entities 2, ERROR 0
- [ ] plugin.json + SKILL.md + 3 commands + 3 protocols + 2 references + 5 presets + 3 guides 존재 확인:
  ```powershell
  Get-ChildItem -Recurse | Where-Object { $_.Extension -in '.md','.json','.py' } | Measure-Object | Select-Object Count
  ```
  Expected: ≥ 35 files
- [ ] git log: ≥ 20 commits, tag v0.1.0 존재

---

## 참고: 의도적으로 v1에서 뺀 항목 (Spec Section 9 일치)

- 외부 LLM helper (대용량 PDF 압축)
- UI metadata (`_uimanifest.yaml`)
- 멀티 wiki / 모노레포 지원
- DDL 직접 생성 (2단계 책임)
- V004~V010 검증기 구현 (v1.1에서 추가 — 본 plan에는 코드/규칙만 명시, 구현은 V001~V003만)

v1.1 backlog:
- V004 (FK 타입 일관성) 구현
- V005 (순환 의존 검출) 구현
- V006~V010 INFO/WARN 검증기 구현
- `_blueprint.yaml` 실제 생성 로직 (`compile` 명령의 yaml 출력 — 현재는 lint만)
- `compile-report.md` 자동 생성
