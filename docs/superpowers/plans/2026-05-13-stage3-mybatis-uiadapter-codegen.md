# Stage 3 — andrej-karpathy-rdb-mybatis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Claude Code plugin that consumes Stage 1 `_blueprint.yaml` + Stage 2 V001~V004 DDL and produces a complete `backend/` directory with MyBatis/uiadapter controller, service, mapper, domain POJO, plus `schema.sql`/`data.sql` for HSQLDB runtime.

**Architecture:** 7-stage Python pipeline (load → normalize → precompute → DDL convert → render → revalidate → report). Hybrid strategy: Jinja2 templates carry the static skeleton while Python `precompute` helpers compute every branching/loop input. Six per-entity Java/XML templates + two SQL templates + one report template.

**Tech Stack:** Python 3.11+, `pyyaml`, `jinja2` (`StrictUndefined`), `pytest`, `subprocess` for `javac`. No Java/Maven build during generation.

**Spec:** `docs/superpowers/specs/2026-05-13-stage3-mybatis-uiadapter-codegen-design.md`

**Plugin repo (created by Task 1):** `D:\AI\workspace\andrej-karpathy-rdb-mybatis\`

---

## Milestone Overview

| M | Scope | Tasks |
|---|---|---|
| M1 | Repo scaffold, plugin manifest, reference docs | 1–2 |
| M2 | blueprint_loader + ddl_loader | 3–4 |
| M3 | name_mapper | 5 |
| M4 | column_classifier | 6 |
| M5 | precompute helpers | 7–9 |
| M6 | postgres_to_hsqldb | 10 |
| M7 | Templates (domain/mapper/service/controller/sql) | 11–17 |
| M8 | codegen orchestrator | 18 |
| M9 | revalidator (xml lint + javac) | 19–20 |
| M10 | reporter | 21 |
| M11 | CLI compile.py + slash command | 22–23 |
| M12 | Golden path E2E | 24 |
| M13 | README + INSTALL-FOR-AI + tag v0.1.0 | 25–26 |

Total: 26 tasks.

---

## File Structure

Plugin source (created over the plan, all paths relative to `D:\AI\workspace\andrej-karpathy-rdb-mybatis\`):

```
.claude/
├── plugin.json
├── commands/karpathy-rdb-mybatis.md
└── skills/karpathy-rdb-mybatis/
    ├── SKILL.md
    ├── references/
    │   ├── blueprint-input-contract.md
    │   ├── nexacro-uiadapter-spec.md
    │   └── output-layout.md
    └── templates/
        ├── domain/entity.java.j2
        ├── mapper/mapper-interface.java.j2
        ├── mapper/mapper.xml.j2
        ├── service/service-interface.java.j2
        ├── service/service-impl.java.j2
        ├── controller/controller.java.j2
        └── ddl/{schema.sql.j2, data.sql.j2}
scripts/
├── compile.py
├── blueprint_loader.py
├── ddl_loader.py
├── name_mapper.py
├── column_classifier.py
├── precompute.py
├── postgres_to_hsqldb.py
├── codegen.py
├── revalidator.py
└── reporter.py
tests/
├── fixtures/{golden_blueprint/, golden_ddl/, expected_output/}
└── test_*.py (10 files)
README.md
INSTALL-FOR-AI.md
pyproject.toml
```

---

## Setup Conventions

- **PowerShell** is the default shell on this Windows machine. Bash works if WSL/Git Bash is installed; commands below use forward slashes where possible.
- All `pytest`, `python`, and `git` commands run from the plugin repo root unless noted.
- **Commit policy** (from user CLAUDE.md): one commit per file when sensible. Each task ends with one `git commit`; if a task touches multiple unrelated files, split into multiple commits within the same task.
- **`StrictUndefined`** must be used on every Jinja2 `Environment` so a missing template variable raises rather than rendering blank.

---

## Task 1: Repo scaffold + plugin manifest

**Files:**
- Create: `D:\AI\workspace\andrej-karpathy-rdb-mybatis\.claude\plugin.json`
- Create: `D:\AI\workspace\andrej-karpathy-rdb-mybatis\.claude\commands\karpathy-rdb-mybatis.md`
- Create: `D:\AI\workspace\andrej-karpathy-rdb-mybatis\.claude\skills\karpathy-rdb-mybatis\SKILL.md`
- Create: `D:\AI\workspace\andrej-karpathy-rdb-mybatis\pyproject.toml`
- Create: `D:\AI\workspace\andrej-karpathy-rdb-mybatis\.gitignore`

- [ ] **Step 1: Initialize repo and create directories**

```powershell
mkdir D:\AI\workspace\andrej-karpathy-rdb-mybatis
cd D:\AI\workspace\andrej-karpathy-rdb-mybatis
git init
mkdir .claude\commands, .claude\skills\karpathy-rdb-mybatis\references, .claude\skills\karpathy-rdb-mybatis\templates\domain, .claude\skills\karpathy-rdb-mybatis\templates\mapper, .claude\skills\karpathy-rdb-mybatis\templates\service, .claude\skills\karpathy-rdb-mybatis\templates\controller, .claude\skills\karpathy-rdb-mybatis\templates\ddl, scripts, tests\fixtures\golden_blueprint, tests\fixtures\golden_ddl, tests\fixtures\expected_output
```

- [ ] **Step 2: Write `pyproject.toml`**

```toml
[project]
name = "andrej-karpathy-rdb-mybatis"
version = "0.1.0"
description = "Stage 3 codegen — Blueprint + DDL → MyBatis/nexacro uiadapter backend"
requires-python = ">=3.11"
dependencies = ["pyyaml>=6.0", "jinja2>=3.1"]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[tool.pytest.ini_options]
pythonpath = ["scripts"]
testpaths = ["tests"]
```

- [ ] **Step 3: Write `.gitignore`**

```
__pycache__/
*.pyc
.pytest_cache/
*.egg-info/
.venv/
tests/fixtures/_tmp_*/
```

- [ ] **Step 4: Write `.claude/plugin.json`**

```json
{
  "name": "andrej-karpathy-rdb-mybatis",
  "version": "0.1.0",
  "description": "Stage 3 — Blueprint + DDL → MyBatis/nexacro uiadapter backend codegen",
  "author": "business-fullstack-creater",
  "commands": [".claude/commands"],
  "skills": [".claude/skills"]
}
```

- [ ] **Step 5: Write `.claude/commands/karpathy-rdb-mybatis.md`**

```markdown
---
name: karpathy-rdb-mybatis
description: Stage 3 — Generate MyBatis + nexacro uiadapter backend from Stage 1/2 artifacts
argument-hint: compile [--blueprint <path>] [--ddl-dir <path>] [--out <path>] [--package <name>] [--skip-compile] [--dry-run]
allowed-tools: Bash, Read, Write, Edit
---

Run the Stage 3 codegen pipeline.

Arguments after `compile`:
- `--blueprint <path>` (default `wiki/_blueprint.yaml`)
- `--ddl-dir <path>` (default `db/migrations`)
- `--out <path>` (default `backend/`)
- `--package <name>` (default `com.nexacro.uiadapter`)
- `--table-prefix <prefix>` (default `TB_`, sanity check only)
- `--skip-compile` to bypass R006 javac
- `--dry-run` to write report only

Execute via:
`python scripts/compile.py $ARGUMENTS`
```

- [ ] **Step 6: Write `.claude/skills/karpathy-rdb-mybatis/SKILL.md`**

```markdown
---
name: karpathy-rdb-mybatis
description: Generates MyBatis + nexacro uiadapter backend (controller/service/mapper/domain + schema.sql/data.sql) from Stage 1 blueprint and Stage 2 DDL.
---

# karpathy-rdb-mybatis

Stage 3 of the business-fullstack-creater pipeline.

## Inputs
- `wiki/_blueprint.yaml` — Stage 1 output (version 1, validation.passed must be true)
- `db/migrations/V001~V004__*.sql` — Stage 2 PostgreSQL DDL
- `db/seed/*.sql` (optional) — Stage 2 seed rows

## Outputs (under `--out`, default `backend/`)
- `src/main/java/com/nexacro/uiadapter/{controller,service,service/impl,mapper,domain}/*.java`
- `src/main/resources/schema.sql`, `data.sql`
- `src/main/resources/mybatis/mapper/*.xml`
- `mybatis-report.md`

## Conventions
- 4.2 canonical package layout under `com.nexacro.uiadapter`
- Plain POJO `extends NexacroBase`, no Lombok, no JPA
- Endpoints `/<entity>/select_datalist_map.do`, `/<entity>/save_datalist_map.do`
- Map-based search input, `List<Map<String,Object>>` output
- HSQLDB runtime via `schema.sql` (Spring Boot bootstrap)

See `references/` for the input contract, output layout, and uiadapter spec.
```

- [ ] **Step 7: Commit each file separately**

```powershell
git add pyproject.toml
git commit -m "chore: pyproject for andrej-karpathy-rdb-mybatis"
git add .gitignore
git commit -m "chore: gitignore"
git add .claude/plugin.json
git commit -m "feat: plugin manifest"
git add .claude/commands/karpathy-rdb-mybatis.md
git commit -m "feat: slash command karpathy-rdb-mybatis"
git add .claude/skills/karpathy-rdb-mybatis/SKILL.md
git commit -m "feat: SKILL.md for stage 3 codegen"
```

---

## Task 2: Reference docs

**Files:**
- Create: `.claude/skills/karpathy-rdb-mybatis/references/blueprint-input-contract.md`
- Create: `.claude/skills/karpathy-rdb-mybatis/references/nexacro-uiadapter-spec.md`
- Create: `.claude/skills/karpathy-rdb-mybatis/references/output-layout.md`

- [ ] **Step 1: Write `blueprint-input-contract.md`**

```markdown
# Blueprint Input Contract (Stage 1 → Stage 3)

Source: `wiki/_blueprint.yaml` produced by `/karpathy-rdb compile`.

## Required top-level keys
- `version`: must equal `1`
- `project`: string (Korean domain name)
- `entities`: list of `{name, table, schema, columns, indexes?, constraints?}`
- `relations`: list of `{from, to, cardinality, fk, on_delete?}`
- `business_rules`: list of `{name, applies_to, enforced_by}`
- `validation.passed`: must equal `true`

## Entity column shape
```yaml
columns:
  - { name: customer_id, type: varchar(36), pk: true, null: false }
  - { name: name,        type: varchar(100), null: true }
```

## Hard rejects
- `version != 1` → exit 1
- `validation.passed != true` → exit 1
- any entity with zero `pk: true` columns → exit 1
```

- [ ] **Step 2: Write `nexacro-uiadapter-spec.md`**

```markdown
# nexacro uiadapter Spec Summary

References:
- `spring boot 3.0기반-nexacroN-개발자가이드(v0.3).pdf` p.62–74
- GitLab: `nexacron/spring-boot/jakarta/uiadapter-jakarta` `BoardController.java`, `BoardServiceImpl.java`

## Mandatory imports (per layer)
- Controller: `com.nexacro.uiadapter.jakarta.core.data.{NexacroResult, ParamDataSet}`, `com.nexacro.uiadapter.jakarta.core.NexacroException`
- ServiceImpl: `com.nexacro.java.xapi.data.DataSet`, `com.nexacro.uiadapter.jakarta.core.data.DataSetRowTypeAccessor`, `org.mybatis.spring.SqlSessionTemplate`
- Domain: `com.nexacro.uiadapter.jakarta.core.data.NexacroBase`

> JDK17 / Jakarta EE target: NexacroN uiadapter classes live under the `.jakarta.` package, not `.spring.`. The `.spring.` variant is for the legacy javax (Spring Boot 2.x / JDK 8-11) artifact.

## Save dispatch (single endpoint)
```java
int rowType = Integer.parseInt(String.valueOf(row.get(DataSetRowTypeAccessor.NAME)));
if (rowType == DataSet.ROW_TYPE_INSERTED) { mapper.insert_<entity>_map(row); }
else if (rowType == DataSet.ROW_TYPE_UPDATED) { mapper.update_<entity>_map(row); }
else if (rowType == DataSet.ROW_TYPE_DELETED) { mapper.delete_<entity>_map(row); }
```

