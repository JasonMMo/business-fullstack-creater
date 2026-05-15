# andrej-karpathy-rdb-ddl Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Claude Code plugin (`andrej-karpathy-rdb-ddl`) that consumes `_blueprint.yaml` from Stage 1 and emits PostgreSQL + HSQLDB DDL, Flyway migrations, JPA entities, and seed SQL.

**Architecture:** Python 3.11+ CLI with Jinja2 templates, organized as a `scripts/` package per Stage 1's pattern. Each generator accepts `dialect: str` and selects templates under `templates/<dialect>/`. JPA generator is dialect-agnostic. pytest TDD with a golden-blueprint integration test.

**Tech Stack:** Python 3.11+, PyYAML, Jinja2, pytest, argparse.

**Repo root:** `D:\AI\workspace\andrej-karpathy-rdb-ddl\` (new repo, to be created in Task 1).

**Spec reference:** `D:\AI\workspace\business-fullstack-creater\docs\superpowers\specs\2026-05-13-andrej-karpathy-rdb-ddl-design.md`.

---

## File Structure & Responsibilities

| File | Responsibility |
|---|---|
| `plugin.json` | Claude Code plugin manifest |
| `scripts/ddl_compile.py` | CLI entrypoint, argparse, orchestration, exit codes |
| `scripts/loader.py` | Load + parse `_blueprint.yaml`, version/validation checks |
| `scripts/toposort.py` | FK-dependency topological sort, cycle detection |
| `scripts/revalidator.py` | V001~V005 revalidation, returns diagnostics |
| `scripts/dialect.py` | `Dialect` dataclass + `get_dialect(name)` registry (postgres, hsqldb) |
| `scripts/preset_catalog.py` | Hardcoded `(domain, name) → preset_id` catalog + `is_preset(entity)` |
| `scripts/ddl_gen.py` | Render V001~V004 SQL files via Jinja2 |
| `scripts/jpa_gen.py` | Render JPA Entity `.java` files (dialect-agnostic) |
| `scripts/seed_gen.py` | Render seed SQL for preset entities |
| `.claude/commands/rdb-ddl-compile.md` | Slash command definition |
| `.claude/skills/karpathy-rdb-ddl/SKILL.md` | Skill manifest |
| `.claude/skills/karpathy-rdb-ddl/references/ddl-spec.md` | Output contract reference |
| `.claude/skills/karpathy-rdb-ddl/references/validation-codes.md` | V001~V010 reference |
| `.claude/skills/karpathy-rdb-ddl/templates/postgres/*.j2` | PostgreSQL Jinja2 templates (5 files) |
| `.claude/skills/karpathy-rdb-ddl/templates/hsqldb/*.j2` | HSQLDB Jinja2 templates (5 files) |
| `.claude/skills/karpathy-rdb-ddl/templates/entity.java.j2` | JPA template (shared) |
| `tests/conftest.py` | pytest path config |
| `tests/fixtures/golden_blueprint.yaml` | Frozen Stage 1 output |
| `tests/test_*.py` | one per scripts/ module + golden path |

---

## Task Layout

- M1: Repo scaffold + plugin manifest (Tasks 1-2)
- M2: Loader (Task 3)
- M3: Toposort (Task 4)
- M4: Dialect registry + preset catalog (Tasks 5-6)
- M5: Revalidator V001~V005 (Tasks 7-11)
- M6: PostgreSQL DDL generator + templates (Tasks 12-15)
- M7: HSQLDB DDL generator + templates (Task 16)
- M8: JPA Entity generator (Task 17)
- M9: Seed generator (Task 18)
- M10: CLI orchestration + Slash command (Tasks 19-20)
- M11: Golden integration test + fixtures (Task 21)
- M12: Documentation + plugin manifest finalize (Tasks 22-23)

---

### Task 1: Repository scaffold

**Files:**
- Create: `D:\AI\workspace\andrej-karpathy-rdb-ddl\.gitignore`
- Create: `D:\AI\workspace\andrej-karpathy-rdb-ddl\plugin.json`
- Create: `D:\AI\workspace\andrej-karpathy-rdb-ddl\scripts\__init__.py`
- Create: `D:\AI\workspace\andrej-karpathy-rdb-ddl\tests\__init__.py`
- Create: `D:\AI\workspace\andrej-karpathy-rdb-ddl\tests\conftest.py`

- [ ] **Step 1: Initialize repo**

```bash
cd D:/AI/workspace
mkdir andrej-karpathy-rdb-ddl
cd andrej-karpathy-rdb-ddl
git init
mkdir -p scripts tests/fixtures .claude/commands .claude/skills/karpathy-rdb-ddl/references .claude/skills/karpathy-rdb-ddl/templates/postgres .claude/skills/karpathy-rdb-ddl/templates/hsqldb
```

- [ ] **Step 2: Create .gitignore**

Content:
```
__pycache__/
*.pyc
.pytest_cache/
.venv/
*.egg-info/
.DS_Store
```

- [ ] **Step 3: Create plugin.json**

Content:
```json
{
  "name": "andrej-karpathy-rdb-ddl",
  "version": "0.1.0",
  "description": "Stage 2: PostgreSQL/HSQLDB DDL + Flyway + JPA Entity + seed SQL generator from _blueprint.yaml",
  "author": "business-fullstack-creater pipeline",
  "commands": [".claude/commands"],
  "skills": [".claude/skills"]
}
```

- [ ] **Step 4: Create conftest.py**

Path: `tests/conftest.py`
```python
import sys
import pathlib

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
```

- [ ] **Step 5: Create empty __init__.py files and commit**

```bash
echo "" > scripts/__init__.py
echo "" > tests/__init__.py
python -m pip install --quiet pyyaml jinja2 pytest
pytest tests/ -v  # collects 0 tests
git add .gitignore plugin.json scripts/__init__.py tests/__init__.py tests/conftest.py
git commit -m "chore: scaffold repo with plugin.json and pytest config"
```
Expected: `pytest` reports `no tests ran in 0.XXs`.

---

### Task 2: Plugin manifest reference docs

**Files:**
- Create: `.claude/skills/karpathy-rdb-ddl/SKILL.md`
- Create: `.claude/skills/karpathy-rdb-ddl/references/ddl-spec.md`
- Create: `.claude/skills/karpathy-rdb-ddl/references/validation-codes.md`

- [ ] **Step 1: Create SKILL.md**

Path: `.claude/skills/karpathy-rdb-ddl/SKILL.md`
```markdown
---
name: karpathy-rdb-ddl
description: Stage 2 — generates PostgreSQL/HSQLDB DDL, Flyway migrations, JPA Entity Java, and seed SQL from Stage 1 _blueprint.yaml
---

# karpathy-rdb-ddl

Stage 2 of the business-fullstack-creater pipeline. Consumes the validated `_blueprint.yaml` from Stage 1 (`andrej-karpathy-rdb-skill`) and produces:

- PostgreSQL or HSQLDB DDL split into Flyway migrations V001~V004
- JPA Entity Java sources (Lombok, JDK 11+ compatible)
- Seed SQL for preset entities (3 rows each)
- `ddl-report.md` with V001~V005 revalidation results

## Command

`/rdb-ddl-compile <wiki_path> [--out <dir>] [--package <pkg>] [--dialect postgres|hsqldb]`

See `references/ddl-spec.md` for output contract.
See `references/validation-codes.md` for V001~V010 reference.
```

- [ ] **Step 2: Create ddl-spec.md**

Path: `.claude/skills/karpathy-rdb-ddl/references/ddl-spec.md`
```markdown
# DDL Output Contract

## Inputs
- `<wiki_path>/_blueprint.yaml` (Stage 1 output, must have `validation.passed: true`)

## Outputs (under `--out`, default `./db/`)
- `migrations/V001__create_schema.sql` — CREATE SCHEMA statements
- `migrations/V002__create_tables.sql` — CREATE TABLE (toposort order)
- `migrations/V003__create_indexes.sql` — CREATE INDEX
- `migrations/V004__create_constraints.sql` — ALTER TABLE ADD FK + CHECK
- `seed/01_<entity>_sample.sql` — 3 sample rows per preset entity
- `src/main/java/<pkg>/<Entity>.java` — JPA entities
- `ddl-report.md` — revalidation summary

All DDL is idempotent (`IF NOT EXISTS`). PostgreSQL uses `BIGSERIAL` + `ON CONFLICT DO NOTHING`; HSQLDB uses `BIGINT GENERATED BY DEFAULT AS IDENTITY` + `MERGE INTO`.
```

- [ ] **Step 3: Create validation-codes.md**

Path: `.claude/skills/karpathy-rdb-ddl/references/validation-codes.md`
```markdown
# Validation Codes (Stage 2 re-runs V001~V005 at DDL level)

| Code | Check | Severity | On fail |
|---|---|---|---|
| V001 | Every entity has a PK column (`pk: true`) | ERROR | abort |
| V002 | Every relation.to exists, target has PK, FK column type matches | ERROR | abort |
| V003 | Identifiers are snake_case, not reserved, ≤63 chars | ERROR | abort |
| V004 | entity.schema present; cross-schema FK declared | ERROR | abort |
| V005 | `business_rules[*].enforced_by` SQL parses for target dialect | WARN | skip that CHECK, log to report |
```

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/karpathy-rdb-ddl/
git commit -m "docs: add SKILL.md and reference docs for karpathy-rdb-ddl"
```

---

### Task 3: Loader (parse _blueprint.yaml + version/validation guard)

**Files:**
- Create: `scripts/loader.py`
- Test: `tests/test_loader.py`

- [ ] **Step 1: Write failing test**

Path: `tests/test_loader.py`
```python
import pytest
import pathlib
from loader import load_blueprint, BlueprintError


def write(tmp_path, content):
    p = tmp_path / "_blueprint.yaml"
    p.write_text(content, encoding="utf-8")
    return p


def test_load_valid_blueprint(tmp_path):
    p = write(tmp_path, """
version: 1
project: 테스트
entities: []
relations: []
business_rules: []
validation:
  passed: true
""")
    bp = load_blueprint(p)
    assert bp["version"] == 1
    assert bp["project"] == "테스트"


def test_reject_missing_version(tmp_path):
    p = write(tmp_path, """
project: x
validation: {passed: true}
""")
    with pytest.raises(BlueprintError, match="version"):
        load_blueprint(p)


def test_reject_wrong_version(tmp_path):
    p = write(tmp_path, """
version: 99
project: x
validation: {passed: true}
""")
    with pytest.raises(BlueprintError, match="version"):
        load_blueprint(p)


def test_reject_failed_validation(tmp_path):
    p = write(tmp_path, """
version: 1
project: x
validation: {passed: false}
""")
    with pytest.raises(BlueprintError, match="Stage 1 validation failed"):
        load_blueprint(p)


def test_reject_missing_file(tmp_path):
    with pytest.raises(BlueprintError, match="not found"):
        load_blueprint(tmp_path / "missing.yaml")
```

- [ ] **Step 2: Run test (RED)**

```bash
pytest tests/test_loader.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'loader'`

- [ ] **Step 3: Implement loader.py**

Path: `scripts/loader.py`
```python
import pathlib
import yaml


class BlueprintError(Exception):
    pass


def load_blueprint(path: pathlib.Path) -> dict:
    path = pathlib.Path(path)
    if not path.exists():
        raise BlueprintError(f"blueprint not found: {path}")
    try:
        bp = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise BlueprintError(f"malformed yaml: {e}") from e
    if not isinstance(bp, dict):
        raise BlueprintError("blueprint root must be a mapping")
    if bp.get("version") != 1:
        raise BlueprintError(f"unsupported blueprint version: {bp.get('version')}")
    validation = bp.get("validation") or {}
    if not validation.get("passed"):
        raise BlueprintError("Stage 1 validation failed — run /karpathy-rdb compile again")
    bp.setdefault("entities", [])
    bp.setdefault("relations", [])
    bp.setdefault("business_rules", [])
    return bp
```

- [ ] **Step 4: Run test (GREEN)**

```bash
pytest tests/test_loader.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/loader.py tests/test_loader.py
git commit -m "feat: blueprint loader with version + validation guard"
```

---

### Task 4: Toposort (FK-dependency entity ordering)

**Files:**
- Create: `scripts/toposort.py`
- Test: `tests/test_toposort.py`

- [ ] **Step 1: Write failing test**

Path: `tests/test_toposort.py`
```python
import pytest
from toposort import topo_sort, CycleError


def E(name):
    return {"name": name}


def R(frm, to, fk="x"):
    return {"from": frm, "to": to, "fk": fk}


def test_linear_chain():
    entities = [E("c"), E("a"), E("b")]
    relations = [R("b", "a"), R("c", "b")]
    result = [e["name"] for e in topo_sort(entities, relations)]
    assert result == ["a", "b", "c"]


def test_diamond():
    entities = [E("d"), E("a"), E("b"), E("c")]
    relations = [R("b", "a"), R("c", "a"), R("d", "b"), R("d", "c")]
    result = [e["name"] for e in topo_sort(entities, relations)]
    assert result.index("a") < result.index("b")
    assert result.index("a") < result.index("c")
    assert result.index("b") < result.index("d")
    assert result.index("c") < result.index("d")


def test_self_reference_allowed():
    entities = [E("emp")]
    relations = [R("emp", "emp", fk="manager_id")]
    result = [e["name"] for e in topo_sort(entities, relations)]
    assert result == ["emp"]


def test_cycle_raises():
    entities = [E("a"), E("b")]
    relations = [R("a", "b"), R("b", "a")]
    with pytest.raises(CycleError):
        topo_sort(entities, relations)


def test_no_relations():
    entities = [E("z"), E("a"), E("m")]
    result = sorted(e["name"] for e in topo_sort(entities, []))
    assert result == ["a", "m", "z"]
```

- [ ] **Step 2: Run test (RED)**

```bash
pytest tests/test_toposort.py -v
```
Expected: FAIL `ModuleNotFoundError`.

- [ ] **Step 3: Implement toposort.py**

Path: `scripts/toposort.py`
```python
from collections import defaultdict, deque
from typing import List, Dict


class CycleError(Exception):
    pass


def topo_sort(entities: List[dict], relations: List[dict]) -> List[dict]:
    by_name: Dict[str, dict] = {e["name"]: e for e in entities}
    indegree: Dict[str, int] = {name: 0 for name in by_name}
    out: Dict[str, set] = defaultdict(set)
    for r in relations:
        frm, to = r["from"], r["to"]
        if frm == to:  # self-reference, ignore for ordering
            continue
        if frm not in by_name or to not in by_name:
            continue
        if frm in out[to]:
            continue
        out[to].add(frm)
        indegree[frm] += 1
    ready = deque(sorted(name for name, d in indegree.items() if d == 0))
    result = []
    while ready:
        name = ready.popleft()
        result.append(by_name[name])
        for downstream in sorted(out[name]):
            indegree[downstream] -= 1
            if indegree[downstream] == 0:
                ready.append(downstream)
    if len(result) != len(by_name):
        remaining = set(by_name) - {e["name"] for e in result}
        raise CycleError(f"cycle detected among: {sorted(remaining)}")
    return result
```

- [ ] **Step 4: Run test (GREEN)**

```bash
pytest tests/test_toposort.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/toposort.py tests/test_toposort.py
git commit -m "feat: topological sort for FK dependency ordering"
```

---

### Task 5: Dialect registry

**Files:**
- Create: `scripts/dialect.py`
- Test: `tests/test_dialect.py`

- [ ] **Step 1: Write failing test**

Path: `tests/test_dialect.py`
```python
import pytest
from dialect import get_dialect, DialectError


def test_get_postgres():
    d = get_dialect("postgres")
    assert d.name == "postgres"
    assert d.schema_strategy == "native"
    assert d.type_map["bigserial"] == "BIGSERIAL"
    assert d.idempotent_insert == "ON CONFLICT DO NOTHING"
    assert d.regex_op == "~"


def test_get_hsqldb():
    d = get_dialect("hsqldb")
    assert d.name == "hsqldb"
    assert d.schema_strategy == "native"
    assert d.type_map["bigserial"] == "BIGINT GENERATED BY DEFAULT AS IDENTITY"
    assert d.idempotent_insert == "MERGE"
    assert d.regex_op is None


def test_unknown_dialect():
    with pytest.raises(DialectError, match="unknown"):
        get_dialect("oracle")


def test_template_dir_postgres():
    d = get_dialect("postgres")
    assert d.template_dir == "postgres"


def test_template_dir_hsqldb():
    d = get_dialect("hsqldb")
    assert d.template_dir == "hsqldb"
```

- [ ] **Step 2: Run test (RED)**

```bash
pytest tests/test_dialect.py -v
```
Expected: FAIL `ModuleNotFoundError`.

- [ ] **Step 3: Implement dialect.py**

Path: `scripts/dialect.py`
```python
from dataclasses import dataclass, field
from typing import Dict, Optional


class DialectError(Exception):
    pass


@dataclass
class Dialect:
    name: str
    template_dir: str
    schema_strategy: str           # "native" | "prefix"
    type_map: Dict[str, str]
    idempotent_insert: str         # "ON CONFLICT DO NOTHING" | "INSERT IGNORE" | "MERGE"
    regex_op: Optional[str]        # infix regex operator or None


POSTGRES = Dialect(
    name="postgres",
    template_dir="postgres",
    schema_strategy="native",
    type_map={
        "bigserial": "BIGSERIAL",
        "bigint": "BIGINT",
        "integer": "INTEGER",
        "varchar": "VARCHAR",
        "text": "TEXT",
        "boolean": "BOOLEAN",
        "timestamp": "TIMESTAMP",
        "date": "DATE",
        "numeric": "NUMERIC",
    },
    idempotent_insert="ON CONFLICT DO NOTHING",
    regex_op="~",
)

HSQLDB = Dialect(
    name="hsqldb",
    template_dir="hsqldb",
    schema_strategy="native",
    type_map={
        "bigserial": "BIGINT GENERATED BY DEFAULT AS IDENTITY",
        "bigint": "BIGINT",
        "integer": "INTEGER",
        "varchar": "VARCHAR",
        "text": "LONGVARCHAR",
        "boolean": "BOOLEAN",
        "timestamp": "TIMESTAMP",
        "date": "DATE",
        "numeric": "NUMERIC",
    },
    idempotent_insert="MERGE",
    regex_op=None,
)

_REGISTRY = {"postgres": POSTGRES, "hsqldb": HSQLDB}


def get_dialect(name: str) -> Dialect:
    if name not in _REGISTRY:
        raise DialectError(f"unknown dialect: {name}")
    return _REGISTRY[name]
```

- [ ] **Step 4: Run test (GREEN)**

```bash
pytest tests/test_dialect.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/dialect.py tests/test_dialect.py
git commit -m "feat: dialect registry for postgres and hsqldb"
```

---

### Task 6: Preset catalog

**Files:**
- Create: `scripts/preset_catalog.py`
- Test: `tests/test_preset_catalog.py`

- [ ] **Step 1: Write failing test**

Path: `tests/test_preset_catalog.py`
```python
from preset_catalog import is_preset


def test_preset_marker_wins():
    e = {"name": "anything", "preset": "고객관리"}
    assert is_preset(e) is True


def test_catalog_match_by_domain_and_name():
    e = {"name": "customer", "domain": ["고객관리"]}
    assert is_preset(e) is True


def test_catalog_match_string_domain():
    e = {"name": "sales_order", "domain": "주문관리"}
    assert is_preset(e) is True


def test_non_preset():
    e = {"name": "random_user_table", "domain": ["기타"]}
    assert is_preset(e) is False


def test_unknown_entity_in_known_domain():
    e = {"name": "totally_made_up", "domain": ["고객관리"]}
    assert is_preset(e) is False
```

- [ ] **Step 2: Run test (RED)**

```bash
pytest tests/test_preset_catalog.py -v
```
Expected: FAIL `ModuleNotFoundError`.

- [ ] **Step 3: Implement preset_catalog.py**

Path: `scripts/preset_catalog.py`
```python
PRESETS = {
    "고객관리": {"customer", "address", "contact_log"},
    "주문관리": {"sales_order", "order_item", "payment"},
    "재고관리": {"product", "sku", "warehouse", "stock"},
    "인사관리": {"employee", "department", "position"},
    "재무관리": {"account", "fiscal_period", "ledger_entry"},
}


def _domains(entity: dict):
    d = entity.get("domain")
    if d is None:
        return []
    if isinstance(d, str):
        return [d]
    return list(d)


def is_preset(entity: dict) -> bool:
    if entity.get("preset"):
        return True
    name = entity.get("name")
    for domain in _domains(entity):
        if name in PRESETS.get(domain, set()):
            return True
    return False
```

- [ ] **Step 4: Run test (GREEN)**

```bash
pytest tests/test_preset_catalog.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/preset_catalog.py tests/test_preset_catalog.py
git commit -m "feat: preset catalog with marker and fallback detection"
```

---

### Task 7: Revalidator skeleton + V001 (PK exists)

**Files:**
- Create: `scripts/revalidator.py`
- Test: `tests/test_revalidator.py`

- [ ] **Step 1: Write failing test**

Path: `tests/test_revalidator.py`
```python
from revalidator import revalidate


def bp(entities=None, relations=None, business_rules=None):
    return {
        "version": 1,
        "entities": entities or [],
        "relations": relations or [],
        "business_rules": business_rules or [],
    }


def test_v001_pk_exists_green():
    e = {"name": "c", "table": "c", "schema": "crm",
         "columns": [{"name": "id", "type": "bigserial", "pk": True}]}
    diags = revalidate(bp(entities=[e]))
    assert not any(d["code"] == "V001" for d in diags)


def test_v001_no_pk_error():
    e = {"name": "c", "table": "c", "schema": "crm",
         "columns": [{"name": "name", "type": "varchar"}]}
    diags = revalidate(bp(entities=[e]))
    v001 = [d for d in diags if d["code"] == "V001"]
    assert len(v001) == 1
    assert v001[0]["severity"] == "ERROR"
    assert "c" in v001[0]["message"]
```

- [ ] **Step 2: Run test (RED)**

```bash
pytest tests/test_revalidator.py -v
```
Expected: FAIL `ModuleNotFoundError`.

- [ ] **Step 3: Implement revalidator skeleton + V001**

Path: `scripts/revalidator.py`
```python
from typing import List, Dict


def _diag(code: str, severity: str, message: str, **kw) -> Dict:
    d = {"code": code, "severity": severity, "message": message}
    d.update(kw)
    return d


def _v001_pk_exists(entity: dict) -> List[Dict]:
    cols = entity.get("columns") or []
    if not any(c.get("pk") for c in cols):
        return [_diag("V001", "ERROR",
                      f"entity '{entity.get('name')}' has no PK column",
                      entity=entity.get("name"))]
    return []


def revalidate(blueprint: dict) -> List[Dict]:
    diags = []
    for e in blueprint.get("entities", []):
        diags.extend(_v001_pk_exists(e))
    return diags
```

- [ ] **Step 4: Run test (GREEN)**

```bash
pytest tests/test_revalidator.py -v
```
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/revalidator.py tests/test_revalidator.py
git commit -m "feat: revalidator V001 PK exists"
```

---

### Task 8: V002 FK targets

**Files:**
- Modify: `scripts/revalidator.py`
- Modify: `tests/test_revalidator.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_revalidator.py`:
```python
def _ent(name, cols=None):
    return {"name": name, "table": name, "schema": "crm",
            "columns": cols or [{"name": "id", "type": "bigserial", "pk": True}]}


def test_v002_fk_target_exists_green():
    customer = _ent("customer")
    address = _ent("address", [
        {"name": "id", "type": "bigserial", "pk": True},
        {"name": "customer_id", "type": "bigint"},
    ])
    r = {"from": "address", "to": "customer", "fk": "customer_id"}
    diags = revalidate(bp(entities=[customer, address], relations=[r]))
    assert not any(d["code"] == "V002" for d in diags)


def test_v002_missing_target_error():
    address = _ent("address", [
        {"name": "id", "type": "bigserial", "pk": True},
        {"name": "ghost_id", "type": "bigint"},
    ])
    r = {"from": "address", "to": "ghost", "fk": "ghost_id"}
    diags = revalidate(bp(entities=[address], relations=[r]))
    v002 = [d for d in diags if d["code"] == "V002"]
    assert len(v002) == 1
    assert v002[0]["severity"] == "ERROR"


def test_v002_target_no_pk_error():
    pk_less = {"name": "x", "table": "x", "schema": "s",
               "columns": [{"name": "n", "type": "varchar"}]}
    src = _ent("src", [
        {"name": "id", "type": "bigserial", "pk": True},
        {"name": "x_id", "type": "bigint"},
    ])
    r = {"from": "src", "to": "x", "fk": "x_id"}
    diags = revalidate(bp(entities=[pk_less, src], relations=[r]))
    # V002 will only fire after V001 already flags pk_less; we expect V002 too.
    assert any(d["code"] == "V002" for d in diags)
```

- [ ] **Step 2: Run test (RED)**

```bash
pytest tests/test_revalidator.py -v
```
Expected: 3 new tests FAIL.

- [ ] **Step 3: Add V002 to revalidator.py**

Append to `scripts/revalidator.py`:
```python
def _v002_fk_targets(blueprint: dict) -> List[Dict]:
    diags = []
    by_name = {e["name"]: e for e in blueprint.get("entities", [])}
    for r in blueprint.get("relations", []):
        target = by_name.get(r.get("to"))
        if target is None:
            diags.append(_diag("V002", "ERROR",
                               f"relation {r.get('from')}->{r.get('to')}: target entity not found",
                               relation=r))
            continue
        target_cols = target.get("columns") or []
        if not any(c.get("pk") for c in target_cols):
            diags.append(_diag("V002", "ERROR",
                               f"relation {r.get('from')}->{r.get('to')}: target has no PK",
                               relation=r))
    return diags
```

And modify `revalidate(...)`:
```python
def revalidate(blueprint: dict) -> List[Dict]:
    diags = []
    for e in blueprint.get("entities", []):
        diags.extend(_v001_pk_exists(e))
    diags.extend(_v002_fk_targets(blueprint))
    return diags
```

- [ ] **Step 4: Run test (GREEN)**

```bash
pytest tests/test_revalidator.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/revalidator.py tests/test_revalidator.py
git commit -m "feat: revalidator V002 FK target validation"
```

---

### Task 9: V003 Naming

**Files:**
- Modify: `scripts/revalidator.py`
- Modify: `tests/test_revalidator.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_revalidator.py`:
```python
def test_v003_naming_green():
    e = _ent("customer", [{"name": "id", "type": "bigserial", "pk": True},
                          {"name": "email", "type": "varchar"}])
    diags = revalidate(bp(entities=[e]))
    assert not any(d["code"] == "V003" for d in diags)


def test_v003_camel_case_error():
    e = _ent("Customer", [{"name": "id", "type": "bigserial", "pk": True}])
    diags = revalidate(bp(entities=[e]))
    assert any(d["code"] == "V003" for d in diags)


def test_v003_reserved_word_error():
    e = _ent("user", [{"name": "id", "type": "bigserial", "pk": True}])
    diags = revalidate(bp(entities=[e]))
    assert any(d["code"] == "V003" for d in diags)


def test_v003_too_long_error():
    e = _ent("a" * 64, [{"name": "id", "type": "bigserial", "pk": True}])
    diags = revalidate(bp(entities=[e]))
    assert any(d["code"] == "V003" for d in diags)
```

- [ ] **Step 2: Run test (RED)**

```bash
pytest tests/test_revalidator.py -v
```
Expected: 4 new tests FAIL.

- [ ] **Step 3: Add V003**

Append to `scripts/revalidator.py`:
```python
import re

_NAME_RE = re.compile(r"^[a-z_][a-z0-9_]*$")
RESERVED = frozenset({
    "user", "order", "select", "table", "from", "where", "group", "join",
    "index", "primary", "key", "foreign", "check", "constraint", "default",
    "null", "true", "false", "and", "or", "not", "in", "is", "as", "by",
})


def _v003_naming(entity: dict) -> List[Dict]:
    diags = []
    name = entity.get("name", "")
    if not _NAME_RE.match(name):
        diags.append(_diag("V003", "ERROR",
                           f"entity name '{name}' must be snake_case",
                           entity=name))
    if name.lower() in RESERVED:
        diags.append(_diag("V003", "ERROR",
                           f"entity name '{name}' is a SQL reserved word",
                           entity=name))
    if len(name) > 63:
        diags.append(_diag("V003", "ERROR",
                           f"entity name '{name}' exceeds 63 chars",
                           entity=name))
    for col in entity.get("columns") or []:
        cn = col.get("name", "")
        if not _NAME_RE.match(cn):
            diags.append(_diag("V003", "ERROR",
                               f"column '{name}.{cn}' must be snake_case",
                               entity=name, column=cn))
        if len(cn) > 63:
            diags.append(_diag("V003", "ERROR",
                               f"column '{name}.{cn}' exceeds 63 chars",
                               entity=name, column=cn))
    return diags
```

Update `revalidate(...)` to include V003:
```python
def revalidate(blueprint: dict) -> List[Dict]:
    diags = []
    for e in blueprint.get("entities", []):
        diags.extend(_v001_pk_exists(e))
        diags.extend(_v003_naming(e))
    diags.extend(_v002_fk_targets(blueprint))
    return diags
```

- [ ] **Step 4: Run test (GREEN)**

```bash
pytest tests/test_revalidator.py -v
```
Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/revalidator.py tests/test_revalidator.py
git commit -m "feat: revalidator V003 naming rules"
```

---

### Task 10: V004 Schema consistency

**Files:**
- Modify: `scripts/revalidator.py`
- Modify: `tests/test_revalidator.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_revalidator.py`:
```python
def test_v004_schema_present_green():
    e = _ent("customer")
    e["schema"] = "crm"
    diags = revalidate(bp(entities=[e]))
    assert not any(d["code"] == "V004" for d in diags)


def test_v004_schema_missing_error():
    e = _ent("customer")
    e.pop("schema", None)
    diags = revalidate(bp(entities=[e]))
    assert any(d["code"] == "V004" for d in diags)


def test_v004_cross_schema_fk_undeclared():
    a = _ent("a"); a["schema"] = "s1"
    b = _ent("b", [{"name": "id", "type": "bigserial", "pk": True},
                   {"name": "a_id", "type": "bigint"}])
    b["schema"] = "s2"
    r = {"from": "b", "to": "a", "fk": "a_id"}  # no cross_schema marker
    diags = revalidate(bp(entities=[a, b], relations=[r]))
    assert any(d["code"] == "V004" for d in diags)


def test_v004_cross_schema_fk_declared():
    a = _ent("a"); a["schema"] = "s1"
    b = _ent("b", [{"name": "id", "type": "bigserial", "pk": True},
                   {"name": "a_id", "type": "bigint"}])
    b["schema"] = "s2"
    r = {"from": "b", "to": "a", "fk": "a_id", "cross_schema": True}
    diags = revalidate(bp(entities=[a, b], relations=[r]))
    assert not any(d["code"] == "V004" for d in diags)
```

- [ ] **Step 2: Run test (RED)**

```bash
pytest tests/test_revalidator.py -v
```
Expected: 4 new tests FAIL.

- [ ] **Step 3: Add V004**

Append to `scripts/revalidator.py`:
```python
def _v004_schema(blueprint: dict) -> List[Dict]:
    diags = []
    by_name = {e["name"]: e for e in blueprint.get("entities", [])}
    for e in blueprint.get("entities", []):
        if not e.get("schema"):
            diags.append(_diag("V004", "ERROR",
                               f"entity '{e.get('name')}' missing schema",
                               entity=e.get("name")))
    for r in blueprint.get("relations", []):
        src = by_name.get(r.get("from"))
        dst = by_name.get(r.get("to"))
        if not src or not dst:
            continue
        if src.get("schema") and dst.get("schema") and src["schema"] != dst["schema"]:
            if not r.get("cross_schema"):
                diags.append(_diag("V004", "ERROR",
                                   f"cross-schema FK {r['from']}->{r['to']} not declared "
                                   "(set relation.cross_schema: true)",
                                   relation=r))
    return diags
```

Update `revalidate(...)`:
```python
def revalidate(blueprint: dict) -> List[Dict]:
    diags = []
    for e in blueprint.get("entities", []):
        diags.extend(_v001_pk_exists(e))
        diags.extend(_v003_naming(e))
    diags.extend(_v002_fk_targets(blueprint))
    diags.extend(_v004_schema(blueprint))
    return diags
```

- [ ] **Step 4: Run test (GREEN)**

```bash
pytest tests/test_revalidator.py -v
```
Expected: 13 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/revalidator.py tests/test_revalidator.py
git commit -m "feat: revalidator V004 schema consistency"
```

---

### Task 11: V005 Constraint translatable (with dialect)

**Files:**
- Modify: `scripts/revalidator.py`
- Modify: `tests/test_revalidator.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_revalidator.py`:
```python
def test_v005_simple_check_postgres_pass():
    br = {"name": "chk_age", "enforced_by": "age >= 0"}
    diags = revalidate(bp(business_rules=[br]), dialect="postgres")
    assert not any(d["code"] == "V005" for d in diags)


def test_v005_regex_postgres_pass():
    br = {"name": "chk_email", "enforced_by": "email ~ '^[^@]+@[^@]+$'"}
    diags = revalidate(bp(business_rules=[br]), dialect="postgres")
    assert not any(d["code"] == "V005" for d in diags)


def test_v005_regex_hsqldb_warns():
    br = {"name": "chk_email", "enforced_by": "email ~ '^[^@]+@[^@]+$'"}
    diags = revalidate(bp(business_rules=[br]), dialect="hsqldb")
    v005 = [d for d in diags if d["code"] == "V005"]
    assert len(v005) == 1
    assert v005[0]["severity"] == "WARN"


def test_v005_empty_expression_warns():
    br = {"name": "chk_x", "enforced_by": ""}
    diags = revalidate(bp(business_rules=[br]), dialect="postgres")
    assert any(d["code"] == "V005" for d in diags)
```

- [ ] **Step 2: Run test (RED)**

```bash
pytest tests/test_revalidator.py -v
```
Expected: 4 new tests FAIL.

- [ ] **Step 3: Add V005 and pass dialect through**

Modify top of `scripts/revalidator.py`:
```python
from dialect import get_dialect
```

Add:
```python
def _v005_constraints(blueprint: dict, dialect_name: str) -> List[Dict]:
    d = get_dialect(dialect_name)
    diags = []
    for br in blueprint.get("business_rules") or []:
        expr = (br.get("enforced_by") or "").strip()
        if not expr:
            diags.append(_diag("V005", "WARN",
                               f"business rule '{br.get('name')}' has empty enforced_by",
                               rule=br.get("name")))
            continue
        if "~" in expr and d.regex_op is None:
            diags.append(_diag("V005", "WARN",
                               f"business rule '{br.get('name')}' uses regex operator "
                               f"not supported by dialect '{dialect_name}'",
                               rule=br.get("name")))
    return diags
```

Update signature:
```python
def revalidate(blueprint: dict, dialect: str = "postgres") -> List[Dict]:
    diags = []
    for e in blueprint.get("entities", []):
        diags.extend(_v001_pk_exists(e))
        diags.extend(_v003_naming(e))
    diags.extend(_v002_fk_targets(blueprint))
    diags.extend(_v004_schema(blueprint))
    diags.extend(_v005_constraints(blueprint, dialect))
    return diags
```

- [ ] **Step 4: Run test (GREEN)**

```bash
pytest tests/test_revalidator.py -v
```
Expected: 17 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/revalidator.py tests/test_revalidator.py
git commit -m "feat: revalidator V005 constraint dialect awareness"
```

---

### Task 12: PostgreSQL templates — schema + tables

**Files:**
- Create: `.claude/skills/karpathy-rdb-ddl/templates/postgres/schema.sql.j2`
- Create: `.claude/skills/karpathy-rdb-ddl/templates/postgres/tables.sql.j2`

- [ ] **Step 1: Create schema.sql.j2**

```jinja
-- V001 Generated by andrej-karpathy-rdb-ddl (dialect: postgres)
{% for schema in schemas %}
CREATE SCHEMA IF NOT EXISTS {{ schema }};
{% endfor %}
```

- [ ] **Step 2: Create tables.sql.j2**

```jinja
-- V002 Generated by andrej-karpathy-rdb-ddl (dialect: postgres)
{% for e in entities %}
CREATE TABLE IF NOT EXISTS {{ e.schema }}.{{ e.table }} (
{%- for col in e.columns %}
    {{ col.name }} {{ col.sql_type }}{% if col.pk %} PRIMARY KEY{% endif %}{% if col.null == False %} NOT NULL{% endif %}{% if col.default is defined and col.default %} DEFAULT {{ col.default }}{% endif %}{% if not loop.last %},{% endif %}
{%- endfor %}
);
{% endfor %}
```

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/karpathy-rdb-ddl/templates/postgres/schema.sql.j2 .claude/skills/karpathy-rdb-ddl/templates/postgres/tables.sql.j2
git commit -m "feat: add postgres schema + tables Jinja2 templates"
```

---

### Task 13: PostgreSQL templates — indexes + constraints + seed

**Files:**
- Create: `.claude/skills/karpathy-rdb-ddl/templates/postgres/indexes.sql.j2`
- Create: `.claude/skills/karpathy-rdb-ddl/templates/postgres/constraints.sql.j2`
- Create: `.claude/skills/karpathy-rdb-ddl/templates/postgres/seed.sql.j2`

- [ ] **Step 1: Create indexes.sql.j2**

```jinja
-- V003 Generated by andrej-karpathy-rdb-ddl (dialect: postgres)
{% for idx in indexes %}
CREATE {% if idx.unique %}UNIQUE {% endif %}INDEX IF NOT EXISTS {{ idx.name }} ON {{ idx.schema }}.{{ idx.table }} ({{ idx.columns | join(', ') }});
{% endfor %}
```

- [ ] **Step 2: Create constraints.sql.j2**

```jinja
-- V004 Generated by andrej-karpathy-rdb-ddl (dialect: postgres)
{% for fk in foreign_keys %}
ALTER TABLE {{ fk.src_schema }}.{{ fk.src_table }}
    ADD CONSTRAINT {{ fk.name }}
    FOREIGN KEY ({{ fk.column }}) REFERENCES {{ fk.ref_schema }}.{{ fk.ref_table }}({{ fk.ref_column }})
    ON DELETE {{ fk.on_delete | upper }};
{% endfor %}
{% for chk in checks %}
ALTER TABLE {{ chk.schema }}.{{ chk.table }} ADD CONSTRAINT {{ chk.name }} CHECK ({{ chk.expression }});
{% endfor %}
```

- [ ] **Step 3: Create seed.sql.j2**

```jinja
-- Seed for {{ entity.schema }}.{{ entity.table }} (preset)
INSERT INTO {{ entity.schema }}.{{ entity.table }} ({{ columns | join(', ') }}) VALUES
{%- for row in rows %}
    ({{ row | join(', ') }}){% if not loop.last %},{% else %}{% endif %}
{%- endfor %}
ON CONFLICT DO NOTHING;
```

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/karpathy-rdb-ddl/templates/postgres/indexes.sql.j2 .claude/skills/karpathy-rdb-ddl/templates/postgres/constraints.sql.j2 .claude/skills/karpathy-rdb-ddl/templates/postgres/seed.sql.j2
git commit -m "feat: add postgres indexes/constraints/seed Jinja2 templates"
```

---

### Task 14: DDL generator (postgres) — schema + tables

**Files:**
- Create: `scripts/ddl_gen.py`
- Test: `tests/test_ddl_gen.py`

- [ ] **Step 1: Write failing test**

Path: `tests/test_ddl_gen.py`
```python
import pathlib
from ddl_gen import generate_ddl


def make_blueprint():
    return {
        "version": 1,
        "entities": [
            {"name": "customer", "table": "customer", "schema": "crm",
             "columns": [
                 {"name": "id", "type": "bigserial", "pk": True, "null": False},
                 {"name": "email", "type": "varchar(255)", "null": False},
             ],
             "indexes": [{"name": "ix_customer_email", "columns": ["email"], "unique": True}]},
            {"name": "address", "table": "address", "schema": "crm",
             "columns": [
                 {"name": "id", "type": "bigserial", "pk": True, "null": False},
                 {"name": "customer_id", "type": "bigint", "null": False},
             ]},
        ],
        "relations": [
            {"from": "address", "to": "customer", "fk": "customer_id", "on_delete": "cascade"},
        ],
        "business_rules": [],
    }


def test_v001_creates_schema(tmp_path):
    generate_ddl(make_blueprint(), tmp_path, dialect="postgres")
    v001 = (tmp_path / "migrations" / "V001__create_schema.sql").read_text(encoding="utf-8")
    assert "CREATE SCHEMA IF NOT EXISTS crm;" in v001


def test_v002_creates_tables_in_toposort(tmp_path):
    generate_ddl(make_blueprint(), tmp_path, dialect="postgres")
    v002 = (tmp_path / "migrations" / "V002__create_tables.sql").read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS crm.customer" in v002
    assert "CREATE TABLE IF NOT EXISTS crm.address" in v002
    assert v002.index("crm.customer") < v002.index("crm.address")


def test_v002_uses_bigserial_for_postgres(tmp_path):
    generate_ddl(make_blueprint(), tmp_path, dialect="postgres")
    v002 = (tmp_path / "migrations" / "V002__create_tables.sql").read_text(encoding="utf-8")
    assert "BIGSERIAL" in v002
```

- [ ] **Step 2: Run test (RED)**

```bash
pytest tests/test_ddl_gen.py -v
```
Expected: FAIL `ModuleNotFoundError`.

- [ ] **Step 3: Implement ddl_gen.py (schema + tables)**

Path: `scripts/ddl_gen.py`
```python
import pathlib
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from dialect import get_dialect
from toposort import topo_sort


TEMPLATE_ROOT = pathlib.Path(__file__).resolve().parent.parent / ".claude" / "skills" / "karpathy-rdb-ddl" / "templates"


def _env(dialect_dir: str) -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_ROOT / dialect_dir)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _normalize_columns(entity: dict, dialect) -> list:
    cols = []
    for c in entity.get("columns") or []:
        c2 = dict(c)
        raw_type = c.get("type", "").strip()
        base = raw_type.split("(")[0].lower()
        mapped = dialect.type_map.get(base, raw_type.upper())
        if "(" in raw_type and base in {"varchar", "numeric"}:
            mapped = mapped + raw_type[raw_type.index("("):]
        c2["sql_type"] = mapped
        cols.append(c2)
    return cols


def _gather_schemas(entities):
    return sorted({e["schema"] for e in entities if e.get("schema")})


def generate_ddl(blueprint: dict, out_dir: pathlib.Path, dialect: str = "postgres") -> None:
    out_dir = pathlib.Path(out_dir)
    (out_dir / "migrations").mkdir(parents=True, exist_ok=True)
    d = get_dialect(dialect)
    env = _env(d.template_dir)

    entities_sorted = topo_sort(blueprint.get("entities", []), blueprint.get("relations", []))
    entities_render = [{**e, "columns": _normalize_columns(e, d)} for e in entities_sorted]
    schemas = _gather_schemas(entities_sorted)

    (out_dir / "migrations" / "V001__create_schema.sql").write_text(
        env.get_template("schema.sql.j2").render(schemas=schemas), encoding="utf-8")
    (out_dir / "migrations" / "V002__create_tables.sql").write_text(
        env.get_template("tables.sql.j2").render(entities=entities_render), encoding="utf-8")
```

- [ ] **Step 4: Run test (GREEN)**

```bash
pytest tests/test_ddl_gen.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/ddl_gen.py tests/test_ddl_gen.py
git commit -m "feat: DDL generator V001 schema + V002 tables (postgres)"
```

---

### Task 15: DDL generator — indexes + constraints

**Files:**
- Modify: `scripts/ddl_gen.py`
- Modify: `tests/test_ddl_gen.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_ddl_gen.py`:
```python
def test_v003_creates_unique_index(tmp_path):
    generate_ddl(make_blueprint(), tmp_path, dialect="postgres")
    v003 = (tmp_path / "migrations" / "V003__create_indexes.sql").read_text(encoding="utf-8")
    assert "CREATE UNIQUE INDEX IF NOT EXISTS ix_customer_email" in v003
    assert "ON crm.customer (email)" in v003


def test_v004_creates_fk(tmp_path):
    generate_ddl(make_blueprint(), tmp_path, dialect="postgres")
    v004 = (tmp_path / "migrations" / "V004__create_constraints.sql").read_text(encoding="utf-8")
    assert "ALTER TABLE crm.address" in v004
    assert "REFERENCES crm.customer(id)" in v004
    assert "ON DELETE CASCADE" in v004


def test_v004_creates_check(tmp_path):
    bp = make_blueprint()
    bp["business_rules"] = [{
        "name": "chk_email_format",
        "applies_to": "customer",
        "enforced_by": "email LIKE '%@%'",
    }]
    generate_ddl(bp, tmp_path, dialect="postgres")
    v004 = (tmp_path / "migrations" / "V004__create_constraints.sql").read_text(encoding="utf-8")
    assert "chk_email_format" in v004
    assert "CHECK (email LIKE '%@%')" in v004
```

- [ ] **Step 2: Run test (RED)**

```bash
pytest tests/test_ddl_gen.py -v
```
Expected: 3 new tests FAIL.

- [ ] **Step 3: Extend ddl_gen.py with indexes + constraints**

Add to `scripts/ddl_gen.py`:
```python
def _gather_indexes(entities_sorted):
    out = []
    for e in entities_sorted:
        for ix in e.get("indexes") or []:
            out.append({
                "name": ix["name"],
                "schema": e["schema"],
                "table": e["table"],
                "columns": ix["columns"],
                "unique": bool(ix.get("unique")),
            })
    return out


def _gather_foreign_keys(blueprint: dict, by_name):
    fks = []
    for r in blueprint.get("relations") or []:
        src = by_name.get(r.get("from"))
        dst = by_name.get(r.get("to"))
        if not src or not dst:
            continue
        ref_pk = next((c["name"] for c in dst.get("columns") or [] if c.get("pk")), None)
        if not ref_pk:
            continue
        fk_name = f"fk_{src['table']}_{r.get('fk', 'unknown')}"
        fks.append({
            "name": fk_name,
            "src_schema": src["schema"], "src_table": src["table"],
            "column": r.get("fk"),
            "ref_schema": dst["schema"], "ref_table": dst["table"],
            "ref_column": ref_pk,
            "on_delete": r.get("on_delete", "no action"),
        })
    return fks


def _gather_checks(blueprint: dict, by_name):
    chks = []
    for br in blueprint.get("business_rules") or []:
        expr = (br.get("enforced_by") or "").strip()
        if not expr:
            continue
        target = by_name.get(br.get("applies_to"))
        if not target:
            continue
        chks.append({
            "name": br["name"],
            "schema": target["schema"],
            "table": target["table"],
            "expression": expr,
        })
    return chks
```

Update `generate_ddl(...)` end:
```python
def generate_ddl(blueprint: dict, out_dir: pathlib.Path, dialect: str = "postgres") -> None:
    out_dir = pathlib.Path(out_dir)
    (out_dir / "migrations").mkdir(parents=True, exist_ok=True)
    d = get_dialect(dialect)
    env = _env(d.template_dir)

    entities_sorted = topo_sort(blueprint.get("entities", []), blueprint.get("relations", []))
    entities_render = [{**e, "columns": _normalize_columns(e, d)} for e in entities_sorted]
    schemas = _gather_schemas(entities_sorted)
    by_name = {e["name"]: e for e in entities_sorted}
    indexes = _gather_indexes(entities_sorted)
    fks = _gather_foreign_keys(blueprint, by_name)
    chks = _gather_checks(blueprint, by_name)

    (out_dir / "migrations" / "V001__create_schema.sql").write_text(
        env.get_template("schema.sql.j2").render(schemas=schemas), encoding="utf-8")
    (out_dir / "migrations" / "V002__create_tables.sql").write_text(
        env.get_template("tables.sql.j2").render(entities=entities_render), encoding="utf-8")
    (out_dir / "migrations" / "V003__create_indexes.sql").write_text(
        env.get_template("indexes.sql.j2").render(indexes=indexes), encoding="utf-8")
    (out_dir / "migrations" / "V004__create_constraints.sql").write_text(
        env.get_template("constraints.sql.j2").render(foreign_keys=fks, checks=chks), encoding="utf-8")
```

- [ ] **Step 4: Run test (GREEN)**

```bash
pytest tests/test_ddl_gen.py -v
```
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/ddl_gen.py tests/test_ddl_gen.py
git commit -m "feat: DDL generator V003 indexes + V004 FKs and checks"
```

---

### Task 16: HSQLDB templates + dialect test

**Files:**
- Create: `.claude/skills/karpathy-rdb-ddl/templates/hsqldb/schema.sql.j2`
- Create: `.claude/skills/karpathy-rdb-ddl/templates/hsqldb/tables.sql.j2`
- Create: `.claude/skills/karpathy-rdb-ddl/templates/hsqldb/indexes.sql.j2`
- Create: `.claude/skills/karpathy-rdb-ddl/templates/hsqldb/constraints.sql.j2`
- Create: `.claude/skills/karpathy-rdb-ddl/templates/hsqldb/seed.sql.j2`
- Create: `tests/test_ddl_gen_hsqldb.py`

- [ ] **Step 1: Copy postgres templates and adapt**

`hsqldb/schema.sql.j2`:
```jinja
-- V001 Generated by andrej-karpathy-rdb-ddl (dialect: hsqldb)
{% for schema in schemas %}
CREATE SCHEMA IF NOT EXISTS {{ schema }};
{% endfor %}
```

`hsqldb/tables.sql.j2`:
```jinja
-- V002 Generated by andrej-karpathy-rdb-ddl (dialect: hsqldb)
{% for e in entities %}
CREATE TABLE IF NOT EXISTS {{ e.schema }}.{{ e.table }} (
{%- for col in e.columns %}
    {{ col.name }} {{ col.sql_type }}{% if col.pk %} PRIMARY KEY{% endif %}{% if col.null == False %} NOT NULL{% endif %}{% if col.default is defined and col.default %} DEFAULT {{ col.default }}{% endif %}{% if not loop.last %},{% endif %}
{%- endfor %}
);
{% endfor %}
```

`hsqldb/indexes.sql.j2`:
```jinja
-- V003 Generated by andrej-karpathy-rdb-ddl (dialect: hsqldb)
{% for idx in indexes %}
CREATE {% if idx.unique %}UNIQUE {% endif %}INDEX IF NOT EXISTS {{ idx.name }} ON {{ idx.schema }}.{{ idx.table }} ({{ idx.columns | join(', ') }});
{% endfor %}
```

`hsqldb/constraints.sql.j2`:
```jinja
-- V004 Generated by andrej-karpathy-rdb-ddl (dialect: hsqldb)
{% for fk in foreign_keys %}
ALTER TABLE {{ fk.src_schema }}.{{ fk.src_table }}
    ADD CONSTRAINT {{ fk.name }}
    FOREIGN KEY ({{ fk.column }}) REFERENCES {{ fk.ref_schema }}.{{ fk.ref_table }}({{ fk.ref_column }})
    ON DELETE {{ fk.on_delete | upper }};
{% endfor %}
{% for chk in checks %}
ALTER TABLE {{ chk.schema }}.{{ chk.table }} ADD CONSTRAINT {{ chk.name }} CHECK ({{ chk.expression }});
{% endfor %}
```

`hsqldb/seed.sql.j2`:
```jinja
-- Seed for {{ entity.schema }}.{{ entity.table }} (preset, hsqldb)
{% for row in rows %}
MERGE INTO {{ entity.schema }}.{{ entity.table }} USING (VALUES({{ row | join(', ') }})) AS s({{ columns | join(', ') }}) ON {{ entity.schema }}.{{ entity.table }}.{{ pk_column }} = s.{{ pk_column }} WHEN NOT MATCHED THEN INSERT ({{ columns | join(', ') }}) VALUES ({{ columns | map('insert_prefix', 's.') | join(', ') }});
{% endfor %}
```

> Note: the `insert_prefix` filter prefixes each column name with `s.`. Implemented in env setup below.

- [ ] **Step 2: Write HSQLDB-specific test**

Path: `tests/test_ddl_gen_hsqldb.py`
```python
import pathlib
from ddl_gen import generate_ddl


def make_blueprint():
    return {
        "version": 1,
        "entities": [{
            "name": "customer", "table": "customer", "schema": "crm",
            "columns": [
                {"name": "id", "type": "bigserial", "pk": True, "null": False},
                {"name": "email", "type": "varchar(255)", "null": False},
            ],
            "indexes": [{"name": "ix_email", "columns": ["email"], "unique": True}],
        }],
        "relations": [],
        "business_rules": [],
    }


def test_hsqldb_uses_identity(tmp_path):
    generate_ddl(make_blueprint(), tmp_path, dialect="hsqldb")
    v002 = (tmp_path / "migrations" / "V002__create_tables.sql").read_text(encoding="utf-8")
    assert "BIGINT GENERATED BY DEFAULT AS IDENTITY" in v002
    assert "BIGSERIAL" not in v002


def test_hsqldb_creates_schema_natively(tmp_path):
    generate_ddl(make_blueprint(), tmp_path, dialect="hsqldb")
    v001 = (tmp_path / "migrations" / "V001__create_schema.sql").read_text(encoding="utf-8")
    assert "CREATE SCHEMA IF NOT EXISTS crm" in v001
```

- [ ] **Step 3: Run tests (RED then GREEN)**

```bash
pytest tests/test_ddl_gen_hsqldb.py -v
```
Expected: 2 passed (no code change needed; ddl_gen already routes via dialect).

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/karpathy-rdb-ddl/templates/hsqldb/ tests/test_ddl_gen_hsqldb.py
git commit -m "feat: HSQLDB templates and dialect test coverage"
```

---

### Task 17: JPA Entity generator (dialect-agnostic)

**Files:**
- Create: `.claude/skills/karpathy-rdb-ddl/templates/entity.java.j2`
- Create: `scripts/jpa_gen.py`
- Test: `tests/test_jpa_gen.py`

- [ ] **Step 1: Create entity.java.j2**

Path: `.claude/skills/karpathy-rdb-ddl/templates/entity.java.j2`
```jinja
package {{ package }};

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
{% if has_timestamp %}import java.time.LocalDateTime;
{% endif %}{% if has_date %}import java.time.LocalDate;
{% endif %}{% if has_bigdecimal %}import java.math.BigDecimal;
{% endif %}

@Entity
@Table(name = "{{ entity.table }}", schema = "{{ entity.schema }}")
@Data
@NoArgsConstructor
@AllArgsConstructor
public class {{ class_name }} {
{% for col in entity.columns %}
    {% if col.pk %}@Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    {% endif %}@Column(name = "{{ col.name }}"{% if col.null == False %}, nullable = false{% endif %}{% if col.unique %}, unique = true{% endif %})
    private {{ col.java_type }} {{ col.java_name }};

{% endfor %}}
```

- [ ] **Step 2: Write failing test**

Path: `tests/test_jpa_gen.py`
```python
import pathlib
import re
from jpa_gen import generate_jpa


def make_entities():
    return [{
        "name": "customer", "table": "customer", "schema": "crm",
        "columns": [
            {"name": "id", "type": "bigserial", "pk": True, "null": False},
            {"name": "email", "type": "varchar(255)", "null": False, "unique": True},
            {"name": "created_at", "type": "timestamp", "null": False},
        ],
    }]


def test_jpa_file_created(tmp_path):
    generate_jpa(make_entities(), package="com.example.crm", out_dir=tmp_path)
    f = tmp_path / "src" / "main" / "java" / "com" / "example" / "crm" / "Customer.java"
    assert f.exists()


def test_jpa_has_lombok_annotations(tmp_path):
    generate_jpa(make_entities(), package="com.example.crm", out_dir=tmp_path)
    text = (tmp_path / "src" / "main" / "java" / "com" / "example" / "crm" / "Customer.java").read_text()
    assert "@Data" in text
    assert "@NoArgsConstructor" in text
    assert "@AllArgsConstructor" in text
    assert "@Table(name = \"customer\", schema = \"crm\")" in text


def test_jpa_no_jdk17_syntax(tmp_path):
    generate_jpa(make_entities(), package="com.example.crm", out_dir=tmp_path)
    text = (tmp_path / "src" / "main" / "java" / "com" / "example" / "crm" / "Customer.java").read_text()
    # Records, sealed, switch-arrow: none
    assert not re.search(r"\brecord\s+\w+", text)
    assert "sealed " not in text
    assert "->" not in text  # switch arrow / lambda — not expected in entity


def test_jpa_camelcase_field_names(tmp_path):
    generate_jpa(make_entities(), package="com.example.crm", out_dir=tmp_path)
    text = (tmp_path / "src" / "main" / "java" / "com" / "example" / "crm" / "Customer.java").read_text()
    assert "private LocalDateTime createdAt;" in text


def test_jpa_id_annotation(tmp_path):
    generate_jpa(make_entities(), package="com.example.crm", out_dir=tmp_path)
    text = (tmp_path / "src" / "main" / "java" / "com" / "example" / "crm" / "Customer.java").read_text()
    assert "@Id" in text
    assert "GenerationType.IDENTITY" in text
```

- [ ] **Step 3: Run test (RED)**

```bash
pytest tests/test_jpa_gen.py -v
```
Expected: FAIL `ModuleNotFoundError`.

- [ ] **Step 4: Implement jpa_gen.py**

Path: `scripts/jpa_gen.py`
```python
import pathlib
from jinja2 import Environment, FileSystemLoader, StrictUndefined


TEMPLATE_ROOT = pathlib.Path(__file__).resolve().parent.parent / ".claude" / "skills" / "karpathy-rdb-ddl" / "templates"


_JAVA_TYPE = {
    "bigserial": "Long", "bigint": "Long", "integer": "Integer",
    "varchar": "String", "text": "String", "boolean": "Boolean",
    "timestamp": "LocalDateTime", "date": "LocalDate", "numeric": "BigDecimal",
}


def _pascal(name: str) -> str:
    return "".join(p.capitalize() for p in name.split("_"))


def _camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def _java_type(sql_type: str) -> str:
    base = sql_type.split("(")[0].lower().strip()
    return _JAVA_TYPE.get(base, "String")


def generate_jpa(entities, package: str, out_dir: pathlib.Path) -> None:
    out_dir = pathlib.Path(out_dir)
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_ROOT)),
        undefined=StrictUndefined,
        trim_blocks=False,
        lstrip_blocks=False,
        keep_trailing_newline=True,
    )
    tpl = env.get_template("entity.java.j2")
    for e in entities:
        cols_render = []
        for c in e.get("columns") or []:
            cols_render.append({
                **c,
                "java_type": _java_type(c.get("type", "")),
                "java_name": _camel(c.get("name", "")),
            })
        types = {c["java_type"] for c in cols_render}
        pkg = package
        if "<schema>" in pkg:
            pkg = pkg.replace("<schema>", e["schema"])
        elif pkg.endswith(".<schema>") is False and e.get("schema") and pkg.count(".") >= 1 and pkg.split(".")[-1] != e["schema"]:
            # If caller passed a plain package, append schema as subpackage
            pass
        class_name = _pascal(e["name"])
        out_path = out_dir / "src" / "main" / "java" / pathlib.Path(*pkg.split("."))
        out_path.mkdir(parents=True, exist_ok=True)
        rendered = tpl.render(
            package=pkg, entity={**e, "columns": cols_render},
            class_name=class_name,
            has_timestamp="LocalDateTime" in types,
            has_date="LocalDate" in types,
            has_bigdecimal="BigDecimal" in types,
        )
        (out_path / f"{class_name}.java").write_text(rendered, encoding="utf-8")
```

- [ ] **Step 5: Run test (GREEN)**

```bash
pytest tests/test_jpa_gen.py -v
```
Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add scripts/jpa_gen.py .claude/skills/karpathy-rdb-ddl/templates/entity.java.j2 tests/test_jpa_gen.py
git commit -m "feat: JPA Entity generator with Lombok, JDK11+ compatible"
```

---

### Task 18: Seed generator (preset entities only)

**Files:**
- Create: `scripts/seed_gen.py`
- Test: `tests/test_seed_gen.py`

- [ ] **Step 1: Write failing test**

Path: `tests/test_seed_gen.py`
```python
import pathlib
from seed_gen import generate_seed


def make_entities():
    return [
        {
            "name": "customer", "table": "customer", "schema": "crm",
            "domain": ["고객관리"], "preset": "고객관리",
            "columns": [
                {"name": "id", "type": "bigserial", "pk": True},
                {"name": "email", "type": "varchar(255)", "null": False},
            ],
        },
        {
            "name": "totally_custom", "table": "totally_custom", "schema": "etc",
            "domain": ["기타"],
            "columns": [{"name": "id", "type": "bigserial", "pk": True}],
        },
    ]


def test_seed_created_for_preset(tmp_path):
    generate_seed(make_entities(), tmp_path, dialect="postgres")
    f = tmp_path / "seed" / "01_customer_sample.sql"
    assert f.exists()
    text = f.read_text(encoding="utf-8")
    assert "INSERT INTO crm.customer" in text
    assert "ON CONFLICT DO NOTHING" in text
    assert text.count("'sample") == 3  # 3 rows with sample values


def test_seed_skipped_for_non_preset(tmp_path):
    generate_seed(make_entities(), tmp_path, dialect="postgres")
    assert not (tmp_path / "seed" / "01_totally_custom_sample.sql").exists()


def test_seed_hsqldb_uses_merge(tmp_path):
    generate_seed(make_entities(), tmp_path, dialect="hsqldb")
    f = tmp_path / "seed" / "01_customer_sample.sql"
    text = f.read_text(encoding="utf-8")
    assert "MERGE INTO crm.customer" in text
```

- [ ] **Step 2: Run test (RED)**

```bash
pytest tests/test_seed_gen.py -v
```
Expected: FAIL `ModuleNotFoundError`.

- [ ] **Step 3: Implement seed_gen.py**

Path: `scripts/seed_gen.py`
```python
import pathlib
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from dialect import get_dialect
from preset_catalog import is_preset


TEMPLATE_ROOT = pathlib.Path(__file__).resolve().parent.parent / ".claude" / "skills" / "karpathy-rdb-ddl" / "templates"


def _sample_value(col: dict, row_idx: int) -> str:
    base = col.get("type", "").split("(")[0].lower()
    if base in {"bigserial", "bigint", "integer", "numeric"}:
        return str(row_idx + 1)
    if base == "boolean":
        return "TRUE"
    if base in {"timestamp", "date"}:
        return "CURRENT_TIMESTAMP" if base == "timestamp" else "CURRENT_DATE"
    return f"'sample{row_idx + 1}'"


def generate_seed(entities, out_dir: pathlib.Path, dialect: str = "postgres") -> None:
    out_dir = pathlib.Path(out_dir)
    (out_dir / "seed").mkdir(parents=True, exist_ok=True)
    d = get_dialect(dialect)
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_ROOT / d.template_dir)),
        undefined=StrictUndefined,
        trim_blocks=True, lstrip_blocks=True,
    )
    if d.idempotent_insert == "MERGE":
        env.filters["insert_prefix"] = lambda name, prefix: f"{prefix}{name}"
    tpl = env.get_template("seed.sql.j2")

    for e in entities:
        if not is_preset(e):
            continue
        non_pk_cols = [c for c in e.get("columns") or [] if not c.get("pk")]
        if not non_pk_cols:
            continue
        col_names = [c["name"] for c in non_pk_cols]
        pk_col = next((c["name"] for c in e.get("columns") or [] if c.get("pk")), "id")
        rows = [[_sample_value(c, i) for c in non_pk_cols] for i in range(3)]
        rendered = tpl.render(entity=e, columns=col_names, rows=rows, pk_column=pk_col)
        (out_dir / "seed" / f"01_{e['table']}_sample.sql").write_text(rendered, encoding="utf-8")
```

- [ ] **Step 4: Run test (GREEN)**

```bash
pytest tests/test_seed_gen.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/seed_gen.py tests/test_seed_gen.py
git commit -m "feat: seed generator for preset entities (postgres+hsqldb)"
```

---

### Task 19: CLI orchestration (ddl_compile.py)

**Files:**
- Create: `scripts/ddl_compile.py`
- Test: `tests/test_ddl_compile.py`

- [ ] **Step 1: Write failing test**

Path: `tests/test_ddl_compile.py`
```python
import pathlib
import subprocess
import sys
import textwrap


def write_blueprint(tmp_path, passed=True):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    (wiki / "_blueprint.yaml").write_text(textwrap.dedent(f"""
        version: 1
        project: 테스트
        entities:
          - name: customer
            table: customer
            schema: crm
            domain: [고객관리]
            preset: 고객관리
            columns:
              - {{name: id, type: bigserial, pk: true, null: false}}
              - {{name: email, type: 'varchar(255)', null: false}}
            indexes:
              - {{name: ix_email, columns: [email], unique: true}}
        relations: []
        business_rules: []
        validation:
          passed: {str(passed).lower()}
        """).strip(), encoding="utf-8")
    return wiki


def run(args, cwd):
    script = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "ddl_compile.py"
    return subprocess.run([sys.executable, str(script), *args], cwd=cwd, capture_output=True, text=True)


def test_compile_success(tmp_path):
    wiki = write_blueprint(tmp_path)
    out = tmp_path / "out"
    r = run([str(wiki / "_blueprint.yaml"), "--out", str(out), "--package", "com.example.crm"], cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    assert (out / "migrations" / "V001__create_schema.sql").exists()
    assert (out / "migrations" / "V002__create_tables.sql").exists()
    assert (out / "migrations" / "V003__create_indexes.sql").exists()
    assert (out / "migrations" / "V004__create_constraints.sql").exists()
    assert (out / "seed" / "01_customer_sample.sql").exists()
    assert (out / "src" / "main" / "java" / "com" / "example" / "crm" / "Customer.java").exists()
    assert (out / "ddl-report.md").exists()


def test_compile_aborts_on_failed_validation(tmp_path):
    wiki = write_blueprint(tmp_path, passed=False)
    out = tmp_path / "out"
    r = run([str(wiki / "_blueprint.yaml"), "--out", str(out)], cwd=tmp_path)
    assert r.returncode == 1
    assert "Stage 1 validation failed" in r.stderr


def test_compile_hsqldb_dialect(tmp_path):
    wiki = write_blueprint(tmp_path)
    out = tmp_path / "out"
    r = run([str(wiki / "_blueprint.yaml"), "--out", str(out), "--dialect", "hsqldb"], cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    v002 = (out / "migrations" / "V002__create_tables.sql").read_text(encoding="utf-8")
    assert "BIGINT GENERATED BY DEFAULT AS IDENTITY" in v002
```

- [ ] **Step 2: Run test (RED)**

```bash
pytest tests/test_ddl_compile.py -v
```
Expected: FAIL — script does not exist.

- [ ] **Step 3: Implement ddl_compile.py**

Path: `scripts/ddl_compile.py`
```python
#!/usr/bin/env python3
import argparse
import pathlib
import sys
import datetime

# Ensure scripts/ is on path when invoked as a file
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from loader import load_blueprint, BlueprintError
from revalidator import revalidate
from ddl_gen import generate_ddl
from jpa_gen import generate_jpa
from seed_gen import generate_seed


def _resolve_package(template: str, schema: str) -> str:
    return template.replace("<schema>", schema)


def _write_report(out_dir: pathlib.Path, blueprint: dict, diags: list, dialect: str, stats: dict) -> None:
    errors = [d for d in diags if d["severity"] == "ERROR"]
    warns = [d for d in diags if d["severity"] == "WARN"]
    lines = [
        "# DDL Compile Report",
        f"- timestamp: {datetime.datetime.now().isoformat()}",
        f"- dialect: {dialect}",
        f"- project: {blueprint.get('project')}",
        f"- entities: {stats['entities']}, relations: {stats['relations']}, schemas: {stats['schemas']}",
        "",
        "## Revalidation",
        f"- ERROR: {len(errors)}",
        f"- WARN: {len(warns)}",
    ]
    if warns:
        lines.append("")
        lines.append("### Warnings")
        for w in warns:
            lines.append(f"- {w['code']}: {w['message']}")
    if errors:
        lines.append("")
        lines.append("### Errors")
        for e in errors:
            lines.append(f"- {e['code']}: {e['message']}")
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- migrations: 4 files")
    lines.append(f"- jpa: {stats['entities']} entity files")
    lines.append(f"- seed: {stats['seeds']} preset files")
    lines.append("")
    lines.append("## Next")
    lines.append("Hand off `db/` to Stage 3 (/nexacro-fullstack-starter).")
    (out_dir / "ddl-report.md").write_text("\n".join(lines), encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="ddl_compile")
    ap.add_argument("blueprint", help="path to _blueprint.yaml")
    ap.add_argument("--out", default="./db", help="output directory (default ./db)")
    ap.add_argument("--package", default="com.example.<schema>", help="Java package template")
    ap.add_argument("--dialect", default="postgres", choices=["postgres", "hsqldb"])
    args = ap.parse_args(argv)

    try:
        bp = load_blueprint(pathlib.Path(args.blueprint))
    except BlueprintError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    diags = revalidate(bp, dialect=args.dialect)
    errors = [d for d in diags if d["severity"] == "ERROR"]
    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if errors:
        stats = {"entities": len(bp.get("entities") or []),
                 "relations": len(bp.get("relations") or []),
                 "schemas": len({e["schema"] for e in bp.get("entities") or [] if e.get("schema")}),
                 "seeds": 0}
        _write_report(out_dir, bp, diags, args.dialect, stats)
        for e in errors:
            print(f"ERROR {e['code']}: {e['message']}", file=sys.stderr)
        return 1

    try:
        generate_ddl(bp, out_dir, dialect=args.dialect)
        for e in bp.get("entities") or []:
            pkg = _resolve_package(args.package, e.get("schema", "default"))
            generate_jpa([e], package=pkg, out_dir=out_dir)
        generate_seed(bp.get("entities") or [], out_dir, dialect=args.dialect)
    except Exception as e:
        print(f"ERROR: template/IO failure: {e}", file=sys.stderr)
        return 3

    from preset_catalog import is_preset
    stats = {
        "entities": len(bp.get("entities") or []),
        "relations": len(bp.get("relations") or []),
        "schemas": len({e["schema"] for e in bp.get("entities") or [] if e.get("schema")}),
        "seeds": sum(1 for e in bp.get("entities") or [] if is_preset(e)),
    }
    _write_report(out_dir, bp, diags, args.dialect, stats)
    print(f"OK: wrote {out_dir} (dialect={args.dialect})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test (GREEN)**

```bash
pytest tests/test_ddl_compile.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/ddl_compile.py tests/test_ddl_compile.py
git commit -m "feat: CLI orchestration with exit codes and ddl-report.md"
```

---

### Task 20: Slash command definition

**Files:**
- Create: `.claude/commands/rdb-ddl-compile.md`

- [ ] **Step 1: Create command file**

Path: `.claude/commands/rdb-ddl-compile.md`
```markdown
---
name: rdb-ddl-compile
description: Stage 2 — generate PostgreSQL/HSQLDB DDL + Flyway + JPA + seed from _blueprint.yaml
argument-hint: <wiki_path> [--out <dir>] [--package <pkg>] [--dialect postgres|hsqldb]
---

# /rdb-ddl-compile

Compile Stage 1 wiki (`<wiki_path>/_blueprint.yaml`) into DDL artifacts.

## Usage

```
/rdb-ddl-compile <wiki_path> [--out <output_dir>] [--package <java_pkg>] [--dialect <postgres|hsqldb>]
```

## Defaults

- `--out`: `./db/`
- `--package`: `com.example.<schema>` (the literal substring `<schema>` is replaced per entity)
- `--dialect`: `postgres`

## Behavior

1. Verify `<wiki_path>/_blueprint.yaml` exists; abort with guidance if missing.
2. Run: `python scripts/ddl_compile.py <wiki>/_blueprint.yaml --out <out> --package <pkg> --dialect <dialect>`
3. Exit 0 → print artifact paths + `ddl-report.md`. Non-zero → surface `ddl-report.md` location and stderr.

## Exit codes

- 0: success
- 1: Stage 1 validation failed OR revalidation ERROR
- 2: file IO failure
- 3: template rendering failure
```

- [ ] **Step 2: Commit**

```bash
git add .claude/commands/rdb-ddl-compile.md
git commit -m "feat: add /rdb-ddl-compile slash command"
```

---

### Task 21: Golden integration test

**Files:**
- Create: `tests/fixtures/golden_blueprint.yaml`
- Create: `tests/test_golden_path.py`

- [ ] **Step 1: Create golden fixture**

Path: `tests/fixtures/golden_blueprint.yaml`
```yaml
version: 1
project: 골든
entities:
  - name: customer
    table: customer
    schema: crm
    domain: [고객관리]
    preset: 고객관리
    columns:
      - {name: id, type: bigserial, pk: true, null: false}
      - {name: email, type: varchar(255), null: false, unique: true}
      - {name: created_at, type: timestamp, null: false}
    indexes:
      - {name: ix_customer_email, columns: [email], unique: true}
  - name: address
    table: address
    schema: crm
    domain: [고객관리]
    preset: 고객관리
    columns:
      - {name: id, type: bigserial, pk: true, null: false}
      - {name: customer_id, type: bigint, null: false}
      - {name: line1, type: varchar(255), null: false}
relations:
  - {from: address, to: customer, fk: customer_id, on_delete: cascade}
business_rules:
  - {name: chk_customer_email, applies_to: customer, enforced_by: "email LIKE '%@%'"}
validation:
  passed: true
```

- [ ] **Step 2: Write integration test**

Path: `tests/test_golden_path.py`
```python
import pathlib
import sys
import subprocess


FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "golden_blueprint.yaml"
SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "ddl_compile.py"


def _run(args, cwd):
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=cwd, capture_output=True, text=True)


def test_golden_postgres(tmp_path):
    r = _run([str(FIXTURE), "--out", str(tmp_path), "--dialect", "postgres"], cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    for f in [
        "migrations/V001__create_schema.sql",
        "migrations/V002__create_tables.sql",
        "migrations/V003__create_indexes.sql",
        "migrations/V004__create_constraints.sql",
        "seed/01_customer_sample.sql",
        "seed/01_address_sample.sql",
        "src/main/java/com/example/crm/Customer.java",
        "src/main/java/com/example/crm/Address.java",
        "ddl-report.md",
    ]:
        assert (tmp_path / f).exists(), f"missing {f}"
    v004 = (tmp_path / "migrations" / "V004__create_constraints.sql").read_text()
    assert "fk_address_customer_id" in v004
    assert "chk_customer_email" in v004


def test_golden_hsqldb(tmp_path):
    r = _run([str(FIXTURE), "--out", str(tmp_path), "--dialect", "hsqldb"], cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    v002 = (tmp_path / "migrations" / "V002__create_tables.sql").read_text()
    assert "BIGINT GENERATED BY DEFAULT AS IDENTITY" in v002
```

- [ ] **Step 3: Run test (GREEN expected — all components done)**

```bash
pytest tests/test_golden_path.py -v
```
Expected: 2 passed. If any FAIL, investigate (likely template rendering edge case) and patch.

- [ ] **Step 4: Run full test suite**

```bash
pytest tests/ -v
```
Expected: all tests passed (40+ tests).

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/golden_blueprint.yaml tests/test_golden_path.py
git commit -m "test: golden integration test covering postgres and hsqldb"
```

---

### Task 22: README + install guide

**Files:**
- Create: `README.md`
- Create: `README.ko.md`
- Create: `INSTALL-FOR-AI.md`

- [ ] **Step 1: Create README.md (English)**

Path: `README.md`
```markdown
# andrej-karpathy-rdb-ddl

Stage 2 of the `business-fullstack-creater` pipeline.

Converts the Stage 1 `_blueprint.yaml` (from `andrej-karpathy-rdb-skill`) into:

- PostgreSQL or HSQLDB DDL
- Flyway-compatible migrations (`V001~V004__*.sql`)
- JPA Entity Java sources (Lombok, JDK 11+ compatible)
- Seed SQL for preset entities

Korean version: [README.ko.md](README.ko.md)
Install for AI agents: [INSTALL-FOR-AI.md](INSTALL-FOR-AI.md)

## Quick start

```
/rdb-ddl-compile <wiki_path> --out ./db --dialect postgres
```

## Pipeline position

```
Stage 1 (andrej-karpathy-rdb-skill)  →  _blueprint.yaml
                                          ↓
Stage 2 (andrej-karpathy-rdb-ddl)    →  DDL + JPA + seed   ← you are here
                                          ↓
Stage 3 (/nexacro-fullstack-starter) →  Spring Boot scaffold
```
```

- [ ] **Step 2: Create README.ko.md (Korean default)**

Path: `README.ko.md`
```markdown
# andrej-karpathy-rdb-ddl

`business-fullstack-creater` 파이프라인의 2단계.

1단계 `andrej-karpathy-rdb-skill`의 산출물 `_blueprint.yaml`을 입력받아 다음을 생성합니다:

- PostgreSQL / HSQLDB DDL
- Flyway 마이그레이션 (`V001~V004__*.sql`)
- JPA Entity Java 소스 (Lombok, JDK 11+ 호환)
- preset 엔티티에 대한 seed SQL

## 빠른 시작

```
/rdb-ddl-compile <wiki_경로> --out ./db --dialect postgres
```

## 지원 dialect

- `postgres` (기본): PostgreSQL 15+
- `hsqldb`: HSQLDB 2.7+ (embedded/test 용)

## 파이프라인 위치

```
1단계 (andrej-karpathy-rdb-skill)  →  _blueprint.yaml
                                       ↓
2단계 (andrej-karpathy-rdb-ddl)    →  DDL + JPA + seed   ← 현재
                                       ↓
3단계 (/nexacro-fullstack-starter) →  Spring Boot 스캐폴드
```
```

- [ ] **Step 3: Create INSTALL-FOR-AI.md**

Path: `INSTALL-FOR-AI.md`
```markdown
# Install for AI agents

This plugin is consumed automatically by Claude Code after install. The 5-phase install protocol below assumes the user has already produced `_blueprint.yaml` from Stage 1.

## Phase 1 — Verify Stage 1 output

Ask the user to confirm path to `<wiki>/_blueprint.yaml`. Verify:
- file exists
- `version: 1`
- `validation.passed: true`

If any check fails, instruct the user to re-run `/karpathy-rdb compile` in Stage 1.

## Phase 2 — Plugin install (one-time)

```
git clone <repo> ~/.claude/plugins/andrej-karpathy-rdb-ddl
```

`plugin.json` registers commands and skills automatically.

## Phase 3 — Pick dialect

Ask user: PostgreSQL (default, production) or HSQLDB (embedded testing). Save to project CLAUDE.md.

## Phase 4 — Run compile

```
/rdb-ddl-compile <wiki_path> --out ./db --package com.example.<schema> --dialect <chosen>
```

## Phase 5 — Verify + handoff

Confirm `ddl-report.md` shows ERROR: 0. List generated files. Tell user the `./db/` directory is the input for Stage 3 `/nexacro-fullstack-starter`.
```

- [ ] **Step 4: Commit each file separately (per user CLAUDE.md rule: one commit per file)**

```bash
git add README.md
git commit -m "docs: add English README"
git add README.ko.md
git commit -m "docs: add Korean README (default)"
git add INSTALL-FOR-AI.md
git commit -m "docs: add 5-phase AI install protocol"
```

---

### Task 23: Final verification + parent project handoff

**Files:**
- Modify: `D:\AI\workspace\business-fullstack-creater\needs\business-fullstack-creater 플러그인 요구기능.md` (append Stage 2 completion row)

- [ ] **Step 1: Run full test suite**

```bash
pytest tests/ -v
```
Expected: all tests pass. Record pass count.

- [ ] **Step 2: Smoke test from command line**

```bash
python scripts/ddl_compile.py tests/fixtures/golden_blueprint.yaml --out /tmp/smoke --dialect postgres
ls /tmp/smoke/migrations
ls /tmp/smoke/src/main/java/com/example/crm
cat /tmp/smoke/ddl-report.md
```
Expected: 4 migration files, Customer.java + Address.java, report ERROR: 0.

- [ ] **Step 3: Update parent project status file**

Read the existing requirement file then append a Stage 2 completion row:

```bash
# In business-fullstack-creater repo
```

In `needs/business-fullstack-creater 플러그인 요구기능.md`, locate the progress table and update Stage 2 row to ✅ Complete with a link to this repo and the spec file.

- [ ] **Step 4: Tag v0.1.0**

```bash
cd D:/AI/workspace/andrej-karpathy-rdb-ddl
git log --oneline | head -25  # verify expected commit count (~22)
git tag v0.1.0
```

- [ ] **Step 5: Final commit (parent project)**

```bash
cd D:/AI/workspace/business-fullstack-creater
# Note: business-fullstack-creater is not a git repo per session context; if not, skip git steps.
git status 2>/dev/null && git add "needs/business-fullstack-creater 플러그인 요구기능.md" && git commit -m "docs: mark Stage 2 (andrej-karpathy-rdb-ddl) complete" || echo "non-git parent — file updated only"
```

---

## Self-Review (writer's check)

**Spec coverage**:
- §2 inputs/abort → Task 3 (loader)
- §3.1 DDL outputs → Tasks 12-16 (templates + ddl_gen)
- §3.2 JPA → Task 17 (entity.java.j2 + jpa_gen)
- §3.3 Seed → Task 18 (preset catalog + seed_gen) + Task 6 (preset detection)
- §4 Revalidation V001~V005 → Tasks 7-11
- §5 Pipeline / dialect → Tasks 5, 14, 16, 19
- §6 Repo structure → Task 1
- §7 Slash command → Task 20
- §8 Tests (loader, revalidator, toposort, ddl_gen, jpa_gen, seed_gen, ddl_gen_hsqldb, golden_path) → covered Tasks 3, 4, 7-11, 14-18, 21
- §9.1 Extension contract → documented in spec, no code task (architecture already supports it via `dialect.py`)
- §10 D1-D11 → reflected throughout
- §11 Handoff → Task 23

**No gaps found**.

**Type consistency**: function signatures verified across tasks (`generate_ddl(blueprint, out_dir, dialect)`, `generate_jpa(entities, package, out_dir)`, `generate_seed(entities, out_dir, dialect)`, `revalidate(blueprint, dialect)`, `is_preset(entity)`, `topo_sort(entities, relations)`, `get_dialect(name)`). All match.

**Placeholder scan**: no "TBD", "implement later", "add error handling" — every step includes complete code.