## Method naming
- Controller method = endpoint segment (snake_case): `select_datalist_map`, `save_datalist_map`
- Service / Mapper methods: `<verb>_<entity>_<suffix>_map` — `select_<entity>_datalist_map`, `insert_<entity>_map`, `update_<entity>_map`, `delete_<entity>_map`, `save_<entity>_datalist_map`

## Mapper XML
- `namespace` = full mapper interface FQCN
- column references = `#{UPPER_SNAKE}` matching DDL column names
- `parameterType="java.util.Map"`, `resultType="java.util.Map"` (search list)
```

- [ ] **Step 3: Write `output-layout.md`**

```markdown
# Output Layout (Stage 3)

Under `--out` (default `backend/`):

```
src/main/java/com/nexacro/uiadapter/
├── controller/<Entity>Controller.java
├── service/<Entity>Service.java
├── service/impl/<Entity>ServiceImpl.java
├── mapper/<Entity>Mapper.java
└── domain/<Entity>.java
src/main/resources/
├── schema.sql
├── data.sql                (if seed present)
└── mybatis/mapper/<Entity>Mapper.xml
mybatis-report.md
```

Stage 3 does NOT touch `pom.xml`, `application.yml`, `Application.java`, or `config/` — those come from `nexacro-fullstack-starter`.
```

- [ ] **Step 4: Commit each file**

```powershell
git add .claude/skills/karpathy-rdb-mybatis/references/blueprint-input-contract.md
git commit -m "docs: blueprint input contract reference"
git add .claude/skills/karpathy-rdb-mybatis/references/nexacro-uiadapter-spec.md
git commit -m "docs: nexacro uiadapter spec reference"
git add .claude/skills/karpathy-rdb-mybatis/references/output-layout.md
git commit -m "docs: stage 3 output layout reference"
```

---

## Task 3: blueprint_loader

**Files:**
- Create: `scripts/blueprint_loader.py`
- Create: `tests/test_blueprint_loader.py`
- Create: `tests/fixtures/golden_blueprint/_blueprint.yaml`

- [ ] **Step 1: Seed `tests/fixtures/golden_blueprint/_blueprint.yaml`**

Copy this minimal valid blueprint (used by all later tests):

```yaml
version: 1
project: 고객관리
entities:
  - name: customer
    table: TB_CUSTOMER
    schema: public
    columns:
      - { name: customer_id, type: varchar(36), pk: true,  null: false }
      - { name: name,        type: varchar(100), null: true }
      - { name: email,       type: varchar(200), null: true }
      - { name: status,      type: varchar(20),  null: true }
    indexes:
      - { name: ix_tb_customer_email, columns: [email], unique: false }
  - name: address
    table: TB_ADDRESS
    schema: public
    columns:
      - { name: address_id,  type: varchar(36), pk: true,  null: false }
      - { name: customer_id, type: varchar(36), null: false }
      - { name: line1,       type: varchar(200), null: true }
relations:
  - { from: address, to: customer, cardinality: "N:1", fk: customer_id, on_delete: cascade }
business_rules: []
validation:
  passed: true
```

- [ ] **Step 2: Write failing test `tests/test_blueprint_loader.py`**

```python
import pathlib
import pytest
from blueprint_loader import load, BlueprintError

GOLDEN = pathlib.Path(__file__).parent / "fixtures" / "golden_blueprint" / "_blueprint.yaml"


def test_golden_loads():
    bp = load(GOLDEN)
    assert bp["project"] == "고객관리"
    assert len(bp["entities"]) == 2


def test_rejects_wrong_version(tmp_path):
    p = tmp_path / "bp.yaml"
    p.write_text("version: 2\nproject: x\nentities: []\nrelations: []\nbusiness_rules: []\nvalidation: {passed: true}\n", encoding="utf-8")
    with pytest.raises(BlueprintError, match="version"):
        load(p)


def test_rejects_validation_failed(tmp_path):
    p = tmp_path / "bp.yaml"
    p.write_text("version: 1\nproject: x\nentities: []\nrelations: []\nbusiness_rules: []\nvalidation: {passed: false}\n", encoding="utf-8")
    with pytest.raises(BlueprintError, match="validation.passed"):
        load(p)


def test_rejects_missing_file(tmp_path):
    with pytest.raises(BlueprintError, match="not found"):
        load(tmp_path / "missing.yaml")
```

- [ ] **Step 3: Run test, verify fail**

```powershell
pytest tests/test_blueprint_loader.py -v
```
Expected: `ModuleNotFoundError: No module named 'blueprint_loader'`

- [ ] **Step 4: Implement `scripts/blueprint_loader.py`**

```python
import pathlib
import yaml


class BlueprintError(Exception):
    pass


def load(path: pathlib.Path) -> dict:
    path = pathlib.Path(path)
    if not path.exists():
        raise BlueprintError(f"blueprint not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data.get("version") != 1:
        raise BlueprintError(f"unsupported blueprint version: {data.get('version')} (expected 1)")
    validation = data.get("validation") or {}
    if validation.get("passed") is not True:
        raise BlueprintError("blueprint validation.passed is not true — re-run Stage 1 /karpathy-rdb compile")
    return data
```

- [ ] **Step 5: Run test, verify pass**

```powershell
pytest tests/test_blueprint_loader.py -v
```
Expected: 4 passed

- [ ] **Step 6: Commit**

```powershell
git add tests/fixtures/golden_blueprint/_blueprint.yaml
git commit -m "test: golden blueprint fixture"
git add scripts/blueprint_loader.py tests/test_blueprint_loader.py
git commit -m "feat: blueprint loader with version + validation gates"
```

---

## Task 4: ddl_loader

**Files:**
- Create: `scripts/ddl_loader.py`
- Create: `tests/test_ddl_loader.py`
- Create: `tests/fixtures/golden_ddl/V001__create_schema.sql`
- Create: `tests/fixtures/golden_ddl/V002__create_tables.sql`
- Create: `tests/fixtures/golden_ddl/V003__create_indexes.sql`
- Create: `tests/fixtures/golden_ddl/V004__create_constraints.sql`

- [ ] **Step 1: Seed `tests/fixtures/golden_ddl/V001__create_schema.sql`**

```sql
CREATE SCHEMA IF NOT EXISTS public;
```

- [ ] **Step 2: Seed `tests/fixtures/golden_ddl/V002__create_tables.sql`**

```sql
CREATE TABLE public.TB_CUSTOMER (
  CUSTOMER_ID VARCHAR(36) NOT NULL,
  NAME        VARCHAR(100),
  EMAIL       VARCHAR(200),
  STATUS      VARCHAR(20),
  CONSTRAINT PK_TB_CUSTOMER PRIMARY KEY (CUSTOMER_ID)
);

CREATE TABLE public.TB_ADDRESS (
  ADDRESS_ID  VARCHAR(36) NOT NULL,
  CUSTOMER_ID VARCHAR(36) NOT NULL,
  LINE1       VARCHAR(200),
  CONSTRAINT PK_TB_ADDRESS PRIMARY KEY (ADDRESS_ID)
);
```

- [ ] **Step 3: Seed `tests/fixtures/golden_ddl/V003__create_indexes.sql`**

```sql
CREATE INDEX ix_tb_customer_email ON public.TB_CUSTOMER (EMAIL);
```

- [ ] **Step 4: Seed `tests/fixtures/golden_ddl/V004__create_constraints.sql`**

```sql
ALTER TABLE public.TB_ADDRESS
  ADD CONSTRAINT fk_tb_address_customer
  FOREIGN KEY (CUSTOMER_ID) REFERENCES public.TB_CUSTOMER (CUSTOMER_ID)
  ON DELETE CASCADE;
```

- [ ] **Step 5: Write failing test `tests/test_ddl_loader.py`**

```python
import pathlib
import pytest
from ddl_loader import load, DDLBundleError

GOLDEN = pathlib.Path(__file__).parent / "fixtures" / "golden_ddl"


def test_golden_loads():
    bundle = load(GOLDEN)
    assert bundle.schema_sql.startswith("CREATE SCHEMA")
    assert "TB_CUSTOMER" in bundle.tables_sql
    assert "ix_tb_customer_email" in bundle.indexes_sql
    assert "FOREIGN KEY" in bundle.constraints_sql
    assert bundle.seed_files == []


def test_rejects_missing_file(tmp_path):
    (tmp_path / "V001__create_schema.sql").write_text("-- empty", encoding="utf-8")
    with pytest.raises(DDLBundleError, match="V002"):
        load(tmp_path)


def test_collects_seed_files(tmp_path):
    for n in ["V001__create_schema.sql","V002__create_tables.sql","V003__create_indexes.sql","V004__create_constraints.sql"]:
        (tmp_path / n).write_text("-- " + n, encoding="utf-8")
    seed = tmp_path.parent / "seed"
    seed.mkdir()
    (seed / "01_customer_sample.sql").write_text("INSERT INTO TB_CUSTOMER VALUES ('1','a','b','c');", encoding="utf-8")
    bundle = load(tmp_path, seed_dir=seed)
    assert len(bundle.seed_files) == 1
```

- [ ] **Step 6: Run test, verify fail**

```powershell
pytest tests/test_ddl_loader.py -v
```
Expected: `ModuleNotFoundError`

- [ ] **Step 7: Implement `scripts/ddl_loader.py`**

```python
import pathlib
from dataclasses import dataclass, field


class DDLBundleError(Exception):
    pass


@dataclass
class DDLBundle:
    schema_sql: str = ""
    tables_sql: str = ""
    indexes_sql: str = ""
    constraints_sql: str = ""
    seed_files: list = field(default_factory=list)


REQUIRED = {
    "schema":      "V001__create_schema.sql",
    "tables":      "V002__create_tables.sql",
    "indexes":     "V003__create_indexes.sql",
    "constraints": "V004__create_constraints.sql",
}


def load(ddl_dir: pathlib.Path, seed_dir: pathlib.Path | None = None) -> DDLBundle:
    ddl_dir = pathlib.Path(ddl_dir)
    if not ddl_dir.exists():
        raise DDLBundleError(f"ddl dir not found: {ddl_dir}")
    bundle = DDLBundle()
    for slot, fname in REQUIRED.items():
        p = ddl_dir / fname
        if not p.exists():
            raise DDLBundleError(f"missing required DDL file: {fname}")
        setattr(bundle, f"{slot}_sql", p.read_text(encoding="utf-8"))
    if seed_dir and pathlib.Path(seed_dir).exists():
        bundle.seed_files = sorted(pathlib.Path(seed_dir).glob("*.sql"))
    return bundle
```

- [ ] **Step 8: Run test, verify pass**

```powershell
pytest tests/test_ddl_loader.py -v
```
Expected: 3 passed

- [ ] **Step 9: Commit**

```powershell
git add tests/fixtures/golden_ddl/
git commit -m "test: golden DDL fixture (V001-V004)"
git add scripts/ddl_loader.py tests/test_ddl_loader.py
git commit -m "feat: ddl_loader for V001-V004 + optional seed"
```

---

## Task 5: name_mapper

**Files:**
- Create: `scripts/name_mapper.py`
- Create: `tests/test_name_mapper.py`

- [ ] **Step 1: Write failing test `tests/test_name_mapper.py`**

```python
from name_mapper import to_pascal, to_camel, to_upper_snake, to_snake


def test_to_pascal():
    assert to_pascal("customer") == "Customer"
    assert to_pascal("customer_address") == "CustomerAddress"
    assert to_pascal("TB_CUSTOMER") == "TbCustomer"


def test_to_camel():
    assert to_camel("customer_id") == "customerId"
    assert to_camel("status") == "status"


def test_to_upper_snake():
    assert to_upper_snake("customer_id") == "CUSTOMER_ID"
    assert to_upper_snake("customerId") == "CUSTOMER_ID"


def test_to_snake():
    assert to_snake("CustomerId") == "customer_id"
    assert to_snake("CUSTOMER_ID") == "customer_id"
    assert to_snake("customerId") == "customer_id"
```

- [ ] **Step 2: Run test, verify fail**

```powershell
pytest tests/test_name_mapper.py -v
```
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement `scripts/name_mapper.py`**

```python
import re

_camel_split = re.compile(r"(?<!^)(?=[A-Z])")


def to_snake(s: str) -> str:
    if "_" in s:
        return s.lower()
    return _camel_split.sub("_", s).lower()


def to_upper_snake(s: str) -> str:
    return to_snake(s).upper()


def to_pascal(s: str) -> str:
    parts = to_snake(s).split("_")
    return "".join(p.capitalize() for p in parts if p)


def to_camel(s: str) -> str:
    p = to_pascal(s)
    return p[0].lower() + p[1:] if p else p
```

- [ ] **Step 4: Run test, verify pass**

```powershell
pytest tests/test_name_mapper.py -v
```
Expected: 4 passed

- [ ] **Step 5: Commit**

```powershell
git add scripts/name_mapper.py tests/test_name_mapper.py
git commit -m "feat: name_mapper for snake/UPPER_SNAKE/PascalCase/camelCase"
```

---

## Task 6: column_classifier

**Files:**
- Create: `scripts/column_classifier.py`
- Create: `tests/test_column_classifier.py`

- [ ] **Step 1: Write failing test `tests/test_column_classifier.py`**

```python
import pytest
from column_classifier import classify, validate_pk_coverage, ColumnClassifierError


def _entity(name, cols):
    return {"name": name, "table": "TB_" + name.upper(), "columns": cols}


def test_classify_pk_and_non_pk():
    e = _entity("customer", [
        {"name": "customer_id", "type": "varchar(36)", "pk": True},
        {"name": "name",        "type": "varchar(100)"},
        {"name": "email",       "type": "varchar(200)"},
    ])
    c = classify(e)
    assert [x["name"] for x in c["pk"]] == ["customer_id"]
    assert [x["name"] for x in c["non_pk"]] == ["name", "email"]
    assert [x["name"] for x in c["all"]] == ["customer_id", "name", "email"]


def test_validate_pk_coverage_passes():
    entities = [_entity("customer", [{"name": "id", "pk": True, "type": "int"}])]
    validate_pk_coverage(entities)


def test_validate_pk_coverage_fails_when_no_pk():
    entities = [_entity("orphan", [{"name": "x", "type": "int"}])]
    with pytest.raises(ColumnClassifierError, match="PK"):
        validate_pk_coverage(entities)
```

- [ ] **Step 2: Run test, verify fail**

```powershell
pytest tests/test_column_classifier.py -v
```
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement `scripts/column_classifier.py`**

```python
class ColumnClassifierError(Exception):
    pass


def classify(entity: dict) -> dict:
    cols = entity.get("columns") or []
    pk = [c for c in cols if c.get("pk")]
    non_pk = [c for c in cols if not c.get("pk")]
    return {"pk": pk, "non_pk": non_pk, "all": cols}


def validate_pk_coverage(entities: list) -> None:
    bad = [e["name"] for e in entities if not any(c.get("pk") for c in (e.get("columns") or []))]
    if bad:
        raise ColumnClassifierError(f"entities without PK: {bad}")
```

- [ ] **Step 4: Run test, verify pass**

```powershell
pytest tests/test_column_classifier.py -v
```
Expected: 3 passed

- [ ] **Step 5: Commit**

```powershell
git add scripts/column_classifier.py tests/test_column_classifier.py
git commit -m "feat: column_classifier with R004 PK coverage validation"
```

---

## Task 7: precompute helper — mapper columns

**Files:**
- Create: `scripts/precompute.py`
- Create: `tests/test_precompute.py`

- [ ] **Step 1: Write failing test (mapper columns portion)**

```python
from precompute import gather_mapper_columns


def test_gather_mapper_columns_basic():
    entity = {
        "name": "customer",
        "table": "TB_CUSTOMER",
        "columns": [
            {"name": "customer_id", "type": "varchar(36)", "pk": True},
            {"name": "name",        "type": "varchar(100)"},
            {"name": "email",       "type": "varchar(200)"},
        ],
    }
    out = gather_mapper_columns(entity)
    assert out["pk_upper"] == ["CUSTOMER_ID"]
    assert out["non_pk_upper"] == ["NAME", "EMAIL"]
    assert out["all_upper"] == ["CUSTOMER_ID", "NAME", "EMAIL"]
    assert out["all_lower"] == ["customer_id", "name", "email"]
```

- [ ] **Step 2: Run test, verify fail**

```powershell
pytest tests/test_precompute.py -v
```
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement `scripts/precompute.py` (initial)**

```python
from name_mapper import to_upper_snake
from column_classifier import classify


def gather_mapper_columns(entity: dict) -> dict:
    c = classify(entity)
    return {
        "pk_upper":     [to_upper_snake(x["name"]) for x in c["pk"]],
        "non_pk_upper": [to_upper_snake(x["name"]) for x in c["non_pk"]],
        "all_upper":    [to_upper_snake(x["name"]) for x in c["all"]],
        "all_lower":    [x["name"] for x in c["all"]],
    }
```

- [ ] **Step 4: Run test, verify pass**

```powershell
pytest tests/test_precompute.py -v
```
Expected: 1 passed

- [ ] **Step 5: Commit**

```powershell
git add scripts/precompute.py tests/test_precompute.py
git commit -m "feat: precompute.gather_mapper_columns"
```

---

## Task 8: precompute helper — save branches + search predicates

**Files:**
- Modify: `scripts/precompute.py`
- Modify: `tests/test_precompute.py`

- [ ] **Step 1: Append failing tests to `tests/test_precompute.py`**

```python
from precompute import build_save_branches, build_search_predicates


def test_build_save_branches():
    entity = {"name": "customer", "columns": [{"name": "customer_id", "pk": True}]}
    branches = build_save_branches(entity)
    assert branches == [
        {"row_type_const": "DataSet.ROW_TYPE_INSERTED", "mapper_method": "insert_customer_map"},
        {"row_type_const": "DataSet.ROW_TYPE_UPDATED",  "mapper_method": "update_customer_map"},
        {"row_type_const": "DataSet.ROW_TYPE_DELETED",  "mapper_method": "delete_customer_map"},
    ]


def test_build_search_predicates():
    entity = {"name": "customer", "columns": [
        {"name": "customer_id", "pk": True},
        {"name": "name"},
        {"name": "email"},
    ]}
    preds = build_search_predicates(entity)
    assert preds == [
        '<if test="CUSTOMER_ID != null and CUSTOMER_ID != \'\'"> AND CUSTOMER_ID = #{CUSTOMER_ID}</if>',
        '<if test="NAME != null and NAME != \'\'"> AND NAME = #{NAME}</if>',
        '<if test="EMAIL != null and EMAIL != \'\'"> AND EMAIL = #{EMAIL}</if>',
    ]
```

- [ ] **Step 2: Run, verify the two new tests fail**

```powershell
pytest tests/test_precompute.py -v
```
Expected: `ImportError` on the new names.

- [ ] **Step 3: Extend `scripts/precompute.py`**

```python
def build_save_branches(entity: dict) -> list:
    name = entity["name"]
    return [
        {"row_type_const": "DataSet.ROW_TYPE_INSERTED", "mapper_method": f"insert_{name}_map"},
        {"row_type_const": "DataSet.ROW_TYPE_UPDATED",  "mapper_method": f"update_{name}_map"},
        {"row_type_const": "DataSet.ROW_TYPE_DELETED",  "mapper_method": f"delete_{name}_map"},
    ]


def build_search_predicates(entity: dict) -> list:
    cols = gather_mapper_columns(entity)["all_upper"]
    return [
        f'<if test="{c} != null and {c} != \'\'"> AND {c} = #{{{c}}}</if>'
        for c in cols
    ]
```

- [ ] **Step 4: Run, verify pass**

```powershell
pytest tests/test_precompute.py -v
```
Expected: 3 passed total in this file.

- [ ] **Step 5: Commit**

```powershell
git add scripts/precompute.py tests/test_precompute.py
git commit -m "feat: precompute.build_save_branches + build_search_predicates"
```

---

## Task 9: precompute helper — domain fields + entity context

**Files:**
- Modify: `scripts/precompute.py`
- Modify: `tests/test_precompute.py`

- [ ] **Step 1: Append failing tests**

```python
from precompute import build_domain_fields, build_entity_context


def test_build_domain_fields():
    entity = {"name": "customer", "columns": [
        {"name": "customer_id", "type": "varchar(36)", "pk": True},
        {"name": "status", "type": "varchar(20)"},
    ]}
    fields = build_domain_fields(entity)
    field_names = [f["field"] for f in fields]
    assert "customerId" in field_names
    assert "status" in field_names
    # auto search fields
    assert "searchCondition" in field_names
    assert "searchKeyword" in field_names
    assert "searchUseYn" in field_names
    customer_id = next(f for f in fields if f["field"] == "customerId")
    assert customer_id["java_type"] == "String"
    assert customer_id["getter"] == "getCustomerId"
    assert customer_id["setter"] == "setCustomerId"


def test_build_entity_context_shape():
    entity = {"name": "customer", "table": "TB_CUSTOMER", "columns": [
        {"name": "customer_id", "type": "varchar(36)", "pk": True},
        {"name": "name", "type": "varchar(100)"},
    ]}
    ctx = build_entity_context(entity, base_package="com.nexacro.uiadapter")
    assert ctx["entity_name"] == "customer"
    assert ctx["pascal"] == "Customer"
    assert ctx["camel"] == "customer"
    assert ctx["table"] == "TB_CUSTOMER"
    assert ctx["base_package"] == "com.nexacro.uiadapter"
    assert ctx["mapper_fqcn"] == "com.nexacro.uiadapter.mapper.CustomerMapper"
    assert ctx["endpoint_base"] == "/customer"
    assert ctx["mapper_columns"]["pk_upper"] == ["CUSTOMER_ID"]
    assert ctx["save_branches"][0]["mapper_method"] == "insert_customer_map"
    assert ctx["search_predicates"][0].startswith('<if test="CUSTOMER_ID')
    assert ctx["fields"][0]["field"] == "customerId"
```

- [ ] **Step 2: Run, verify fail**

```powershell
pytest tests/test_precompute.py -v
```
Expected: import errors on `build_domain_fields`, `build_entity_context`.

- [ ] **Step 3: Extend `scripts/precompute.py`**

```python
from name_mapper import to_camel, to_pascal

_TYPE_MAP = {
    "varchar": "String", "char": "String", "text": "String", "longvarchar": "String",
    "int": "Integer", "integer": "Integer", "smallint": "Integer",
    "bigint": "Long", "long": "Long",
    "numeric": "java.math.BigDecimal", "decimal": "java.math.BigDecimal",
    "boolean": "Boolean", "bool": "Boolean",
    "timestamp": "java.sql.Timestamp", "date": "java.sql.Date", "time": "java.sql.Time",
}

_SEARCH_FIELDS = [
    {"field": "searchCondition", "java_type": "String"},
    {"field": "searchKeyword",   "java_type": "String"},
    {"field": "searchUseYn",     "java_type": "String"},
]


def _java_type_for(sql_type: str) -> str:
    base = (sql_type or "").split("(")[0].strip().lower()
    return _TYPE_MAP.get(base, "String")


def build_domain_fields(entity: dict) -> list:
    out = []
    for c in entity.get("columns") or []:
        field = to_camel(c["name"])
        jt = _java_type_for(c.get("type"))
        cap = field[0].upper() + field[1:]
        out.append({"field": field, "java_type": jt, "getter": f"get{cap}", "setter": f"set{cap}"})
    for sf in _SEARCH_FIELDS:
        cap = sf["field"][0].upper() + sf["field"][1:]
        out.append({"field": sf["field"], "java_type": sf["java_type"],
                    "getter": f"get{cap}", "setter": f"set{cap}"})
    return out


def build_entity_context(entity: dict, base_package: str) -> dict:
    name = entity["name"]
    pascal = to_pascal(name)
    return {
        "entity_name": name,
        "pascal": pascal,
        "camel": to_camel(name),
        "table": entity["table"],
        "base_package": base_package,
        "mapper_fqcn": f"{base_package}.mapper.{pascal}Mapper",
        "endpoint_base": f"/{name}",
        "mapper_columns": gather_mapper_columns(entity),
        "save_branches": build_save_branches(entity),
        "search_predicates": build_search_predicates(entity),
        "fields": build_domain_fields(entity),
    }
```

- [ ] **Step 4: Run, verify pass**

```powershell
pytest tests/test_precompute.py -v
```
Expected: 5 passed in this file.

- [ ] **Step 5: Commit**

```powershell
git add scripts/precompute.py tests/test_precompute.py
git commit -m "feat: precompute.build_domain_fields + build_entity_context"
```

---

## Task 10: postgres_to_hsqldb dialect converter

**Files:**
- Create: `scripts/postgres_to_hsqldb.py`
- Create: `tests/test_postgres_to_hsqldb.py`

- [ ] **Step 1: Write failing test `tests/test_postgres_to_hsqldb.py`**

```python
from postgres_to_hsqldb import convert_bundle
from ddl_loader import DDLBundle


def test_strips_create_schema():
    b = DDLBundle(schema_sql="CREATE SCHEMA IF NOT EXISTS public;\n",
                  tables_sql="CREATE TABLE public.x (id int);",
                  indexes_sql="", constraints_sql="")
    out = convert_bundle(b)
    assert "CREATE SCHEMA" not in out
    assert "public.x" not in out
    assert "CREATE TABLE x" in out


def test_type_substitutions():
    b = DDLBundle(schema_sql="", indexes_sql="", constraints_sql="",
                  tables_sql="CREATE TABLE t (a SERIAL, b TEXT, c NUMERIC(10,2), d TIMESTAMP WITH TIME ZONE);")
    out = convert_bundle(b)
    assert "INTEGER GENERATED BY DEFAULT AS IDENTITY" in out
    assert "LONGVARCHAR" in out
    assert "DECIMAL(10,2)" in out
    assert "TIMESTAMP" in out and "WITH TIME ZONE" not in out


def test_jsonb_downgrade_with_warning():
    b = DDLBundle(schema_sql="", indexes_sql="", constraints_sql="",
                  tables_sql="CREATE TABLE t (payload JSONB);")
    out = convert_bundle(b)
    assert "LONGVARCHAR" in out
    assert "JSONB" not in out


def test_strips_gen_random_uuid_default():
    b = DDLBundle(schema_sql="", indexes_sql="", constraints_sql="",
                  tables_sql="CREATE TABLE t (id VARCHAR(36) DEFAULT gen_random_uuid());")
    out = convert_bundle(b)
    assert "gen_random_uuid" not in out


def test_preserves_fk_and_index_sections():
    b = DDLBundle(
        schema_sql="CREATE SCHEMA IF NOT EXISTS public;",
        tables_sql="CREATE TABLE public.a (id INT PRIMARY KEY);",
        indexes_sql="CREATE INDEX ix_a_id ON public.a (id);",
        constraints_sql="ALTER TABLE public.a ADD CONSTRAINT chk_a CHECK (id > 0);",
    )
    out = convert_bundle(b)
    assert "CREATE INDEX ix_a_id ON a" in out
    assert "ALTER TABLE a" in out
    assert "CHECK (id > 0)" in out
```

- [ ] **Step 2: Run, verify fail**

```powershell
pytest tests/test_postgres_to_hsqldb.py -v
```
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `scripts/postgres_to_hsqldb.py`**

```python
import re
from ddl_loader import DDLBundle


_SCHEMA_LINE = re.compile(r"(?im)^\s*CREATE\s+SCHEMA\s+[^;]+;\s*$")
_SCHEMA_QUALIFIER = re.compile(r"\bpublic\.")


_TYPE_REWRITES = [
    (re.compile(r"\bBIGSERIAL\b", re.I),                       "BIGINT GENERATED BY DEFAULT AS IDENTITY"),
    (re.compile(r"\bSERIAL\b",    re.I),                       "INTEGER GENERATED BY DEFAULT AS IDENTITY"),
    (re.compile(r"\bTIMESTAMP\s+WITH\s+TIME\s+ZONE\b", re.I),  "TIMESTAMP"),
    (re.compile(r"\bTIMESTAMPTZ\b", re.I),                     "TIMESTAMP"),
    (re.compile(r"\bNUMERIC\b", re.I),                         "DECIMAL"),
    (re.compile(r"\bJSONB\b", re.I),                           "LONGVARCHAR"),
    (re.compile(r"\bTEXT\b", re.I),                            "LONGVARCHAR"),
]

_DEFAULT_UUID = re.compile(r"\s*DEFAULT\s+gen_random_uuid\(\)", re.I)


def _strip_schema(sql: str) -> str:
    sql = _SCHEMA_LINE.sub("", sql)
    return _SCHEMA_QUALIFIER.sub("", sql)


def _rewrite_types(sql: str) -> str:
    for pat, repl in _TYPE_REWRITES:
        sql = pat.sub(repl, sql)
    sql = _DEFAULT_UUID.sub("", sql)
    return sql


def _section(title: str, body: str) -> str:
    body = body.strip()
    if not body:
        return ""
    return f"-- {title}\n{body}\n"


def convert_bundle(bundle: DDLBundle) -> str:
    parts = []
    parts.append("-- Generated from db/migrations/V001~V004 (postgres -> hsqldb)\n")
    for title, raw in [
        ("V002 tables",      bundle.tables_sql),
        ("V003 indexes",     bundle.indexes_sql),
        ("V004 constraints", bundle.constraints_sql),
    ]:
        converted = _rewrite_types(_strip_schema(raw))
        parts.append(_section(title, converted))
    return "\n".join(p for p in parts if p)


def convert_seed_files(seed_files: list) -> str:
    chunks = ["-- Generated from db/seed/* (postgres -> hsqldb)\n"]
    for p in seed_files:
        chunks.append(f"-- {p.name}\n")
        chunks.append(_rewrite_types(_strip_schema(p.read_text(encoding='utf-8'))).strip() + "\n")
    return "\n".join(chunks)
```

- [ ] **Step 4: Run, verify pass**

```powershell
pytest tests/test_postgres_to_hsqldb.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```powershell
git add scripts/postgres_to_hsqldb.py tests/test_postgres_to_hsqldb.py
git commit -m "feat: postgres_to_hsqldb dialect converter"
```

---

## Task 11: Template — domain/entity.java.j2

**Files:**
- Create: `.claude/skills/karpathy-rdb-mybatis/templates/domain/entity.java.j2`

- [ ] **Step 1: Write the template**

```jinja
package {{ base_package }}.domain;

import {{ base_package }}.jakarta.core.data.NexacroBase;

public class {{ pascal }} extends NexacroBase {

{% for f in fields %}
    private {{ f.java_type }} {{ f.field }};
{% endfor %}

{% for f in fields %}
    public {{ f.java_type }} {{ f.getter }}() { return {{ f.field }}; }
    public void {{ f.setter }}({{ f.java_type }} {{ f.field }}) { this.{{ f.field }} = {{ f.field }}; }

{% endfor %}
}
```

- [ ] **Step 2: Commit**

```powershell
git add .claude/skills/karpathy-rdb-mybatis/templates/domain/entity.java.j2
git commit -m "feat: domain entity Jinja template"
```

---

## Task 12: Template — mapper interface + mapper xml

**Files:**
- Create: `.claude/skills/karpathy-rdb-mybatis/templates/mapper/mapper-interface.java.j2`
- Create: `.claude/skills/karpathy-rdb-mybatis/templates/mapper/mapper.xml.j2`

- [ ] **Step 1: Write `mapper-interface.java.j2`**

```jinja
package {{ base_package }}.mapper;

import java.util.List;
import java.util.Map;

public interface {{ pascal }}Mapper {
    List<Map<String, Object>> select_{{ entity_name }}_datalist_map(Map<String, String> searchMap);
    void insert_{{ entity_name }}_map(Map<String, Object> {{ entity_name }});
    void update_{{ entity_name }}_map(Map<String, Object> {{ entity_name }});
    void delete_{{ entity_name }}_map(Map<String, Object> {{ entity_name }});
}
```

- [ ] **Step 2: Write `mapper.xml.j2`**

```jinja
<?xml version="1.0" encoding="UTF-8" ?>
<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN"
        "http://mybatis.org/dtd/mybatis-3-mapper.dtd">
<mapper namespace="{{ mapper_fqcn }}">

  <select id="select_{{ entity_name }}_datalist_map" parameterType="java.util.Map"
          resultType="java.util.Map">
    SELECT {{ mapper_columns.all_upper | join(", ") }}
      FROM {{ table }}
     WHERE 1=1
{% for pred in search_predicates %}
    {{ pred }}
{% endfor %}
  </select>

  <insert id="insert_{{ entity_name }}_map" parameterType="java.util.Map">
    INSERT INTO {{ table }} ({{ mapper_columns.all_upper | join(", ") }})
    VALUES ({% for c in mapper_columns.all_upper %}#{{ '{' }}{{ c }}{{ '}' }}{% if not loop.last %}, {% endif %}{% endfor %})
  </insert>

  <update id="update_{{ entity_name }}_map" parameterType="java.util.Map">
    UPDATE {{ table }}
       SET {% for c in mapper_columns.non_pk_upper %}{{ c }} = #{{ '{' }}{{ c }}{{ '}' }}{% if not loop.last %},
           {% endif %}{% endfor %}
     WHERE {% for c in mapper_columns.pk_upper %}{{ c }} = #{{ '{' }}{{ c }}{{ '}' }}{% if not loop.last %} AND {% endif %}{% endfor %}
  </update>

  <delete id="delete_{{ entity_name }}_map" parameterType="java.util.Map">
    DELETE FROM {{ table }} WHERE {% for c in mapper_columns.pk_upper %}{{ c }} = #{{ '{' }}{{ c }}{{ '}' }}{% if not loop.last %} AND {% endif %}{% endfor %}
  </delete>

</mapper>
```

- [ ] **Step 3: Commit each file**

```powershell
git add .claude/skills/karpathy-rdb-mybatis/templates/mapper/mapper-interface.java.j2
git commit -m "feat: mapper interface Jinja template"
git add .claude/skills/karpathy-rdb-mybatis/templates/mapper/mapper.xml.j2
git commit -m "feat: mapper xml Jinja template"
```

---

## Task 13: Template — service interface + impl

**Files:**
- Create: `.claude/skills/karpathy-rdb-mybatis/templates/service/service-interface.java.j2`
- Create: `.claude/skills/karpathy-rdb-mybatis/templates/service/service-impl.java.j2`

- [ ] **Step 1: Write `service-interface.java.j2`**

```jinja
package {{ base_package }}.service;

import java.util.List;
import java.util.Map;

public interface {{ pascal }}Service {
    List<Map<String, Object>> select_{{ entity_name }}_datalist_map(Map<String, String> searchMap);
    void save_{{ entity_name }}_datalist_map(List<Map<String, Object>> dataList);
}
```

- [ ] **Step 2: Write `service-impl.java.j2`**

```jinja
package {{ base_package }}.service.impl;

import java.util.List;
import java.util.Map;

import org.mybatis.spring.SqlSessionTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.nexacro.java.xapi.data.DataSet;
import {{ base_package }}.jakarta.core.data.DataSetRowTypeAccessor;
import {{ base_package }}.mapper.{{ pascal }}Mapper;
import {{ base_package }}.service.{{ pascal }}Service;

@Service("{{ camel }}Service")
public class {{ pascal }}ServiceImpl implements {{ pascal }}Service {

    @Autowired
    private SqlSessionTemplate sqlSession;

    @Override
    @Transactional(readOnly = true)
    public List<Map<String, Object>> select_{{ entity_name }}_datalist_map(Map<String, String> searchMap) {
        {{ pascal }}Mapper mapper = sqlSession.getMapper({{ pascal }}Mapper.class);
        return mapper.select_{{ entity_name }}_datalist_map(searchMap);
    }

    @Override
    @Transactional
    public void save_{{ entity_name }}_datalist_map(List<Map<String, Object>> dataList) {
        {{ pascal }}Mapper mapper = sqlSession.getMapper({{ pascal }}Mapper.class);
        for (Map<String, Object> row : dataList) {
            int rowType = Integer.parseInt(String.valueOf(row.get(DataSetRowTypeAccessor.NAME)));
{% for b in save_branches %}
            {% if loop.first %}if{% else %}else if{% endif %} (rowType == {{ b.row_type_const }}) {
                mapper.{{ b.mapper_method }}(row);
            }
{% endfor %}
        }
    }
}
```

- [ ] **Step 3: Commit each**

```powershell
git add .claude/skills/karpathy-rdb-mybatis/templates/service/service-interface.java.j2
git commit -m "feat: service interface Jinja template"
git add .claude/skills/karpathy-rdb-mybatis/templates/service/service-impl.java.j2
git commit -m "feat: service impl Jinja template with rowType branching"
```

---

## Task 14: Template — controller

**Files:**
- Create: `.claude/skills/karpathy-rdb-mybatis/templates/controller/controller.java.j2`

- [ ] **Step 1: Write `controller.java.j2`**

```jinja
package {{ base_package }}.controller;

import java.util.List;
import java.util.Map;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.RequestMapping;

import {{ base_package }}.jakarta.core.data.NexacroResult;
import {{ base_package }}.jakarta.core.data.ParamDataSet;
import {{ base_package }}.jakarta.core.NexacroException;
import {{ base_package }}.service.{{ pascal }}Service;

@Controller
public class {{ pascal }}Controller {

    @Autowired
    private {{ pascal }}Service {{ camel }}Service;

    @RequestMapping(value = "{{ endpoint_base }}/select_datalist_map.do")
    public NexacroResult select_datalist_map(
            @ParamDataSet(name = "dsSearch", required = false) Map<String, String> searchMap)
            throws NexacroException {
        List<Map<String, Object>> list = {{ camel }}Service.select_{{ entity_name }}_datalist_map(searchMap);
        NexacroResult result = new NexacroResult();
        result.addDataSet("output1", list);
        return result;
    }

    @RequestMapping(value = "{{ endpoint_base }}/save_datalist_map.do")
    public NexacroResult save_datalist_map(
            @ParamDataSet(name = "dataList") List<Map<String, Object>> dataList)
            throws NexacroException {
        {{ camel }}Service.save_{{ entity_name }}_datalist_map(dataList);
        return new NexacroResult();
    }
}
```

- [ ] **Step 2: Commit**

```powershell
git add .claude/skills/karpathy-rdb-mybatis/templates/controller/controller.java.j2
git commit -m "feat: controller Jinja template"
```

---

## Task 15: Template — schema.sql + data.sql wrappers

**Files:**
- Create: `.claude/skills/karpathy-rdb-mybatis/templates/ddl/schema.sql.j2`
- Create: `.claude/skills/karpathy-rdb-mybatis/templates/ddl/data.sql.j2`

- [ ] **Step 1: Write `schema.sql.j2`**

```jinja
-- schema.sql (HSQLDB)
-- Generated by /karpathy-rdb-mybatis from db/migrations/V001~V004

{{ converted_sql }}
```

- [ ] **Step 2: Write `data.sql.j2`**

```jinja
-- data.sql (HSQLDB)
-- Generated by /karpathy-rdb-mybatis from db/seed/

{{ converted_seed }}
```

- [ ] **Step 3: Commit each**

```powershell
git add .claude/skills/karpathy-rdb-mybatis/templates/ddl/schema.sql.j2
git commit -m "feat: schema.sql Jinja wrapper template"
git add .claude/skills/karpathy-rdb-mybatis/templates/ddl/data.sql.j2
git commit -m "feat: data.sql Jinja wrapper template"
```

---

## Task 16: codegen — render single entity

**Files:**
- Create: `scripts/codegen.py`
- Create: `tests/test_codegen.py`

- [ ] **Step 1: Write failing test `tests/test_codegen.py`**

```python
import pathlib
from codegen import render_entity_files

ENTITY = {
    "name": "customer",
    "table": "TB_CUSTOMER",
    "columns": [
        {"name": "customer_id", "type": "varchar(36)", "pk": True},
        {"name": "name",        "type": "varchar(100)"},
        {"name": "email",       "type": "varchar(200)"},
        {"name": "status",      "type": "varchar(20)"},
    ],
}


def test_render_entity_files_writes_six_files(tmp_path):
    out = tmp_path / "backend"
    paths = render_entity_files(out, ENTITY, base_package="com.nexacro.uiadapter")
    assert (out / "src/main/java/com/nexacro/uiadapter/domain/Customer.java").exists()
    assert (out / "src/main/java/com/nexacro/uiadapter/mapper/CustomerMapper.java").exists()
    assert (out / "src/main/resources/mybatis/mapper/CustomerMapper.xml").exists()
    assert (out / "src/main/java/com/nexacro/uiadapter/service/CustomerService.java").exists()
    assert (out / "src/main/java/com/nexacro/uiadapter/service/impl/CustomerServiceImpl.java").exists()
    assert (out / "src/main/java/com/nexacro/uiadapter/controller/CustomerController.java").exists()
    assert len(paths) == 6


def test_controller_has_expected_endpoints(tmp_path):
    out = tmp_path / "backend"
    render_entity_files(out, ENTITY, base_package="com.nexacro.uiadapter")
    ctrl = (out / "src/main/java/com/nexacro/uiadapter/controller/CustomerController.java").read_text(encoding="utf-8")
    assert "/customer/select_datalist_map.do" in ctrl
    assert "/customer/save_datalist_map.do" in ctrl


def test_mapper_xml_namespace_matches_interface(tmp_path):
    out = tmp_path / "backend"
    render_entity_files(out, ENTITY, base_package="com.nexacro.uiadapter")
    xml = (out / "src/main/resources/mybatis/mapper/CustomerMapper.xml").read_text(encoding="utf-8")
    assert 'namespace="com.nexacro.uiadapter.mapper.CustomerMapper"' in xml


def test_service_impl_has_three_branches(tmp_path):
    out = tmp_path / "backend"
    render_entity_files(out, ENTITY, base_package="com.nexacro.uiadapter")
    impl = (out / "src/main/java/com/nexacro/uiadapter/service/impl/CustomerServiceImpl.java").read_text(encoding="utf-8")
    assert "ROW_TYPE_INSERTED" in impl
    assert "ROW_TYPE_UPDATED" in impl
    assert "ROW_TYPE_DELETED" in impl
    assert "insert_customer_map" in impl
    assert "update_customer_map" in impl
    assert "delete_customer_map" in impl
```

- [ ] **Step 2: Run, verify fail**

```powershell
pytest tests/test_codegen.py -v
```
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `scripts/codegen.py`**

```python
import pathlib
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from precompute import build_entity_context


TEMPLATE_ROOT = pathlib.Path(__file__).resolve().parent.parent / ".claude" / "skills" / "karpathy-rdb-mybatis" / "templates"


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_ROOT)),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )


def _write(path: pathlib.Path, content: str) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def render_entity_files(out_root: pathlib.Path, entity: dict, base_package: str) -> list:
    out_root = pathlib.Path(out_root)
    ctx = build_entity_context(entity, base_package=base_package)
    env = _env()

    pkg_path = base_package.replace(".", "/")
    java_root = out_root / "src" / "main" / "java" / pkg_path
    xml_root  = out_root / "src" / "main" / "resources" / "mybatis" / "mapper"

    written = []
    written.append(_write(java_root / "domain" / f"{ctx['pascal']}.java",
                          env.get_template("domain/entity.java.j2").render(**ctx)))
    written.append(_write(java_root / "mapper" / f"{ctx['pascal']}Mapper.java",
                          env.get_template("mapper/mapper-interface.java.j2").render(**ctx)))
    written.append(_write(xml_root / f"{ctx['pascal']}Mapper.xml",
                          env.get_template("mapper/mapper.xml.j2").render(**ctx)))
    written.append(_write(java_root / "service" / f"{ctx['pascal']}Service.java",
                          env.get_template("service/service-interface.java.j2").render(**ctx)))
    written.append(_write(java_root / "service" / "impl" / f"{ctx['pascal']}ServiceImpl.java",
                          env.get_template("service/service-impl.java.j2").render(**ctx)))
    written.append(_write(java_root / "controller" / f"{ctx['pascal']}Controller.java",
                          env.get_template("controller/controller.java.j2").render(**ctx)))
    return written


def render_schema_sql(out_root: pathlib.Path, converted_sql: str) -> pathlib.Path:
    env = _env()
    text = env.get_template("ddl/schema.sql.j2").render(converted_sql=converted_sql)
    return _write(pathlib.Path(out_root) / "src" / "main" / "resources" / "schema.sql", text)


def render_data_sql(out_root: pathlib.Path, converted_seed: str) -> pathlib.Path:
    env = _env()
    text = env.get_template("ddl/data.sql.j2").render(converted_seed=converted_seed)
    return _write(pathlib.Path(out_root) / "src" / "main" / "resources" / "data.sql", text)
```

- [ ] **Step 4: Run, verify pass**

```powershell
pytest tests/test_codegen.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```powershell
git add scripts/codegen.py tests/test_codegen.py
git commit -m "feat: codegen renderer for per-entity 6 files + schema/data sql"
```

---

## Task 17: codegen — toposort over multi-entity

**Files:**
- Create: `scripts/toposort.py`
- Modify: `tests/test_codegen.py` (append)

- [ ] **Step 1: Append failing test to `tests/test_codegen.py`**

```python
from toposort import topo_sort


def test_topo_sort_fk_aware():
    entities = [
        {"name": "address", "table": "TB_ADDRESS", "columns": [{"name": "address_id", "pk": True}]},
        {"name": "customer", "table": "TB_CUSTOMER", "columns": [{"name": "customer_id", "pk": True}]},
    ]
    relations = [{"from": "address", "to": "customer", "fk": "customer_id"}]
    ordered = topo_sort(entities, relations)
    names = [e["name"] for e in ordered]
    # parent (customer) must come before child (address)
    assert names.index("customer") < names.index("address")
```

- [ ] **Step 2: Run, verify fail**

```powershell
pytest tests/test_codegen.py::test_topo_sort_fk_aware -v
```
Expected: `ModuleNotFoundError: No module named 'toposort'`.

- [ ] **Step 3: Implement `scripts/toposort.py`**

```python
def topo_sort(entities: list, relations: list) -> list:
    by_name = {e["name"]: e for e in entities}
    indeg = {n: 0 for n in by_name}
    edges = {n: [] for n in by_name}
    for r in relations or []:
        src, dst = r.get("from"), r.get("to")
        if src in by_name and dst in by_name and src != dst:
            edges[dst].append(src)
            indeg[src] += 1
    order = [n for n, d in indeg.items() if d == 0]
    out = []
    i = 0
    while i < len(order):
        n = order[i]; i += 1
        out.append(by_name[n])
        for m in edges[n]:
            indeg[m] -= 1
            if indeg[m] == 0:
                order.append(m)
    # any cycle remainder: append in declaration order
    remaining = [e for e in entities if e["name"] not in {x["name"] for x in out}]
    return out + remaining
```

- [ ] **Step 4: Run, verify pass**

```powershell
pytest tests/test_codegen.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```powershell
git add scripts/toposort.py tests/test_codegen.py
git commit -m "feat: toposort for FK-aware entity ordering"
```

---

## Task 18: revalidator — mapper XML lint (R005)

**Files:**
- Create: `scripts/revalidator.py`
- Create: `tests/test_revalidator.py`

- [ ] **Step 1: Write failing test `tests/test_revalidator.py`**

```python
import pathlib
import pytest
from revalidator import lint_mapper_xmls, RevalidationError


def _seed_pair(base: pathlib.Path, namespace: str, ids: list, methods: list):
    java = base / "src/main/java/com/nexacro/uiadapter/mapper"
    java.mkdir(parents=True, exist_ok=True)
    iface = "package com.nexacro.uiadapter.mapper;\n\npublic interface CustomerMapper {\n"
    for m in methods:
        iface += f"    void {m}();\n"
    iface += "}\n"
    (java / "CustomerMapper.java").write_text(iface, encoding="utf-8")

    xml_root = base / "src/main/resources/mybatis/mapper"
    xml_root.mkdir(parents=True, exist_ok=True)
    xml = f'<?xml version="1.0"?>\n<mapper namespace="{namespace}">\n'
    for i in ids:
        xml += f'  <select id="{i}"></select>\n'
    xml += "</mapper>\n"
    (xml_root / "CustomerMapper.xml").write_text(xml, encoding="utf-8")


def test_lint_passes_when_aligned(tmp_path):
    _seed_pair(tmp_path,
               namespace="com.nexacro.uiadapter.mapper.CustomerMapper",
               ids=["select_customer_datalist_map", "insert_customer_map"],
               methods=["select_customer_datalist_map", "insert_customer_map"])
    lint_mapper_xmls(tmp_path)  # no raise


def test_lint_fails_on_namespace_mismatch(tmp_path):
    _seed_pair(tmp_path,
               namespace="wrong.ns.CustomerMapper",
               ids=["x"], methods=["x"])
    with pytest.raises(RevalidationError, match="namespace"):
        lint_mapper_xmls(tmp_path)


def test_lint_fails_on_id_method_mismatch(tmp_path):
    _seed_pair(tmp_path,
               namespace="com.nexacro.uiadapter.mapper.CustomerMapper",
               ids=["select_customer_datalist_map"], methods=["insert_customer_map"])
    with pytest.raises(RevalidationError, match="id"):
        lint_mapper_xmls(tmp_path)
```

- [ ] **Step 2: Run, verify fail**

```powershell
pytest tests/test_revalidator.py -v
```
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `scripts/revalidator.py`** (lint portion)

```python
import pathlib
import re
import subprocess
import os


class RevalidationError(Exception):
    pass


_NAMESPACE = re.compile(r'<mapper\s+namespace\s*=\s*"([^"]+)"')
_ID = re.compile(r'<(?:select|insert|update|delete)\s+id\s*=\s*"([^"]+)"')
_IFACE_METHOD = re.compile(r'(?:public\s+)?(?:\w[\w<>,\s\[\]\.]*?)\s+(\w+)\s*\(')


def _java_root(out_root: pathlib.Path) -> pathlib.Path:
    return pathlib.Path(out_root) / "src" / "main" / "java"


def _xml_root(out_root: pathlib.Path) -> pathlib.Path:
    return pathlib.Path(out_root) / "src" / "main" / "resources" / "mybatis" / "mapper"


def _read_methods_from_iface(iface_path: pathlib.Path) -> list:
    txt = iface_path.read_text(encoding="utf-8")
    body = txt[txt.index("{") + 1 : txt.rindex("}")]
    return [m.group(1) for m in _IFACE_METHOD.finditer(body)]


def lint_mapper_xmls(out_root: pathlib.Path) -> None:
    java_root = _java_root(out_root)
    xml_root = _xml_root(out_root)
    if not xml_root.exists():
        raise RevalidationError(f"mapper xml dir missing: {xml_root}")
    for xml in xml_root.glob("*Mapper.xml"):
        text = xml.read_text(encoding="utf-8")
        m = _NAMESPACE.search(text)
        if not m:
            raise RevalidationError(f"{xml.name}: namespace not found")
        ns = m.group(1)
        expected_iface = java_root / pathlib.Path(*ns.split("."))
        expected_iface = expected_iface.with_suffix(".java")
        if not expected_iface.exists():
            raise RevalidationError(f"{xml.name}: namespace {ns} has no matching interface at {expected_iface}")
        ids = set(_ID.findall(text))
        methods = set(_read_methods_from_iface(expected_iface))
        missing_in_iface = ids - methods
        if missing_in_iface:
            raise RevalidationError(f"{xml.name}: id(s) not in interface: {sorted(missing_in_iface)}")
        missing_in_xml = methods - ids
        if missing_in_xml:
            raise RevalidationError(f"{xml.name}: method(s) not in xml: {sorted(missing_in_xml)}")
```

- [ ] **Step 4: Run, verify pass**

```powershell
pytest tests/test_revalidator.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```powershell
git add scripts/revalidator.py tests/test_revalidator.py
git commit -m "feat: revalidator R005 mapper xml lint"
```

---

## Task 19: revalidator — javac compile check (R006)

**Files:**
- Modify: `scripts/revalidator.py`
- Modify: `tests/test_revalidator.py`

- [ ] **Step 1: Append failing test**

```python
def test_javac_skip_when_libs_dir_missing(tmp_path, monkeypatch):
    from revalidator import javac_check, JavacResult
    monkeypatch.delenv("NEXACRO_LIBS_DIR", raising=False)
    result = javac_check(tmp_path)
    assert isinstance(result, JavacResult)
    assert result.skipped is True
    assert "NEXACRO_LIBS_DIR" in result.message


def test_javac_skip_when_no_java_files(tmp_path, monkeypatch):
    from revalidator import javac_check
    monkeypatch.setenv("NEXACRO_LIBS_DIR", str(tmp_path))
    result = javac_check(tmp_path)
    assert result.skipped is True
```

- [ ] **Step 2: Run, verify fail**

```powershell
pytest tests/test_revalidator.py -v
```
Expected: import errors on `javac_check, JavacResult`.

- [ ] **Step 3: Extend `scripts/revalidator.py`**

```python
from dataclasses import dataclass


@dataclass
class JavacResult:
    ok: bool = True
    skipped: bool = False
    message: str = ""
    stderr: str = ""


def javac_check(out_root: pathlib.Path) -> JavacResult:
    libs_env = os.environ.get("NEXACRO_LIBS_DIR")
    if not libs_env:
        return JavacResult(ok=True, skipped=True,
                           message="NEXACRO_LIBS_DIR not set; R006 javac check skipped")
    libs_dir = pathlib.Path(libs_env)
    if not libs_dir.exists():
        return JavacResult(ok=True, skipped=True,
                           message=f"NEXACRO_LIBS_DIR does not exist: {libs_dir}")
    java_files = list(_java_root(out_root).rglob("*.java"))
    if not java_files:
        return JavacResult(ok=True, skipped=True, message="no .java files to compile")
    jars = list(libs_dir.glob("*.jar"))
    cp_sep = ";" if os.name == "nt" else ":"
    cp = cp_sep.join(str(j) for j in jars) if jars else ""
    build_dir = pathlib.Path(out_root) / ".build_check"
    build_dir.mkdir(parents=True, exist_ok=True)
    cmd = ["javac", "-d", str(build_dir)]
    if cp:
        cmd += ["-cp", cp]
    cmd += [str(f) for f in java_files]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return JavacResult(ok=(proc.returncode == 0), skipped=False,
                       message=("javac ok" if proc.returncode == 0 else "javac failed"),
                       stderr=proc.stderr)
```

- [ ] **Step 4: Run, verify pass**

```powershell
pytest tests/test_revalidator.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```powershell
git add scripts/revalidator.py tests/test_revalidator.py
git commit -m "feat: revalidator R006 javac check (skips when libs unset)"
```

---

## Task 20: reporter

**Files:**
- Create: `scripts/reporter.py`
- Create: `tests/test_reporter.py`

- [ ] **Step 1: Write failing test**

```python
import pathlib
from reporter import write_report, ReportInput


def test_report_has_required_sections(tmp_path):
    inp = ReportInput(
        out_root=tmp_path,
        blueprint_path=pathlib.Path("wiki/_blueprint.yaml"),
        ddl_dir=pathlib.Path("db/migrations"),
        project="고객관리",
        entity_count=2,
        generated_files=[tmp_path / "x.java"],
        validation={"R001": "PASS", "R002": "PASS", "R003": "PASS", "R004": "PASS", "R005": "PASS", "R006": "SKIP"},
        ddl_conversions=[("V002__create_tables.sql", "schema.sql §1", "type map: NUMERIC→DECIMAL")],
        endpoints=["/customer/select_datalist_map.do", "/customer/save_datalist_map.do"],
        exit_code=0,
    )
    path = write_report(inp)
    text = path.read_text(encoding="utf-8")
    for section in ["# Stage 3", "Validation", "Generated files", "DDL conversion", "Endpoints", "Exit code: 0"]:
        assert section in text
```

- [ ] **Step 2: Run, verify fail**

```powershell
pytest tests/test_reporter.py -v
```
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `scripts/reporter.py`**

```python
import datetime
import pathlib
from dataclasses import dataclass, field


@dataclass
class ReportInput:
    out_root: pathlib.Path
    blueprint_path: pathlib.Path
    ddl_dir: pathlib.Path
    project: str
    entity_count: int
    generated_files: list = field(default_factory=list)
    validation: dict = field(default_factory=dict)
    ddl_conversions: list = field(default_factory=list)
    endpoints: list = field(default_factory=list)
    exit_code: int = 0
    extra_messages: list = field(default_factory=list)


def write_report(inp: ReportInput) -> pathlib.Path:
    now = datetime.datetime.now().isoformat(timespec="seconds")
    lines = [
        "# Stage 3 — MyBatis/uiadapter Codegen Report",
        "",
        f"- Generated at: {now}",
        f"- Blueprint: {inp.blueprint_path} (project: {inp.project}, entities: {inp.entity_count})",
        f"- DDL source: {inp.ddl_dir}",
        f"- Output: {inp.out_root}",
        f"- Exit code: {inp.exit_code}",
        "",
        "## Validation",
    ]
    for k in ["R001", "R002", "R003", "R004", "R005", "R006"]:
        lines.append(f"- {k}: {inp.validation.get(k, 'N/A')}")
    lines += ["", "## Generated files"]
    for f in inp.generated_files:
        lines.append(f"- {f}")
    lines += ["", "## DDL conversion", "| Source | Target | Notes |", "|---|---|---|"]
    for src, tgt, note in inp.ddl_conversions:
        lines.append(f"| {src} | {tgt} | {note} |")
    lines += ["", "## Endpoints"]
    for ep in inp.endpoints:
        lines.append(f"- POST {ep}")
    if inp.extra_messages:
        lines += ["", "## Notes"]
        for m in inp.extra_messages:
            lines.append(f"- {m}")
    path = pathlib.Path(inp.out_root) / "mybatis-report.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
```

- [ ] **Step 4: Run, verify pass**

```powershell
pytest tests/test_reporter.py -v
```
Expected: 1 passed.

- [ ] **Step 5: Commit**

```powershell
git add scripts/reporter.py tests/test_reporter.py
git commit -m "feat: reporter for mybatis-report.md"
```

---

## Task 21: ddl writing — wire converter + writer

**Files:**
- Modify: `tests/test_codegen.py` (append)

This adds an integration test that the schema.sql wrapper template plus converter actually emits a valid combined file.

- [ ] **Step 1: Append failing test**

```python
from codegen import render_schema_sql
from ddl_loader import DDLBundle
from postgres_to_hsqldb import convert_bundle


def test_render_schema_sql_writes_to_resources(tmp_path):
    bundle = DDLBundle(
        schema_sql="CREATE SCHEMA IF NOT EXISTS public;",
        tables_sql="CREATE TABLE public.TB_X (ID INT PRIMARY KEY);",
        indexes_sql="",
        constraints_sql="",
    )
    converted = convert_bundle(bundle)
    path = render_schema_sql(tmp_path / "backend", converted)
    text = path.read_text(encoding="utf-8")
    assert "schema.sql (HSQLDB)" in text
    assert "CREATE TABLE TB_X" in text
    assert "CREATE SCHEMA" not in text
```

- [ ] **Step 2: Run, verify pass**

```powershell
pytest tests/test_codegen.py -v
```
Expected: passes (codegen already exposes `render_schema_sql`).

- [ ] **Step 3: Commit**

```powershell
git add tests/test_codegen.py
git commit -m "test: integration test for render_schema_sql + converter"
```

---

## Task 22: compile.py CLI

**Files:**
- Create: `scripts/compile.py`
- Create: `tests/test_compile_cli.py`

- [ ] **Step 1: Write failing test `tests/test_compile_cli.py`**

```python
import os
import pathlib
import subprocess
import sys
import shutil


PLUGIN_ROOT = pathlib.Path(__file__).resolve().parent.parent
FIXTURE_BP = PLUGIN_ROOT / "tests" / "fixtures" / "golden_blueprint"
FIXTURE_DDL = PLUGIN_ROOT / "tests" / "fixtures" / "golden_ddl"


def _project_dir(tmp_path: pathlib.Path) -> pathlib.Path:
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    shutil.copy(FIXTURE_BP / "_blueprint.yaml", wiki / "_blueprint.yaml")
    db = tmp_path / "db" / "migrations"
    db.mkdir(parents=True)
    for f in FIXTURE_DDL.glob("V0*.sql"):
        shutil.copy(f, db / f.name)
    return tmp_path


def _run_compile(cwd: pathlib.Path, *args, env_extra=None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PLUGIN_ROOT / "scripts")
    if env_extra:
        env.update(env_extra)
    cmd = [sys.executable, str(PLUGIN_ROOT / "scripts" / "compile.py"), *args]
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env)


def test_compile_success_skip_javac(tmp_path):
    proj = _project_dir(tmp_path)
    cp = _run_compile(proj, "compile", "--skip-compile")
    assert cp.returncode == 0, cp.stderr
    out = proj / "backend"
    assert (out / "src/main/java/com/nexacro/uiadapter/controller/CustomerController.java").exists()
    assert (out / "src/main/resources/schema.sql").exists()
    assert (out / "mybatis-report.md").exists()


def test_compile_exits_1_on_bad_blueprint(tmp_path):
    proj = _project_dir(tmp_path)
    (proj / "wiki" / "_blueprint.yaml").write_text(
        "version: 1\nproject: x\nentities: []\nrelations: []\nbusiness_rules: []\nvalidation: {passed: false}\n",
        encoding="utf-8",
    )
    cp = _run_compile(proj, "compile", "--skip-compile")
    assert cp.returncode == 1
    assert "validation.passed" in (cp.stdout + cp.stderr)


def test_compile_dry_run_writes_no_code(tmp_path):
    proj = _project_dir(tmp_path)
    cp = _run_compile(proj, "compile", "--dry-run")
    assert cp.returncode == 0
    out = proj / "backend"
    assert (out / "mybatis-report.md").exists()
    assert not (out / "src/main/java/com/nexacro/uiadapter/controller/CustomerController.java").exists()
```

- [ ] **Step 2: Run, verify fail**

```powershell
pytest tests/test_compile_cli.py -v
```
Expected: compile.py does not exist; either FileNotFoundError or non-zero return.

- [ ] **Step 3: Implement `scripts/compile.py`**

```python
import argparse
import pathlib
import sys

from blueprint_loader import load as load_blueprint, BlueprintError
from ddl_loader import load as load_ddl, DDLBundleError
from column_classifier import validate_pk_coverage, ColumnClassifierError
from toposort import topo_sort
from postgres_to_hsqldb import convert_bundle, convert_seed_files
from codegen import render_entity_files, render_schema_sql, render_data_sql
from revalidator import lint_mapper_xmls, javac_check, RevalidationError
from reporter import write_report, ReportInput


def _parse_args(argv):
    p = argparse.ArgumentParser(prog="karpathy-rdb-mybatis")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("compile")
    c.add_argument("--blueprint", default="wiki/_blueprint.yaml")
    c.add_argument("--ddl-dir",   default="db/migrations")
    c.add_argument("--seed-dir",  default="db/seed")
    c.add_argument("--out",       default="backend")
    c.add_argument("--package",   default="com.nexacro.uiadapter")
    c.add_argument("--table-prefix", default="TB_")
    c.add_argument("--skip-compile", action="store_true")
    c.add_argument("--dry-run",   action="store_true")
    return p.parse_args(argv)


def _check_table_prefix(entities, prefix):
    bad = [e["name"] for e in entities if not e.get("table", "").startswith(prefix)]
    return bad


def main(argv=None):
    args = _parse_args(argv or sys.argv[1:])
    if args.cmd != "compile":
        print(f"unknown command: {args.cmd}", file=sys.stderr)
        return 1

    validation = {}
    extra = []
    try:
        bp = load_blueprint(args.blueprint)
        validation["R001"] = "PASS"
        validation["R002"] = "PASS"
    except BlueprintError as e:
        msg = str(e)
        validation["R001"] = "PASS" if "version" not in msg else "FAIL"
        validation["R002"] = "FAIL" if "validation.passed" in msg else validation.get("R002", "N/A")
        print(f"[R001/R002] {msg}", file=sys.stderr)
        _emit_partial_report(args, validation, exit_code=1, extra=[msg])
        return 1

    try:
        seed_dir = pathlib.Path(args.seed_dir)
        ddl = load_ddl(args.ddl_dir, seed_dir=seed_dir if seed_dir.exists() else None)
        validation["R003"] = "PASS"
    except DDLBundleError as e:
        validation["R003"] = "FAIL"
        print(f"[R003] {e}", file=sys.stderr)
        _emit_partial_report(args, validation, exit_code=1, extra=[str(e)])
        return 1

    try:
        validate_pk_coverage(bp["entities"])
        validation["R004"] = "PASS"
    except ColumnClassifierError as e:
        validation["R004"] = "FAIL"
        print(f"[R004] {e}", file=sys.stderr)
        _emit_partial_report(args, validation, exit_code=1, extra=[str(e)])
        return 1

    prefix_warnings = _check_table_prefix(bp["entities"], args.table_prefix)
    if prefix_warnings:
        extra.append(f"table-prefix warning: {prefix_warnings} do not start with {args.table_prefix}")

    sorted_entities = topo_sort(bp["entities"], bp.get("relations") or [])

    out_root = pathlib.Path(args.out)
    generated = []
    endpoints = []

    if args.dry_run:
        validation.setdefault("R005", "SKIP")
        validation.setdefault("R006", "SKIP")
        for e in sorted_entities:
            endpoints.append(f"/{e['name']}/select_datalist_map.do")
            endpoints.append(f"/{e['name']}/save_datalist_map.do")
        _emit_full_report(args, validation, generated, endpoints, exit_code=0, extra=extra + ["dry-run mode"])
        return 0

    converted_sql = convert_bundle(ddl)
    generated.append(render_schema_sql(out_root, converted_sql))
    if ddl.seed_files:
        converted_seed = convert_seed_files(ddl.seed_files)
        generated.append(render_data_sql(out_root, converted_seed))

    for e in sorted_entities:
        generated.extend(render_entity_files(out_root, e, base_package=args.package))
        endpoints.append(f"/{e['name']}/select_datalist_map.do")
        endpoints.append(f"/{e['name']}/save_datalist_map.do")

    exit_code = 0
    try:
        lint_mapper_xmls(out_root)
        validation["R005"] = "PASS"
    except RevalidationError as e:
        validation["R005"] = "FAIL"
        extra.append(f"R005: {e}")
        exit_code = 2

    if args.skip_compile:
        validation["R006"] = "SKIP"
    else:
        jr = javac_check(out_root)
        if jr.skipped:
            validation["R006"] = "SKIP"
            extra.append(jr.message)
        elif jr.ok:
            validation["R006"] = "PASS"
        else:
            validation["R006"] = "FAIL"
            extra.append("javac stderr:\n" + jr.stderr)
            exit_code = max(exit_code, 2)

    _emit_full_report(args, validation, generated, endpoints, exit_code=exit_code, extra=extra,
                      project=bp.get("project", ""), entity_count=len(sorted_entities))
    return exit_code


def _emit_partial_report(args, validation, exit_code, extra):
    write_report(ReportInput(
        out_root=pathlib.Path(args.out),
        blueprint_path=pathlib.Path(args.blueprint),
        ddl_dir=pathlib.Path(args.ddl_dir),
        project="(unknown)",
        entity_count=0,
        validation=validation,
        exit_code=exit_code,
        extra_messages=extra,
    ))


def _emit_full_report(args, validation, generated, endpoints, exit_code, extra,
                      project="", entity_count=0):
    ddl_conversions = [
        ("V001__create_schema.sql", "(omitted)",     "HSQLDB has no schema concept"),
        ("V002__create_tables.sql", "schema.sql §1", "type map applied"),
        ("V003__create_indexes.sql", "schema.sql §2", "as-is after schema strip"),
        ("V004__create_constraints.sql", "schema.sql §3", "FK + CHECK preserved"),
    ]
    write_report(ReportInput(
        out_root=pathlib.Path(args.out),
        blueprint_path=pathlib.Path(args.blueprint),
        ddl_dir=pathlib.Path(args.ddl_dir),
        project=project,
        entity_count=entity_count,
        generated_files=generated,
        validation=validation,
        ddl_conversions=ddl_conversions,
        endpoints=endpoints,
        exit_code=exit_code,
        extra_messages=extra,
    ))


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run, verify pass**

```powershell
pytest tests/test_compile_cli.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```powershell
git add scripts/compile.py tests/test_compile_cli.py
git commit -m "feat: compile.py CLI orchestrator with validation + report"
```

---

## Task 23: Slash command wiring smoke

**Files:**
- Modify: `.claude/commands/karpathy-rdb-mybatis.md` (no change needed if Task 1 final, but verify)

- [ ] **Step 1: Verify slash command file exists and references compile.py**

```powershell
Get-Content .claude/commands/karpathy-rdb-mybatis.md
```
Expected output includes `python scripts/compile.py $ARGUMENTS`.

- [ ] **Step 2: Smoke run from a scratch project**

```powershell
$P = "$env:TEMP\stage3_smoke"
Remove-Item -Recurse -Force $P -ErrorAction SilentlyContinue
New-Item -ItemType Directory $P | Out-Null
Copy-Item -Recurse tests/fixtures/golden_blueprint $P/wiki
Copy-Item -Recurse tests/fixtures/golden_ddl $P/db/migrations
$env:PYTHONPATH = "$PWD/scripts"
python scripts/compile.py compile --blueprint $P/wiki/_blueprint.yaml --ddl-dir $P/db/migrations --out $P/backend --skip-compile
```
Expected: exit 0; `$P/backend/mybatis-report.md` and Java files present.

- [ ] **Step 3: Commit (only if file changed; otherwise skip)**

```powershell
git status
```
No commit needed if nothing changed.

---

## Task 24: Golden path E2E test

**Files:**
- Create: `tests/test_golden_path.py`
- Create: `tests/fixtures/expected_output/` (filled on first successful run)

- [ ] **Step 1: Write failing test**

```python
import pathlib
import shutil
import subprocess
import sys
import os

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parent.parent
FIXTURE_BP = PLUGIN_ROOT / "tests" / "fixtures" / "golden_blueprint"
FIXTURE_DDL = PLUGIN_ROOT / "tests" / "fixtures" / "golden_ddl"
EXPECTED = PLUGIN_ROOT / "tests" / "fixtures" / "expected_output"


def _run(tmp_path):
    proj = tmp_path / "proj"
    (proj / "wiki").mkdir(parents=True)
    shutil.copy(FIXTURE_BP / "_blueprint.yaml", proj / "wiki" / "_blueprint.yaml")
    (proj / "db" / "migrations").mkdir(parents=True)
    for f in FIXTURE_DDL.glob("V0*.sql"):
        shutil.copy(f, proj / "db" / "migrations" / f.name)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PLUGIN_ROOT / "scripts")
    cp = subprocess.run(
        [sys.executable, str(PLUGIN_ROOT / "scripts" / "compile.py"),
         "compile", "--skip-compile"],
        cwd=proj, capture_output=True, text=True, env=env,
    )
    assert cp.returncode == 0, cp.stderr
    return proj / "backend"


def _normalize(s: str) -> str:
    return "\n".join(line.rstrip() for line in s.splitlines() if line.strip()) + "\n"


def test_golden_files_match_snapshot(tmp_path):
    out = _run(tmp_path)
    if not EXPECTED.exists():
        # bootstrap: copy and fail with a hint, run once to lock
        EXPECTED.mkdir(parents=True)
        for f in out.rglob("*"):
            if f.is_file() and f.name != "mybatis-report.md":
                rel = f.relative_to(out)
                dest = EXPECTED / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(f, dest)
        raise AssertionError("expected_output bootstrapped — review and commit, then re-run")

    diffs = []
    for f in EXPECTED.rglob("*"):
        if not f.is_file():
            continue
        rel = f.relative_to(EXPECTED)
        actual = out / rel
        if not actual.exists():
            diffs.append(f"missing: {rel}")
            continue
        if _normalize(actual.read_text(encoding="utf-8")) != _normalize(f.read_text(encoding="utf-8")):
            diffs.append(f"mismatch: {rel}")
    assert not diffs, "snapshot drift:\n" + "\n".join(diffs)
```

- [ ] **Step 2: First run (bootstrap mode)**

```powershell
pytest tests/test_golden_path.py -v
```
Expected: AssertionError "bootstrapped — review and commit".

- [ ] **Step 3: Inspect `tests/fixtures/expected_output/` and confirm contents look correct**

```powershell
Get-ChildItem -Recurse tests/fixtures/expected_output
Get-Content tests/fixtures/expected_output/src/main/java/com/nexacro/uiadapter/controller/CustomerController.java
```
Confirm output matches the spec section 3 examples.

- [ ] **Step 4: Re-run, verify pass**

```powershell
pytest tests/test_golden_path.py -v
pytest -v
```
Expected: golden path passes; full suite green.

- [ ] **Step 5: Commit**

```powershell
git add tests/fixtures/expected_output tests/test_golden_path.py
git commit -m "test: golden path E2E with snapshot fixtures"
```

---

## Task 25: README + INSTALL-FOR-AI

**Files:**
- Create: `README.md`
- Create: `INSTALL-FOR-AI.md`

- [ ] **Step 1: Write `README.md`**

```markdown
# andrej-karpathy-rdb-mybatis

Stage 3 of the **business-fullstack-creater** pipeline.

```
Stage 1 (rdb-skill) → Stage 2 (rdb-ddl) → **Stage 3 (this)** → Stage 4 (nexacro-claude-skills)
```

Generates a complete MyBatis + nexacro uiadapter `backend/` from a Stage 1 `_blueprint.yaml` and Stage 2 V001~V004 PostgreSQL DDL.

## Install

```bash
/plugin marketplace add D:\AI\workspace\andrej-karpathy-rdb-mybatis
/plugin install andrej-karpathy-rdb-mybatis
```

## Usage

```bash
/karpathy-rdb-mybatis compile \
  --blueprint wiki/_blueprint.yaml \
  --ddl-dir db/migrations \
  --out backend/
```

Optional:
- `--package com.nexacro.uiadapter` (default)
- `--skip-compile` — skip R006 javac check
- `--dry-run` — write report only, no code

## What it generates (per entity)

| Path | Purpose |
|---|---|
| `src/main/java/.../controller/<Entity>Controller.java` | `select_datalist_map.do`, `save_datalist_map.do` |
| `src/main/java/.../service/<Entity>Service.java` | interface |
| `src/main/java/.../service/impl/<Entity>ServiceImpl.java` | `@Transactional`, rowType dispatch |
| `src/main/java/.../mapper/<Entity>Mapper.java` | MyBatis interface |
| `src/main/resources/mybatis/mapper/<Entity>Mapper.xml` | CRUD + dynamic search |
| `src/main/java/.../domain/<Entity>.java` | Plain POJO extends NexacroBase |

Plus:
- `src/main/resources/schema.sql` — HSQLDB DDL (V001~V004 converted)
- `src/main/resources/data.sql` — seed (optional)
- `mybatis-report.md` — validation + file inventory

## Validation

| Rule | Check | On fail |
|---|---|---|
| R001 | blueprint version == 1 | exit 1 |
| R002 | validation.passed == true | exit 1 |
| R003 | V001~V004 present | exit 1 |
| R004 | every entity has PK | exit 1 |
| R005 | mapper xml namespace + id alignment | exit 2 (artifacts preserved) |
| R006 | javac compile clean (requires `NEXACRO_LIBS_DIR`) | exit 2 (artifacts preserved) |

## Development

```bash
python -m pip install -e .[dev]
pytest -v
```
```

- [ ] **Step 2: Write `INSTALL-FOR-AI.md`**

```markdown
# Install instructions for AI agents

Goal: install this plugin into Claude Code from a local path.

## Steps

1. Add the marketplace pointing to the repo root:
   ```
   /plugin marketplace add D:\AI\workspace\andrej-karpathy-rdb-mybatis
   ```

2. Install the plugin:
   ```
   /plugin install andrej-karpathy-rdb-mybatis
   ```

3. Verify the slash command appears:
   ```
   /karpathy-rdb-mybatis compile --help
   ```

4. Run on a project that already has Stage 1 + Stage 2 outputs:
   - `wiki/_blueprint.yaml` (Stage 1)
   - `db/migrations/V001__create_schema.sql`, `V002__create_tables.sql`, `V003__create_indexes.sql`, `V004__create_constraints.sql` (Stage 2)
   - optional `db/seed/*.sql`

   Then:
   ```
   /karpathy-rdb-mybatis compile --skip-compile
   ```

5. Check `backend/mybatis-report.md` for validation results.

## Optional javac check

Set `NEXACRO_LIBS_DIR` to a directory containing:
- `nexacro-uiadapter-*.jar`
- `mybatis-spring-*.jar`
- `mybatis-*.jar`
- `spring-context-*.jar`, `spring-tx-*.jar`, `spring-web-*.jar`

Then run without `--skip-compile`.
```

- [ ] **Step 3: Commit each**

```powershell
git add README.md
git commit -m "docs: README for andrej-karpathy-rdb-mybatis"
git add INSTALL-FOR-AI.md
git commit -m "docs: install instructions for AI agents"
```

---

## Task 26: Final smoke + tag v0.1.0

- [ ] **Step 1: Full test suite green**

```powershell
pytest -v
```
Expected: all tests in `tests/` pass. Note the total count.

- [ ] **Step 2: End-to-end smoke from a clean temp project**

```powershell
$P = "$env:TEMP\stage3_release_smoke"
Remove-Item -Recurse -Force $P -ErrorAction SilentlyContinue
New-Item -ItemType Directory $P, "$P/wiki", "$P/db/migrations" | Out-Null
Copy-Item tests/fixtures/golden_blueprint/_blueprint.yaml $P/wiki/
Copy-Item tests/fixtures/golden_ddl/V0*.sql $P/db/migrations/
$env:PYTHONPATH = "$PWD/scripts"
python scripts/compile.py compile --blueprint $P/wiki/_blueprint.yaml --ddl-dir $P/db/migrations --out $P/backend --skip-compile
Get-Content $P/backend/mybatis-report.md
```
Expected: exit 0; report shows `R001~R005 PASS`, `R006 SKIP`.

- [ ] **Step 3: Verify no uncommitted changes**

```powershell
git status
```
Expected: clean.

- [ ] **Step 4: Tag the release**

```powershell
git tag -a v0.1.0 -m "andrej-karpathy-rdb-mybatis v0.1.0 — Stage 3 codegen GA"
git tag --list
```
Expected: `v0.1.0` listed.

- [ ] **Step 5: Update business-fullstack-creater needs doc**

Modify `D:\AI\workspace\business-fullstack-creater\needs\business-fullstack-creater 플러그인 요구기능.md`:
add a row to the "진행 상태" table:

```markdown
| 3 | `andrej-karpathy-rdb-mybatis` | ✅ 완료 (v0.1.0) — `D:\AI\workspace\andrej-karpathy-rdb-mybatis` |
```

Commit (in the business-fullstack-creater repo, not the plugin repo):

```powershell
cd D:\AI\workspace\business-fullstack-creater
git add needs/business-fullstack-creater\ 플러그인\ 요구기능.md
git commit -m "docs: mark Stage 3 (rdb-mybatis) v0.1.0 complete"
```

---

## Done criteria

All of:
- Tasks 1–26 checkboxes complete
- `pytest -v` is fully green inside `D:\AI\workspace\andrej-karpathy-rdb-mybatis\`
- `v0.1.0` tag present
- `mybatis-report.md` from a clean golden run shows R001–R005 PASS, R006 SKIP/PASS
- business-fullstack-creater status doc reflects Stage 3 completion

---

## Self-Review (run before execution)

**Spec coverage check:**
- D1 plugin name + location → Task 1
- D2 4.2 canonical package → Task 16 (`pkg_path = base_package.replace(".", "/")`) and templates 11–14
- D3 Plain POJO + NexacroBase + search fields → Task 9 `_SEARCH_FIELDS` + Task 11 template
- D4 endpoint URLs → Task 14 controller template
- D5 Map-based search → Task 12 mapper, Task 13 service, Task 14 controller
- D6 all-column dynamic equality → Task 8 `build_search_predicates`, Task 12 mapper XML
- D7 `@Transactional` on save, `readOnly=true` on select → Task 13 service-impl template
- D8 HSQLDB schema.sql/data.sql → Task 10 converter + Task 15 wrappers + Task 16 `render_schema_sql`
- D9 JPA Entity excluded → no JPA template anywhere; Plain POJO only (Task 11)
- D10 CLI `/karpathy-rdb-mybatis compile` + flags → Task 1 command file + Task 22 argparse
- D11 snapshot + javac → Task 24 golden path + Task 19 javac

**Validation rules:**
- R001 → Task 3 `blueprint_loader.load` version gate
- R002 → Task 3 `blueprint_loader.load` validation.passed gate
- R003 → Task 4 `ddl_loader.load` REQUIRED check
- R004 → Task 6 `validate_pk_coverage`
- R005 → Task 18 `lint_mapper_xmls`
- R006 → Task 19 `javac_check`

**Exit codes:**
- 0 success → Task 22 default
- 1 input contract → Task 22 BlueprintError/DDLBundleError/ColumnClassifierError branches
- 2 post-gen failure (preserve artifacts) → Task 22 R005/R006 paths (no cleanup)
- 3 IO/render exception → not yet explicitly handled; argparse + Jinja errors will propagate as code 1 from Python. Acceptable for v0.1.0; document in README that any template render exception is treated as code 1 (matches `python` default exit on uncaught exception). *No new task needed.*

**Placeholder scan:**
- No "TBD"/"TODO" in the plan body.
- Every code step has full code.
- No "similar to Task N" references — code is repeated where needed.

**Type consistency:**
- `blueprint_loader.load → dict`, used in Task 22 ✓
- `ddl_loader.load → DDLBundle`, fed to `convert_bundle` ✓
- `precompute.build_entity_context(entity, base_package=...)` signature matches Task 16 codegen call ✓
- `render_entity_files(out_root, entity, base_package=...) → list[Path]` matches Task 22 usage ✓
- `RevalidationError` raised in Task 18, caught in Task 22 ✓
- `JavacResult(.ok, .skipped, .stderr, .message)` shape matches Task 22 usage ✓

Plan ready for execution.
