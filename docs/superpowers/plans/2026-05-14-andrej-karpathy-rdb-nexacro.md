# Stage 4 — `andrej-karpathy-rdb-nexacro` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stage 1 `_blueprint.yaml` + Stage 3 `endpoints.json` → entity 별 nexacro xfdl form, dsMenu seed, typedefinition patch 자동 생성 plugin.

**Architecture:** Python CLI + Jinja2 templates. 2단 폼 (Search + 편집 가능 Grid + 버튼) 을 entity 당 1개 emit. nexacro-fullstack-starter scaffold 위 overlay 방식. Stage 3 v0.1.4 가 emit 하는 `endpoints.json` 을 입력 계약으로 사용.

**Tech Stack:** Python 3.10+, Jinja2, PyYAML, pytest. 산출은 xfdl/xml (nexacro N v24).

**Spec:** `docs/superpowers/specs/2026-05-14-andrej-karpathy-rdb-nexacro-design.md`

**Repo locations:**
- Stage 3 (patch target): `D:\AI\workspace\andrej-karpathy-rdb-mybatis\`
- Stage 4 (new): `D:\AI\workspace\andrej-karpathy-rdb-nexacro\`

---

## Phase 0 — Stage 3 v0.1.4 predecessor patch (endpoints.json emit)

Stage 4 의 N002 (endpoints.json contract) validator 가 의존. 먼저 Stage 3 가 emit 하도록 패치.

### Task 0.1: endpoints.json emit 함수 + 단위 테스트

**Files:**
- Create: `D:\AI\workspace\andrej-karpathy-rdb-mybatis\scripts\endpoints_emitter.py`
- Test: `D:\AI\workspace\andrej-karpathy-rdb-mybatis\tests\test_endpoints_emitter.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_endpoints_emitter.py
import json
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

from endpoints_emitter import build_endpoints_payload, write_endpoints_json


def test_build_endpoints_payload_two_methods_per_entity():
    entities = [
        {"name": "customer", "table": "TB_CUSTOMER"},
        {"name": "customer_address", "table": "TB_CUSTOMER_ADDRESS"},
    ]
    payload = build_endpoints_payload(entities, context_path="/uiadapter")
    assert payload["version"] == 1
    assert payload["context_path"] == "/uiadapter"
    names = [e["name"] for e in payload["entities"]]
    assert names == ["customer", "customer_address"]
    cust = payload["entities"][0]
    assert cust["endpoint_base"] == "/customer"
    methods = [ep["method"] for ep in cust["endpoints"]]
    assert methods == ["select_datalist_map", "save_datalist_map"]
    assert cust["endpoints"][0]["http_path"] == "/customer/select_datalist_map.do"
    assert cust["endpoints"][0]["input"] == {"dsSearch": "param-dataset"}
    assert cust["endpoints"][0]["output"] == {"output1": "list-dataset"}
    assert cust["endpoints"][1]["input"] == {"dataList": "row-dispatch"}
    assert cust["endpoints"][1]["output"] == {}


def test_write_endpoints_json_round_trip(tmp_path):
    payload = {"version": 1, "context_path": "/x", "entities": []}
    p = write_endpoints_json(tmp_path, payload)
    assert p == tmp_path / "endpoints.json"
    assert json.loads(p.read_text(encoding="utf-8")) == payload
```

- [ ] **Step 2: Run test → FAIL (module not found)**

Run: `cd D:\AI\workspace\andrej-karpathy-rdb-mybatis && python -m pytest tests/test_endpoints_emitter.py -v`
Expected: ModuleNotFoundError

- [ ] **Step 3: Implement emitter**

```python
# scripts/endpoints_emitter.py
import json
import pathlib


def build_endpoints_payload(entities, context_path="/uiadapter"):
    out_entities = []
    for e in entities:
        name = e["name"]
        base = f"/{name}"
        out_entities.append({
            "name": name,
            "endpoint_base": base,
            "endpoints": [
                {
                    "method": "select_datalist_map",
                    "http_path": f"{base}/select_datalist_map.do",
                    "input":  {"dsSearch": "param-dataset"},
                    "output": {"output1": "list-dataset"},
                },
                {
                    "method": "save_datalist_map",
                    "http_path": f"{base}/save_datalist_map.do",
                    "input":  {"dataList": "row-dispatch"},
                    "output": {},
                },
            ],
        })
    return {
        "version": 1,
        "context_path": context_path,
        "entities": out_entities,
    }


def write_endpoints_json(out_root, payload):
    out = pathlib.Path(out_root) / "endpoints.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return out
```

- [ ] **Step 4: Run test → PASS**

Run: `cd D:\AI\workspace\andrej-karpathy-rdb-mybatis && python -m pytest tests/test_endpoints_emitter.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit (per-file)**

```bash
cd D:\AI\workspace\andrej-karpathy-rdb-mybatis
git add scripts/endpoints_emitter.py
git commit -m "feat(stage3): add endpoints_emitter for endpoints.json payload (v0.1.4 prep)"
git add tests/test_endpoints_emitter.py
git commit -m "test(stage3): unit tests for endpoints_emitter"
```

### Task 0.2: Wire emitter into compile.py

**Files:**
- Modify: `D:\AI\workspace\andrej-karpathy-rdb-mybatis\scripts\compile.py` (after `_emit_full_report` invocation)

- [ ] **Step 1: Write integration test**

```python
# tests/test_compile_endpoints_json.py
import json
import pathlib
import subprocess
import sys
import shutil

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_compile_emits_endpoints_json(tmp_path):
    # Copy golden fixture
    fx = ROOT / "tests" / "fixtures" / "golden_blueprint.yaml"
    ddl = ROOT / "tests" / "fixtures" / "golden_ddl"
    out = tmp_path / "backend"
    cmd = [
        sys.executable, str(ROOT / "scripts" / "compile.py"), "compile",
        "--blueprint", str(fx),
        "--ddl-dir",   str(ddl),
        "--out",       str(out),
        "--skip-compile",
        "--dry-run",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    ep = out / "endpoints.json"
    assert ep.exists()
    data = json.loads(ep.read_text(encoding="utf-8"))
    assert data["version"] == 1
    assert len(data["entities"]) >= 1
    methods = [m["method"] for m in data["entities"][0]["endpoints"]]
    assert "select_datalist_map" in methods and "save_datalist_map" in methods
```

> If a `golden_blueprint.yaml`/`golden_ddl` does not yet exist under `tests/fixtures/`, the previously‑passing E2E test (`test_e2e_compile_golden.py`) tells you where to point them. Match its inputs.

- [ ] **Step 2: Run test → FAIL (no endpoints.json)**

Run: `cd D:\AI\workspace\andrej-karpathy-rdb-mybatis && python -m pytest tests/test_compile_endpoints_json.py -v`
Expected: FileNotFoundError or AssertionError on `ep.exists()`

- [ ] **Step 3: Wire emitter into compile.py**

Open `scripts/compile.py`. Add import at top:
```python
from endpoints_emitter import build_endpoints_payload, write_endpoints_json
```

Then, in `main()`, immediately before the final `_emit_full_report(...)` call (around line 138), add:
```python
    endpoints_payload = build_endpoints_payload(sorted_entities, context_path="/uiadapter")
    write_endpoints_json(out_root, endpoints_payload)
    generated.append(str(out_root / "endpoints.json"))
```

Also wire into the `dry-run` branch (around line 95-102), immediately before `_emit_full_report` in that branch:
```python
        endpoints_payload = build_endpoints_payload(sorted_entities, context_path="/uiadapter")
        write_endpoints_json(out_root, endpoints_payload)
        generated.append(str(out_root / "endpoints.json"))
```

- [ ] **Step 4: Run test → PASS**

Run: `cd D:\AI\workspace\andrej-karpathy-rdb-mybatis && python -m pytest tests/test_compile_endpoints_json.py -v`
Expected: 1 passed

- [ ] **Step 5: Run full test suite → PASS**

Run: `cd D:\AI\workspace\andrej-karpathy-rdb-mybatis && python -m pytest -v`
Expected: all green (no regression)

- [ ] **Step 6: Commit**

```bash
cd D:\AI\workspace\andrej-karpathy-rdb-mybatis
git add scripts/compile.py
git commit -m "feat(stage3): wire endpoints_emitter into compile.py main + dry-run paths"
git add tests/test_compile_endpoints_json.py
git commit -m "test(stage3): integration test for endpoints.json emission"
```

### Task 0.3: Bump plugin version to v0.1.4 + tag

**Files:**
- Modify: `D:\AI\workspace\andrej-karpathy-rdb-mybatis\.claude\plugin.json` (version)
- Modify: `D:\AI\workspace\andrej-karpathy-rdb-mybatis\.claude\skills\karpathy-rdb-mybatis\references\output-layout.md` (add `endpoints.json` line)

- [ ] **Step 1: Edit plugin.json**

Change `"version": "0.1.3"` to `"version": "0.1.4"`.

- [ ] **Step 2: Append endpoints.json to output-layout.md**

Add the following row under the `src/main/resources/` section in `output-layout.md`:
```
endpoints.json              (project root — Stage 4 input contract, v0.1.4+)
```

- [ ] **Step 3: Commit per-file**

```bash
cd D:\AI\workspace\andrej-karpathy-rdb-mybatis
git add .claude/plugin.json
git commit -m "chore(stage3): bump version 0.1.3 → 0.1.4"
git add .claude/skills/karpathy-rdb-mybatis/references/output-layout.md
git commit -m "docs(stage3): document endpoints.json output (v0.1.4)"
git tag v0.1.4
```

---

## Phase 1 — Stage 4 plugin scaffold

### Task 1: Repo scaffold + plugin manifest

**Files:**
- Create: `D:\AI\workspace\andrej-karpathy-rdb-nexacro\.claude\plugin.json`
- Create: `D:\AI\workspace\andrej-karpathy-rdb-nexacro\.claude\commands\karpathy-rdb-nexacro.md`
- Create: `D:\AI\workspace\andrej-karpathy-rdb-nexacro\.claude\skills\karpathy-rdb-nexacro\SKILL.md`
- Create: `D:\AI\workspace\andrej-karpathy-rdb-nexacro\.gitignore`
- Create: `D:\AI\workspace\andrej-karpathy-rdb-nexacro\README.md`
- Create: `D:\AI\workspace\andrej-karpathy-rdb-nexacro\pyproject.toml`

- [ ] **Step 1: Create directory tree**

```powershell
$root = "D:\AI\workspace\andrej-karpathy-rdb-nexacro"
New-Item -ItemType Directory -Force $root, "$root\.claude\commands", "$root\.claude\skills\karpathy-rdb-nexacro\references", "$root\scripts", "$root\templates", "$root\tests\unit", "$root\tests\integration", "$root\tests\e2e", "$root\tests\fixtures\expected"
cd $root; git init
```

- [ ] **Step 2: Write `.claude/plugin.json`**

```json
{
  "name": "andrej-karpathy-rdb-nexacro",
  "version": "0.1.0",
  "description": "Stage 4 — Blueprint + endpoints.json → nexacro xfdl form codegen",
  "author": "business-fullstack-creater",
  "keywords": ["claude-code", "plugin", "nexacro", "xfdl", "codegen", "karpathy"],
  "claudeCode": { "minVersion": "2.0.0" },
  "entries": {
    "commands": ".claude/commands/",
    "skills": ".claude/skills/"
  }
}
```

- [ ] **Step 3: Write `.claude/commands/karpathy-rdb-nexacro.md`**

```markdown
---
name: karpathy-rdb-nexacro
description: Compile blueprint + endpoints.json → nexacro xfdl forms
argument-hint: compile --blueprint <path> --endpoints <path> --out <dir>
---

# /karpathy-rdb-nexacro

Generate nexacro xfdl forms from Stage 1 blueprint + Stage 3 endpoints.json.

## Usage

```
/karpathy-rdb-nexacro compile \
  --blueprint  <path>/_blueprint.yaml \
  --endpoints  <path>/endpoints.json \
  --out        <out-dir>
```

Optional flags: `--infer-endpoints`, `--frame {packageN|minimal}`, `--strict`, `--force`.

See SKILL.md for full reference.
```

- [ ] **Step 4: Write `.claude/skills/karpathy-rdb-nexacro/SKILL.md`** (stub — fleshed out in Task 2)

```markdown
---
name: karpathy-rdb-nexacro
description: Generates entity-per-form nexacro xfdl from blueprint + endpoints.json
---

# karpathy-rdb-nexacro

Stage 4 of the business-fullstack-creater pipeline. Consumes:
- Stage 1 `_blueprint.yaml`
- Stage 3 `endpoints.json` (v0.1.4+)

Emits xfdl forms + dsMenu seed + typedefinition patch ready to overlay on
`nexacro-fullstack-starter` scaffold.

See `references/` for input contracts, type matrix, and output layout.
```

- [ ] **Step 5: Write `.gitignore`**

```
__pycache__/
*.pyc
.pytest_cache/
.smoke/
out/
*.bak
```

- [ ] **Step 6: Write minimal `README.md`**

```markdown
# andrej-karpathy-rdb-nexacro

Stage 4 — nexacro xfdl form generator for the `business-fullstack-creater` pipeline.

Status: v0.1.0 (in development)

See `docs/superpowers/specs/2026-05-14-andrej-karpathy-rdb-nexacro-design.md` in the
parent `business-fullstack-creater` repo for the design contract.
```

- [ ] **Step 7: Write `pyproject.toml`**

```toml
[project]
name = "karpathy-rdb-nexacro"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = ["PyYAML>=6.0", "Jinja2>=3.1"]

[project.optional-dependencies]
test = ["pytest>=7.0"]

[tool.pytest.ini_options]
pythonpath = ["scripts"]
testpaths   = ["tests"]
```

- [ ] **Step 8: Commit per-file**

```bash
git add .claude/plugin.json && git commit -m "chore: scaffold plugin.json v0.1.0"
git add .claude/commands/karpathy-rdb-nexacro.md && git commit -m "feat: slash command stub"
git add .claude/skills/karpathy-rdb-nexacro/SKILL.md && git commit -m "docs: SKILL.md stub"
git add .gitignore README.md pyproject.toml
git commit -m "chore: gitignore + README + pyproject"
```

### Task 2: Reference docs

**Files:**
- Create: `.claude/skills/karpathy-rdb-nexacro/references/blueprint-input-contract.md`
- Create: `.claude/skills/karpathy-rdb-nexacro/references/endpoints-input-contract.md`
- Create: `.claude/skills/karpathy-rdb-nexacro/references/type-mapping-matrix.md`
- Create: `.claude/skills/karpathy-rdb-nexacro/references/form-layout.md`
- Create: `.claude/skills/karpathy-rdb-nexacro/references/overlay-policy.md`
- Create: `.claude/skills/karpathy-rdb-nexacro/references/output-layout.md`

- [ ] **Step 1: blueprint-input-contract.md**

```markdown
# Blueprint Input Contract (Stage 1 → Stage 4)

Source: `wiki/_blueprint.yaml` produced by `/karpathy-rdb compile`.

## Required top-level keys
- `version`: must equal `1`
- `project`: string
- `entities[]`: `{name, table, columns[], indexes?, constraints?}`
- `validation.passed`: must equal `true`

## Entity column shape (post nullable refactor)
```yaml
columns:
  - { name: customer_id, type: varchar(36), pk: true, nullable: false }
  - { name: name,        type: varchar(100), nullable: true }
```

## Hard rejects (Stage 4 N001)
- `version != 1`
- `validation.passed != true`
- Any entity with zero `pk: true` columns (N004)
```

- [ ] **Step 2: endpoints-input-contract.md**

```markdown
# Endpoints Input Contract (Stage 3 v0.1.4 → Stage 4)

Source: `<OUT_BACKEND>/endpoints.json`.

## Shape
```json
{
  "version": 1,
  "context_path": "/uiadapter",
  "entities": [
    {
      "name": "customer",
      "endpoint_base": "/customer",
      "endpoints": [
        {"method": "select_datalist_map", "http_path": "/customer/select_datalist_map.do",
         "input": {"dsSearch": "param-dataset"}, "output": {"output1": "list-dataset"}},
        {"method": "save_datalist_map", "http_path": "/customer/save_datalist_map.do",
         "input": {"dataList": "row-dispatch"}, "output": {}}
      ]
    }
  ]
}
```

## Hard rejects (Stage 4 N002)
- `version != 1`
- Any entity missing one of {select_datalist_map, save_datalist_map}
- Any entity in blueprint not present in endpoints.entities (N003)

## Infer mode (`--infer-endpoints`)
If endpoints.json is missing, synthesize from blueprint:
`endpoint_base = /<entity.name>`, two fixed methods, http_path = `<base>/<method>.do`.
```

- [ ] **Step 3: type-mapping-matrix.md** — copy the full table from spec §6 (verbatim).

- [ ] **Step 4: form-layout.md** — copy spec §5 layout description verbatim.

- [ ] **Step 5: overlay-policy.md** — describe `--force`/`.bak` policy and conflict rules from spec §8.

- [ ] **Step 6: output-layout.md**

```markdown
# Output Layout

```
<out>/
├── nxui/
│   ├── _form_/<entity>.xfdl
│   └── _datasets_/dsMenu.seed.xml
├── patches/
│   ├── typedefinition.patch.xml
│   └── typedefinition.merge.py
├── docs/
│   ├── nexacro-report.md
│   └── warnings.md
└── overlay.sh
```
```

- [ ] **Step 7: Commit per-file**

```bash
git add .claude/skills/karpathy-rdb-nexacro/references/blueprint-input-contract.md
git commit -m "docs(ref): blueprint input contract"
git add .claude/skills/karpathy-rdb-nexacro/references/endpoints-input-contract.md
git commit -m "docs(ref): endpoints input contract"
git add .claude/skills/karpathy-rdb-nexacro/references/type-mapping-matrix.md
git commit -m "docs(ref): PG → nexacro type mapping matrix"
git add .claude/skills/karpathy-rdb-nexacro/references/form-layout.md
git commit -m "docs(ref): 2-tier form layout (Search + Grid)"
git add .claude/skills/karpathy-rdb-nexacro/references/overlay-policy.md
git commit -m "docs(ref): overlay conflict policy"
git add .claude/skills/karpathy-rdb-nexacro/references/output-layout.md
git commit -m "docs(ref): output layout"
```

---

## Phase 2 — Loaders + validators

### Task 3: blueprint_loader (N001, N004)

**Files:**
- Create: `scripts/blueprint_loader.py`
- Create: `tests/fixtures/golden_blueprint.yaml`
- Create: `tests/unit/test_blueprint_loader.py`

- [ ] **Step 1: Write fixture `tests/fixtures/golden_blueprint.yaml`**

```yaml
version: 1
project: 고객관리
validation:
  passed: true
  errors: []
entities:
  - name: customer
    table: TB_CUSTOMER
    columns:
      - { name: customer_id, type: varchar(36),  pk: true,  nullable: false }
      - { name: name,        type: varchar(100), nullable: false }
      - { name: email,       type: varchar(200), nullable: true }
      - { name: active_yn,   type: char(1),      nullable: false }
      - { name: created_at,  type: timestamp,    nullable: false }
relations: []
business_rules: []
```

- [ ] **Step 2: Write failing test**

```python
# tests/unit/test_blueprint_loader.py
import pathlib
import pytest
from blueprint_loader import load_blueprint, BlueprintError

FX = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "golden_blueprint.yaml"


def test_load_golden_blueprint():
    bp = load_blueprint(FX)
    assert bp["version"] == 1
    assert bp["validation"]["passed"] is True
    assert bp["entities"][0]["name"] == "customer"


def test_n001_rejects_version_mismatch(tmp_path):
    p = tmp_path / "bp.yaml"
    p.write_text("version: 2\nentities: []\nvalidation: {passed: true}\n")
    with pytest.raises(BlueprintError, match="N001"):
        load_blueprint(p)


def test_n001_rejects_validation_false(tmp_path):
    p = tmp_path / "bp.yaml"
    p.write_text("version: 1\nentities: []\nvalidation: {passed: false}\n")
    with pytest.raises(BlueprintError, match="N001"):
        load_blueprint(p)


def test_n004_rejects_entity_without_pk(tmp_path):
    p = tmp_path / "bp.yaml"
    p.write_text(
        "version: 1\nvalidation: {passed: true}\n"
        "entities:\n"
        "  - name: x\n    table: T\n    columns:\n"
        "      - {name: c, type: varchar(10), nullable: true}\n"
    )
    with pytest.raises(BlueprintError, match="N004"):
        load_blueprint(p)
```

- [ ] **Step 3: Run → FAIL**

Run: `cd D:\AI\workspace\andrej-karpathy-rdb-nexacro && python -m pytest tests/unit/test_blueprint_loader.py -v`
Expected: ModuleNotFoundError

- [ ] **Step 4: Implement loader**

```python
# scripts/blueprint_loader.py
import pathlib
import yaml


class BlueprintError(Exception):
    pass


def load_blueprint(path):
    p = pathlib.Path(path)
    if not p.exists():
        raise BlueprintError(f"N001 blueprint not found: {p}")
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if data.get("version") != 1:
        raise BlueprintError(f"N001 unsupported version: {data.get('version')!r}")
    if not (data.get("validation") or {}).get("passed"):
        raise BlueprintError("N001 blueprint validation.passed != true")
    for e in data.get("entities") or []:
        pk_cols = [c for c in (e.get("columns") or []) if c.get("pk")]
        if not pk_cols:
            raise BlueprintError(f"N004 entity {e.get('name')!r} has no pk column")
    return data
```

- [ ] **Step 5: Run → PASS**

Run: `python -m pytest tests/unit/test_blueprint_loader.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add tests/fixtures/golden_blueprint.yaml
git commit -m "test(fixture): golden_blueprint.yaml for customer entity"
git add scripts/blueprint_loader.py
git commit -m "feat: blueprint_loader with N001/N004 validation"
git add tests/unit/test_blueprint_loader.py
git commit -m "test: blueprint_loader unit tests"
```

### Task 4: endpoints_loader (N002, N003, --infer)

**Files:**
- Create: `scripts/endpoints_loader.py`
- Create: `tests/fixtures/golden_endpoints.json`
- Create: `tests/unit/test_endpoints_loader.py`

- [ ] **Step 1: Write fixture `tests/fixtures/golden_endpoints.json`**

```json
{
  "version": 1,
  "context_path": "/uiadapter",
  "entities": [
    {
      "name": "customer",
      "endpoint_base": "/customer",
      "endpoints": [
        {"method": "select_datalist_map", "http_path": "/customer/select_datalist_map.do",
         "input": {"dsSearch": "param-dataset"}, "output": {"output1": "list-dataset"}},
        {"method": "save_datalist_map", "http_path": "/customer/save_datalist_map.do",
         "input": {"dataList": "row-dispatch"}, "output": {}}
      ]
    }
  ]
}
```

- [ ] **Step 2: Write failing test**

```python
# tests/unit/test_endpoints_loader.py
import json
import pathlib
import pytest
from endpoints_loader import load_endpoints, infer_endpoints, EndpointsError

FX = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "golden_endpoints.json"


def test_load_golden():
    data = load_endpoints(FX)
    assert data["version"] == 1
    assert data["entities"][0]["name"] == "customer"


def test_n002_rejects_version(tmp_path):
    p = tmp_path / "ep.json"
    p.write_text('{"version": 2, "entities": []}')
    with pytest.raises(EndpointsError, match="N002"):
        load_endpoints(p)


def test_n002_rejects_missing_method(tmp_path):
    p = tmp_path / "ep.json"
    p.write_text(json.dumps({
        "version": 1,
        "entities": [{"name": "x", "endpoint_base": "/x",
                      "endpoints": [{"method": "select_datalist_map",
                                     "http_path": "/x/select_datalist_map.do",
                                     "input": {}, "output": {}}]}],
    }))
    with pytest.raises(EndpointsError, match="N002"):
        load_endpoints(p)


def test_infer_from_blueprint_entities():
    inferred = infer_endpoints(
        [{"name": "customer"}, {"name": "customer_address"}],
        context_path="/uiadapter",
    )
    assert inferred["version"] == 1
    assert [e["name"] for e in inferred["entities"]] == ["customer", "customer_address"]
    assert inferred["entities"][0]["endpoints"][0]["http_path"] == "/customer/select_datalist_map.do"


def test_n003_cross_check_entities_match():
    from endpoints_loader import cross_check
    ep = {"entities": [{"name": "customer"}]}
    cross_check([{"name": "customer"}], ep)  # OK
    with pytest.raises(EndpointsError, match="N003"):
        cross_check([{"name": "customer"}, {"name": "order"}], ep)
```

- [ ] **Step 3: Run → FAIL**

Run: `python -m pytest tests/unit/test_endpoints_loader.py -v`
Expected: ModuleNotFoundError

- [ ] **Step 4: Implement loader**

```python
# scripts/endpoints_loader.py
import json
import pathlib

REQUIRED_METHODS = {"select_datalist_map", "save_datalist_map"}


class EndpointsError(Exception):
    pass


def load_endpoints(path):
    p = pathlib.Path(path)
    if not p.exists():
        raise EndpointsError(f"N002 endpoints.json not found: {p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    if data.get("version") != 1:
        raise EndpointsError(f"N002 unsupported version: {data.get('version')!r}")
    for e in data.get("entities") or []:
        methods = {ep.get("method") for ep in e.get("endpoints") or []}
        missing = REQUIRED_METHODS - methods
        if missing:
            raise EndpointsError(
                f"N002 entity {e.get('name')!r} missing methods: {sorted(missing)}"
            )
    return data


def infer_endpoints(entities, context_path="/uiadapter"):
    out = []
    for e in entities:
        name = e["name"]
        base = f"/{name}"
        out.append({
            "name": name,
            "endpoint_base": base,
            "endpoints": [
                {"method": "select_datalist_map",
                 "http_path": f"{base}/select_datalist_map.do",
                 "input": {"dsSearch": "param-dataset"},
                 "output": {"output1": "list-dataset"}},
                {"method": "save_datalist_map",
                 "http_path": f"{base}/save_datalist_map.do",
                 "input": {"dataList": "row-dispatch"},
                 "output": {}},
            ],
        })
    return {"version": 1, "context_path": context_path, "entities": out}


def cross_check(blueprint_entities, endpoints_payload):
    bp_names = {e["name"] for e in blueprint_entities}
    ep_names = {e["name"] for e in endpoints_payload.get("entities") or []}
    only_bp = bp_names - ep_names
    only_ep = ep_names - bp_names
    if only_bp or only_ep:
        raise EndpointsError(
            f"N003 entity sets diverge — blueprint-only={sorted(only_bp)}, "
            f"endpoints-only={sorted(only_ep)}"
        )
```

- [ ] **Step 5: Run → PASS**

Run: `python -m pytest tests/unit/test_endpoints_loader.py -v`
Expected: 5 passed

- [ ] **Step 6: Commit**

```bash
git add tests/fixtures/golden_endpoints.json
git commit -m "test(fixture): golden_endpoints.json"
git add scripts/endpoints_loader.py
git commit -m "feat: endpoints_loader with N002/N003 + infer fallback"
git add tests/unit/test_endpoints_loader.py
git commit -m "test: endpoints_loader unit tests"
```

### Task 5: revalidator (N005 search candidate, N006 XML wellformed)

**Files:**
- Create: `scripts/revalidator.py`
- Create: `tests/unit/test_revalidator.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_revalidator.py
import pathlib
import pytest
from revalidator import (
    check_search_candidates, check_xml_wellformed, RevalidationError
)


def test_n005_search_candidates_ok():
    e = {"name": "customer", "columns": [
        {"name": "id", "type": "varchar(36)", "pk": True, "nullable": False},
        {"name": "name", "type": "varchar(100)", "nullable": False},
    ]}
    check_search_candidates([e])  # OK


def test_n005_rejects_no_searchable_columns():
    e = {"name": "x", "columns": [
        {"name": "id", "type": "varchar(36)", "pk": True, "nullable": True},
        {"name": "memo", "type": "text", "nullable": True},
    ]}
    with pytest.raises(RevalidationError, match="N005"):
        check_search_candidates([e])


def test_n006_xml_wellformed_pass(tmp_path):
    f = tmp_path / "a.xml"
    f.write_text("<root><a/></root>")
    check_xml_wellformed([f])  # OK


def test_n006_xml_wellformed_fail(tmp_path):
    f = tmp_path / "b.xml"
    f.write_text("<root><a></root>")
    with pytest.raises(RevalidationError, match="N006"):
        check_xml_wellformed([f])
```

- [ ] **Step 2: Run → FAIL**

Run: `python -m pytest tests/unit/test_revalidator.py -v`
Expected: ModuleNotFoundError

- [ ] **Step 3: Implement revalidator**

```python
# scripts/revalidator.py
import pathlib
import xml.etree.ElementTree as ET


class RevalidationError(Exception):
    pass


def check_search_candidates(entities):
    for e in entities:
        cands = [c for c in (e.get("columns") or [])
                 if c.get("pk") or c.get("nullable") is False]
        if not cands:
            raise RevalidationError(
                f"N005 entity {e.get('name')!r} has no searchable columns "
                "(no PK and no NOT NULL columns)"
            )


def check_xml_wellformed(paths):
    bad = []
    for p in paths:
        p = pathlib.Path(p)
        try:
            ET.parse(p)
        except ET.ParseError as e:
            bad.append(f"{p}: {e}")
    if bad:
        raise RevalidationError(
            "N006 malformed XML:\n  " + "\n  ".join(bad)
        )
```

- [ ] **Step 4: Run → PASS**

Run: `python -m pytest tests/unit/test_revalidator.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/revalidator.py
git commit -m "feat: revalidator N005/N006 (search candidate + XML well-formed)"
git add tests/unit/test_revalidator.py
git commit -m "test: revalidator unit tests"
```

---

## Phase 3 — Type mapper

### Task 6: type_mapper — fixed matrix + *_yn convention

**Files:**
- Create: `scripts/type_mapper.py`
- Create: `tests/unit/test_type_mapper.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_type_mapper.py
import pytest
from type_mapper import map_column, MapResult


def test_bigserial_pk_readonly():
    r = map_column({"name": "id", "type": "bigserial", "pk": True, "nullable": False})
    assert r.dataset_type == "BIGDECIMAL"
    assert r.grid_edittype == "none"
    assert r.grid_displaytype == "number"
    assert r.search_component == "Edit"


def test_varchar_default():
    r = map_column({"name": "name", "type": "varchar(100)", "nullable": False})
    assert r.dataset_type == "STRING"
    assert r.size == 100
    assert r.grid_edittype == "text"
    assert r.search_component == "Edit"


def test_char1_yn_convention():
    r = map_column({"name": "active_yn", "type": "char(1)", "nullable": False})
    assert r.dataset_type == "STRING"
    assert r.size == 1
    assert r.grid_edittype == "combo"
    assert r.grid_displaytype == "combotext"
    assert r.search_component == "Combo"
    assert r.combo_options == [("Y", "Y"), ("N", "N")]


def test_char1_non_yn_falls_to_text():
    r = map_column({"name": "grade", "type": "char(1)", "nullable": True})
    assert r.grid_edittype == "text"
    assert r.search_component == "Edit"


def test_numeric():
    r = map_column({"name": "amount", "type": "numeric(15,2)", "nullable": False})
    assert r.dataset_type == "BIGDECIMAL"
    assert r.grid_edittype == "masknumber"
    assert r.grid_displaytype == "number"


def test_boolean():
    r = map_column({"name": "is_locked", "type": "boolean", "nullable": False})
    assert r.grid_edittype == "checkbox"
    assert r.search_component == "Combo"


def test_date():
    r = map_column({"name": "birth_dt", "type": "date", "nullable": True})
    assert r.size == 8
    assert r.grid_edittype == "date"
    assert r.search_component == "Calendar"


def test_timestamp():
    r = map_column({"name": "created_at", "type": "timestamp", "nullable": False})
    assert r.size == 14
    assert r.grid_edittype == "date"


def test_json_search_excluded():
    r = map_column({"name": "payload", "type": "jsonb", "nullable": True})
    assert r.search_component is None  # excluded
    assert r.grid_edittype == "text"


def test_unknown_falls_back():
    r = map_column({"name": "xy", "type": "geometry", "nullable": True})
    assert r.dataset_type == "STRING"
    assert r.size == 100
    assert r.grid_edittype == "text"
    assert r.fallback is True
```

- [ ] **Step 2: Run → FAIL**

Run: `python -m pytest tests/unit/test_type_mapper.py -v`
Expected: ModuleNotFoundError

- [ ] **Step 3: Implement mapper**

```python
# scripts/type_mapper.py
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MapResult:
    dataset_type: str
    size: Optional[int] = None
    search_component: Optional[str] = None  # None = exclude from search
    grid_edittype: str = "text"
    grid_displaytype: str = "text"
    combo_options: list = field(default_factory=list)
    fallback: bool = False


_VARCHAR_RE  = re.compile(r"^varchar\((\d+)\)$", re.I)
_CHAR_RE     = re.compile(r"^char\((\d+)\)$", re.I)
_NUMERIC_RE  = re.compile(r"^(numeric|decimal)\((\d+)(?:,\d+)?\)$", re.I)


def map_column(col):
    name = col["name"]
    t = (col.get("type") or "").strip().lower()
    pk = bool(col.get("pk"))

    if t in {"bigserial", "serial", "bigint", "integer", "int", "int4", "int8"}:
        return MapResult(
            dataset_type="BIGDECIMAL",
            search_component="Edit",
            grid_edittype="none" if pk else "masknumber",
            grid_displaytype="number",
        )

    m = _VARCHAR_RE.match(t)
    if m:
        return MapResult(
            dataset_type="STRING", size=int(m.group(1)),
            search_component="Edit", grid_edittype="text", grid_displaytype="text",
        )
    if t == "text":
        return MapResult(
            dataset_type="STRING", size=4000,
            search_component="Edit", grid_edittype="text", grid_displaytype="text",
        )

    m = _CHAR_RE.match(t)
    if m:
        size = int(m.group(1))
        if size == 1 and name.lower().endswith("_yn"):
            return MapResult(
                dataset_type="STRING", size=1,
                search_component="Combo",
                grid_edittype="combo", grid_displaytype="combotext",
                combo_options=[("Y", "Y"), ("N", "N")],
            )
        return MapResult(
            dataset_type="STRING", size=size,
            search_component="Edit", grid_edittype="text", grid_displaytype="text",
        )

    m = _NUMERIC_RE.match(t)
    if m:
        precision = int(m.group(2))
        return MapResult(
            dataset_type="BIGDECIMAL", size=precision,
            search_component="Edit",
            grid_edittype="masknumber", grid_displaytype="number",
        )

    if t == "boolean":
        return MapResult(
            dataset_type="STRING", size=1,
            search_component="Combo",
            grid_edittype="checkbox", grid_displaytype="checkbox",
        )

    if t == "date":
        return MapResult(
            dataset_type="STRING", size=8,
            search_component="Calendar",
            grid_edittype="date", grid_displaytype="date",
        )

    if t in {"timestamp", "timestamptz"}:
        return MapResult(
            dataset_type="STRING", size=14,
            search_component="Calendar",
            grid_edittype="date", grid_displaytype="date",
        )

    if t == "time":
        return MapResult(
            dataset_type="STRING", size=6,
            search_component="Edit", grid_edittype="mask", grid_displaytype="text",
        )

    if t in {"json", "jsonb"}:
        return MapResult(
            dataset_type="STRING", size=4000,
            search_component=None,  # excluded
            grid_edittype="text", grid_displaytype="text",
        )

    if t == "uuid":
        return MapResult(
            dataset_type="STRING", size=36,
            search_component="Edit",
            grid_edittype="none" if pk else "text", grid_displaytype="text",
        )

    return MapResult(
        dataset_type="STRING", size=100,
        search_component="Edit", grid_edittype="text", grid_displaytype="text",
        fallback=True,
    )
```

- [ ] **Step 4: Run → PASS**

Run: `python -m pytest tests/unit/test_type_mapper.py -v`
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/type_mapper.py
git commit -m "feat: type_mapper PG → nexacro fixed matrix + *_yn convention"
git add tests/unit/test_type_mapper.py
git commit -m "test: type_mapper covers 12 categories + fallback"
```

---

## Phase 4 — Templates + composer

### Task 7: dataset + search/grid fragment templates

**Files:**
- Create: `templates/dataset.xml.j2`
- Create: `templates/search_field.xml.j2`
- Create: `templates/grid_format.xml.j2`
- Create: `tests/unit/test_template_fragments.py`

- [ ] **Step 1: Write `templates/dataset.xml.j2`**

```xml
{# Renders a single <Dataset> with column metadata #}
<Dataset id="{{ ds_id }}">
  <ColumnInfo>
{%- for col in columns %}
    <Column id="{{ col.name }}" type="{{ col.dataset_type }}"{% if col.size %} size="{{ col.size }}"{% endif %}/>
{%- endfor %}
  </ColumnInfo>
{%- if rows %}
  <Rows>
{%- for row in rows %}
    <Row>
{%- for k, v in row.items() %}
      <Col id="{{ k }}">{{ v }}</Col>
{%- endfor %}
    </Row>
{%- endfor %}
  </Rows>
{%- endif %}
</Dataset>
```

- [ ] **Step 2: Write `templates/search_field.xml.j2`**

```xml
{# Renders one search field row #}
{%- if comp == "Calendar" %}
<Static id="stt_{{ col_name }}" text="{{ label }}" left="{{ x }}" top="{{ y }}" width="80" height="24"/>
<Calendar id="cal_{{ col_name }}" left="{{ x + 84 }}" top="{{ y }}" width="120" height="24"/>
{%- elif comp == "Combo" %}
<Static id="stt_{{ col_name }}" text="{{ label }}" left="{{ x }}" top="{{ y }}" width="80" height="24"/>
<Combo id="cmb_{{ col_name }}" left="{{ x + 84 }}" top="{{ y }}" width="120" height="24" innerdataset="ds_{{ col_name }}_codes" codecolumn="code" datacolumn="name"/>
{%- else %}
<Static id="stt_{{ col_name }}" text="{{ label }}" left="{{ x }}" top="{{ y }}" width="80" height="24"/>
<Edit id="edt_{{ col_name }}" left="{{ x + 84 }}" top="{{ y }}" width="160" height="24"/>
{%- endif %}
```

- [ ] **Step 3: Write `templates/grid_format.xml.j2`**

```xml
<Format id="default">
  <Columns>
{%- for col in columns %}
    <Column size="{{ col.size or 120 }}"/>
{%- endfor %}
  </Columns>
  <Rows>
    <Row size="24" band="head"/>
    <Row size="24"/>
  </Rows>
  <Band id="head">
{%- for col in columns %}
    <Cell col="{{ loop.index0 }}" text="{{ col.label }}"/>
{%- endfor %}
  </Band>
  <Band id="body">
{%- for col in columns %}
    <Cell col="{{ loop.index0 }}" text="bind:{{ col.name }}" edittype="{{ col.grid_edittype }}" displaytype="{{ col.grid_displaytype }}"/>
{%- endfor %}
  </Band>
</Format>
```

- [ ] **Step 4: Write failing test**

```python
# tests/unit/test_template_fragments.py
import pathlib
from jinja2 import Environment, FileSystemLoader

ROOT = pathlib.Path(__file__).resolve().parents[2]
ENV = Environment(
    loader=FileSystemLoader(ROOT / "templates"),
    trim_blocks=True, lstrip_blocks=True,
    keep_trailing_newline=False,
)


def test_dataset_render():
    tpl = ENV.get_template("dataset.xml.j2")
    out = tpl.render(ds_id="dsCustomer", columns=[
        {"name": "id", "dataset_type": "BIGDECIMAL", "size": None},
        {"name": "name", "dataset_type": "STRING", "size": 100},
    ], rows=None)
    assert '<Dataset id="dsCustomer">' in out
    assert '<Column id="id" type="BIGDECIMAL"/>' in out
    assert '<Column id="name" type="STRING" size="100"/>' in out


def test_grid_format_render():
    tpl = ENV.get_template("grid_format.xml.j2")
    out = tpl.render(columns=[
        {"name": "id", "label": "ID", "size": 80,
         "grid_edittype": "none", "grid_displaytype": "number"},
        {"name": "name", "label": "이름", "size": 200,
         "grid_edittype": "text", "grid_displaytype": "text"},
    ])
    assert 'text="bind:id"' in out
    assert 'edittype="none"' in out
    assert 'edittype="text"' in out
    assert 'text="이름"' in out


def test_search_field_calendar():
    tpl = ENV.get_template("search_field.xml.j2")
    out = tpl.render(comp="Calendar", col_name="created_at", label="등록일",
                     x=10, y=10)
    assert "Calendar" in out and "cal_created_at" in out
```

- [ ] **Step 5: Run → PASS** (templates already on disk)

Run: `python -m pytest tests/unit/test_template_fragments.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit per-file**

```bash
git add templates/dataset.xml.j2
git commit -m "feat(tpl): dataset.xml fragment"
git add templates/search_field.xml.j2
git commit -m "feat(tpl): search_field.xml fragment"
git add templates/grid_format.xml.j2
git commit -m "feat(tpl): grid_format.xml fragment with edittype/displaytype"
git add tests/unit/test_template_fragments.py
git commit -m "test: template fragments"
```

### Task 8: form.xfdl.j2 main template

**Files:**
- Create: `templates/form.xfdl.j2`

- [ ] **Step 1: Write `templates/form.xfdl.j2`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<FDL version="2.0">
<Form id="{{ form_id }}" width="900" height="620" titletext="{{ title }}">
  <Layout>
    <!-- Search panel (top, 60px) -->
    <Static id="ttl_search" left="10" top="6" width="120" height="20" text="검색조건" cssclass="sta_WF_Title"/>
    {{ search_fields | indent(4) }}
    <Button id="btn_search" left="780" top="20" width="80" height="24" text="조회" onclick="fn_search"/>

    <!-- Grid (middle, 520px) -->
    <Grid id="grd_main" left="10" top="70" width="880" height="500"
          binddataset="ds{{ entity_pascal }}" autofittype="col" useinputpanel="false">
{{ grid_format | indent(6) }}
    </Grid>

    <!-- Action buttons (bottom) -->
    <Button id="btn_add"  left="620" top="580" width="80" height="28" text="추가"   onclick="fn_add"/>
    <Button id="btn_del"  left="710" top="580" width="80" height="28" text="삭제"   onclick="fn_delete"/>
    <Button id="btn_save" left="800" top="580" width="80" height="28" text="저장"   onclick="fn_save"/>
  </Layout>

  <Objects>
{{ datasets | indent(4) }}
  </Objects>

  <Script type="xscript5.1"><![CDATA[
this.fn_search = function() {
  this.transaction("select",
    "Svc{{ entity_pascal }}::{{ select_path }}",
    "dsSearch=dsSearch",
    "output1=ds{{ entity_pascal }}",
    "", "fn_callback");
};

this.fn_add = function() {
  var n = this.ds{{ entity_pascal }}.addRow();
  this.grd_main.setCellPos(0);
};

this.fn_delete = function() {
  var r = this.ds{{ entity_pascal }}.rowposition;
  if (r < 0) return;
  this.ds{{ entity_pascal }}.deleteRow(r);
};

this.fn_save = function() {
  if (this.ds{{ entity_pascal }}.getRowCountNF() === 0) {
    alert("저장할 행이 없습니다.");
    return;
  }
  this.transaction("save",
    "Svc{{ entity_pascal }}::{{ save_path }}",
    "",
    "",
    "dataList=ds{{ entity_pascal }}:U",
    "fn_callback");
};

this.fn_callback = function(svcId, errCd, errMsg) {
  if (errCd < 0) { alert(errMsg); return; }
  if (svcId === "save") this.fn_search();
};
  ]]></Script>
</Form>
</FDL>
```

- [ ] **Step 2: Commit**

```bash
git add templates/form.xfdl.j2
git commit -m "feat(tpl): form.xfdl 2-tier (Search + editable Grid + buttons)"
```

### Task 9: form_composer

**Files:**
- Create: `scripts/form_composer.py`
- Create: `tests/integration/test_form_composer.py`

- [ ] **Step 1: Write failing test**

```python
# tests/integration/test_form_composer.py
import pathlib
import xml.etree.ElementTree as ET
from form_composer import compose_form


def test_compose_form_for_customer():
    entity = {
        "name": "customer",
        "table": "TB_CUSTOMER",
        "columns": [
            {"name": "customer_id", "type": "varchar(36)", "pk": True,  "nullable": False},
            {"name": "name",        "type": "varchar(100)",              "nullable": False},
            {"name": "email",       "type": "varchar(200)",              "nullable": True},
            {"name": "active_yn",   "type": "char(1)",                   "nullable": False},
            {"name": "created_at",  "type": "timestamp",                 "nullable": False},
        ],
    }
    endpoints = {
        "endpoint_base": "/customer",
        "endpoints": [
            {"method": "select_datalist_map", "http_path": "/customer/select_datalist_map.do"},
            {"method": "save_datalist_map",   "http_path": "/customer/save_datalist_map.do"},
        ],
    }
    xfdl = compose_form(entity, endpoints)
    # well-formed XML
    root = ET.fromstring(xfdl)
    assert root.tag == "FDL"
    # main dataset id appears
    assert 'id="dsCustomer"' in xfdl
    # dsSearch dataset appears
    assert 'id="dsSearch"' in xfdl
    # *_yn rendered as combo
    assert 'edittype="combo"' in xfdl
    # PK is readonly
    assert 'edittype="none"' in xfdl
    # service path embedded
    assert "/customer/select_datalist_map.do" in xfdl
    assert "/customer/save_datalist_map.do" in xfdl
```

- [ ] **Step 2: Run → FAIL**

Run: `python -m pytest tests/integration/test_form_composer.py -v`
Expected: ModuleNotFoundError

- [ ] **Step 3: Implement composer**

```python
# scripts/form_composer.py
import pathlib
from jinja2 import Environment, FileSystemLoader
from type_mapper import map_column

TEMPLATES = pathlib.Path(__file__).resolve().parents[1] / "templates"
ENV = Environment(
    loader=FileSystemLoader(TEMPLATES),
    trim_blocks=True, lstrip_blocks=True,
    keep_trailing_newline=False,
)


def _pascal(name):
    return "".join(p.capitalize() for p in name.split("_"))


def _search_columns(entity):
    return [c for c in entity["columns"]
            if c.get("pk") or c.get("nullable") is False]


def _label(col_name):
    return col_name.replace("_", " ").title()


def compose_form(entity, endpoints):
    pascal = _pascal(entity["name"])
    cols = []
    for c in entity["columns"]:
        m = map_column(c)
        cols.append({
            "name": c["name"],
            "label": _label(c["name"]),
            "dataset_type": m.dataset_type,
            "size": m.size,
            "grid_edittype": m.grid_edittype,
            "grid_displaytype": m.grid_displaytype,
            "search_component": m.search_component,
        })

    search_cols = []
    for c in _search_columns(entity):
        m = map_column(c)
        if m.search_component is None:
            continue
        search_cols.append({
            "name": c["name"],
            "label": _label(c["name"]),
            "dataset_type": m.dataset_type,
            "size": m.size,
            "search_component": m.search_component,
        })

    # Datasets fragment (dsSearch + ds{Pascal})
    ds_tpl = ENV.get_template("dataset.xml.j2")
    datasets_xml = "\n".join([
        ds_tpl.render(ds_id="dsSearch", columns=search_cols, rows=None),
        ds_tpl.render(ds_id=f"ds{pascal}", columns=cols, rows=None),
    ])

    # Search fragment
    sf_tpl = ENV.get_template("search_field.xml.j2")
    pieces = []
    x = 140
    for sc in search_cols:
        pieces.append(sf_tpl.render(
            comp=sc["search_component"],
            col_name=sc["name"],
            label=sc["label"],
            x=x, y=20,
        ))
        x += 260
    search_fields = "\n".join(pieces) if pieces else ""

    # Grid format
    gf_tpl = ENV.get_template("grid_format.xml.j2")
    grid_format = gf_tpl.render(columns=cols)

    # Resolve paths
    sel_path = next(e["http_path"] for e in endpoints["endpoints"]
                    if e["method"] == "select_datalist_map")
    sav_path = next(e["http_path"] for e in endpoints["endpoints"]
                    if e["method"] == "save_datalist_map")

    # Main form
    form_tpl = ENV.get_template("form.xfdl.j2")
    return form_tpl.render(
        form_id=entity["name"],
        title=f"{pascal} 관리",
        entity_pascal=pascal,
        search_fields=search_fields,
        grid_format=grid_format,
        datasets=datasets_xml,
        select_path=sel_path,
        save_path=sav_path,
    )
```

- [ ] **Step 4: Run → PASS**

Run: `python -m pytest tests/integration/test_form_composer.py -v`
Expected: 1 passed

- [ ] **Step 5: Commit per-file**

```bash
git add scripts/form_composer.py
git commit -m "feat: form_composer assembles dsSearch + ds<Entity> + Grid + Script"
git add tests/integration/test_form_composer.py
git commit -m "test(integration): form_composer covers customer fixture"
```

### Task 10: golden customer.xfdl byte-exact fixture

**Files:**
- Create: `tests/fixtures/expected/customer.xfdl` (generated then checked in)
- Create: `tests/integration/test_golden_customer.py`

- [ ] **Step 1: Generate the candidate xfdl and inspect**

Run from repo root:
```powershell
python -c "from scripts.form_composer import compose_form; import json, pathlib, yaml; bp=yaml.safe_load(open('tests/fixtures/golden_blueprint.yaml',encoding='utf-8')); ep=json.load(open('tests/fixtures/golden_endpoints.json',encoding='utf-8')); ent=bp['entities'][0]; eps=ep['entities'][0]; print(compose_form(ent, eps))" > tests/fixtures/expected/customer.xfdl
```

> Open the file. If anything looks wrong, fix the template or composer first — then regenerate. The committed file is the golden.

- [ ] **Step 2: Write golden test**

```python
# tests/integration/test_golden_customer.py
import json
import pathlib
import yaml
from form_composer import compose_form

ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_golden_customer_xfdl_byte_exact():
    bp = yaml.safe_load((ROOT / "tests" / "fixtures" / "golden_blueprint.yaml").read_text(encoding="utf-8"))
    ep = json.loads((ROOT / "tests" / "fixtures" / "golden_endpoints.json").read_text(encoding="utf-8"))
    got = compose_form(bp["entities"][0], ep["entities"][0])
    expected = (ROOT / "tests" / "fixtures" / "expected" / "customer.xfdl").read_text(encoding="utf-8")
    assert got == expected
```

- [ ] **Step 3: Run → PASS**

Run: `python -m pytest tests/integration/test_golden_customer.py -v`
Expected: 1 passed

- [ ] **Step 4: Commit**

```bash
git add tests/fixtures/expected/customer.xfdl
git commit -m "test(fixture): golden expected/customer.xfdl"
git add tests/integration/test_golden_customer.py
git commit -m "test(integration): golden customer.xfdl byte-exact regression"
```

---

## Phase 5 — Auxiliary outputs

### Task 11: menu_dataset_gen + template

**Files:**
- Create: `templates/menu_dataset.xml.j2`
- Create: `scripts/menu_dataset_gen.py`
- Create: `tests/unit/test_menu_dataset.py`

> **Schema assumption (spec §13):** dsMenu rows have keys `{menu_id, menu_pid, menu_nm, form_url, level}`. Verify against `nexacro-project-maker` packageN scaffold's `frameLeft.xfdl` before running e2e. If actual schema differs, only this template + generator change — no impact on form.xfdl.

- [ ] **Step 1: Write template**

```xml
{# templates/menu_dataset.xml.j2 #}
<Dataset id="dsMenu">
  <ColumnInfo>
    <Column id="menu_id"  type="STRING" size="40"/>
    <Column id="menu_pid" type="STRING" size="40"/>
    <Column id="menu_nm"  type="STRING" size="100"/>
    <Column id="form_url" type="STRING" size="200"/>
    <Column id="level"    type="INT"    size="2"/>
  </ColumnInfo>
  <Rows>
{%- for row in rows %}
    <Row>
      <Col id="menu_id">{{ row.menu_id }}</Col>
      <Col id="menu_pid">{{ row.menu_pid }}</Col>
      <Col id="menu_nm">{{ row.menu_nm }}</Col>
      <Col id="form_url">{{ row.form_url }}</Col>
      <Col id="level">{{ row.level }}</Col>
    </Row>
{%- endfor %}
  </Rows>
</Dataset>
```

- [ ] **Step 2: Write failing test**

```python
# tests/unit/test_menu_dataset.py
import xml.etree.ElementTree as ET
from menu_dataset_gen import build_menu_rows, render_menu_dataset


def test_build_rows_one_entity():
    rows = build_menu_rows([{"name": "customer"}])
    assert rows == [
        {"menu_id": "MENU_CUSTOMER", "menu_pid": "ROOT",
         "menu_nm": "Customer", "form_url": "_form_::customer.xfdl", "level": 1},
    ]


def test_render_emits_one_row_per_entity():
    rows = build_menu_rows([{"name": "customer"}, {"name": "customer_address"}])
    xml = render_menu_dataset(rows)
    root = ET.fromstring(xml)
    assert root.tag == "Dataset"
    assert len(root.find("Rows").findall("Row")) == 2
```

- [ ] **Step 3: Run → FAIL**

Run: `python -m pytest tests/unit/test_menu_dataset.py -v`
Expected: ModuleNotFoundError

- [ ] **Step 4: Implement**

```python
# scripts/menu_dataset_gen.py
import pathlib
from jinja2 import Environment, FileSystemLoader

TEMPLATES = pathlib.Path(__file__).resolve().parents[1] / "templates"
ENV = Environment(loader=FileSystemLoader(TEMPLATES),
                  trim_blocks=True, lstrip_blocks=True,
                  keep_trailing_newline=False)


def _pascal(name):
    return "".join(p.capitalize() for p in name.split("_"))


def build_menu_rows(entities, parent="ROOT", level=1):
    rows = []
    for e in entities:
        name = e["name"]
        rows.append({
            "menu_id":  f"MENU_{name.upper()}",
            "menu_pid": parent,
            "menu_nm":  _pascal(name),
            "form_url": f"_form_::{name}.xfdl",
            "level":    level,
        })
    return rows


def render_menu_dataset(rows):
    tpl = ENV.get_template("menu_dataset.xml.j2")
    return tpl.render(rows=rows)
```

- [ ] **Step 5: Run → PASS**

Run: `python -m pytest tests/unit/test_menu_dataset.py -v`
Expected: 2 passed

- [ ] **Step 6: Commit per-file**

```bash
git add templates/menu_dataset.xml.j2
git commit -m "feat(tpl): dsMenu seed template"
git add scripts/menu_dataset_gen.py
git commit -m "feat: menu_dataset_gen builds dsMenu rows from entity list"
git add tests/unit/test_menu_dataset.py
git commit -m "test: menu_dataset_gen unit tests"
```

### Task 12: typedef_patcher + template

**Files:**
- Create: `templates/typedefinition_patch.xml.j2`
- Create: `scripts/typedef_patcher.py`
- Create: `tests/unit/test_typedef_patcher.py`

- [ ] **Step 1: Write template**

```xml
{# templates/typedefinition_patch.xml.j2 #}
<Services>
{%- for ent in entities %}
  <Service id="Svc{{ ent.pascal }}" url="{{ context_path }}{{ ent.endpoint_base }}" type="default" version="1.0"/>
{%- endfor %}
</Services>
```

- [ ] **Step 2: Write failing test**

```python
# tests/unit/test_typedef_patcher.py
import xml.etree.ElementTree as ET
from typedef_patcher import build_service_entries, render_patch


def test_build_entries():
    out = build_service_entries([
        {"name": "customer", "endpoint_base": "/customer"},
    ])
    assert out == [{"pascal": "Customer", "endpoint_base": "/customer"}]


def test_render_patch_well_formed():
    xml = render_patch(
        build_service_entries([{"name": "customer", "endpoint_base": "/customer"}]),
        context_path="/uiadapter",
    )
    root = ET.fromstring(xml)
    svc = root.find("Service")
    assert svc.get("id") == "SvcCustomer"
    assert svc.get("url") == "/uiadapter/customer"
```

- [ ] **Step 3: Run → FAIL**

Run: `python -m pytest tests/unit/test_typedef_patcher.py -v`
Expected: ModuleNotFoundError

- [ ] **Step 4: Implement**

```python
# scripts/typedef_patcher.py
import pathlib
from jinja2 import Environment, FileSystemLoader

TEMPLATES = pathlib.Path(__file__).resolve().parents[1] / "templates"
ENV = Environment(loader=FileSystemLoader(TEMPLATES),
                  trim_blocks=True, lstrip_blocks=True,
                  keep_trailing_newline=False)


def _pascal(name):
    return "".join(p.capitalize() for p in name.split("_"))


def build_service_entries(endpoint_entities):
    return [
        {"pascal": _pascal(e["name"]), "endpoint_base": e["endpoint_base"]}
        for e in endpoint_entities
    ]


def render_patch(service_entries, context_path="/uiadapter"):
    tpl = ENV.get_template("typedefinition_patch.xml.j2")
    return tpl.render(entities=service_entries, context_path=context_path)
```

- [ ] **Step 5: Run → PASS**

Run: `python -m pytest tests/unit/test_typedef_patcher.py -v`
Expected: 2 passed

- [ ] **Step 6: Commit per-file**

```bash
git add templates/typedefinition_patch.xml.j2
git commit -m "feat(tpl): typedefinition patch Services fragment"
git add scripts/typedef_patcher.py
git commit -m "feat: typedef_patcher emits Service entries per entity"
git add tests/unit/test_typedef_patcher.py
git commit -m "test: typedef_patcher unit tests"
```

---

## Phase 6 — CLI + e2e

### Task 13: form_gen.py CLI orchestrator

**Files:**
- Create: `scripts/form_gen.py`
- Create: `tests/integration/test_form_gen_cli.py`

- [ ] **Step 1: Write failing test**

```python
# tests/integration/test_form_gen_cli.py
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_cli_emits_full_output_tree(tmp_path):
    out = tmp_path / "out"
    cmd = [
        sys.executable, str(ROOT / "scripts" / "form_gen.py"), "compile",
        "--blueprint", str(ROOT / "tests" / "fixtures" / "golden_blueprint.yaml"),
        "--endpoints", str(ROOT / "tests" / "fixtures" / "golden_endpoints.json"),
        "--out", str(out),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert (out / "nxui" / "_form_" / "customer.xfdl").exists()
    assert (out / "nxui" / "_datasets_" / "dsMenu.seed.xml").exists()
    assert (out / "patches" / "typedefinition.patch.xml").exists()
    assert (out / "docs" / "nexacro-report.md").exists()


def test_cli_infer_endpoints(tmp_path):
    out = tmp_path / "out"
    cmd = [
        sys.executable, str(ROOT / "scripts" / "form_gen.py"), "compile",
        "--blueprint", str(ROOT / "tests" / "fixtures" / "golden_blueprint.yaml"),
        "--infer-endpoints",
        "--out", str(out),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert (out / "nxui" / "_form_" / "customer.xfdl").exists()


def test_cli_rejects_missing_endpoints(tmp_path):
    out = tmp_path / "out"
    cmd = [
        sys.executable, str(ROOT / "scripts" / "form_gen.py"), "compile",
        "--blueprint", str(ROOT / "tests" / "fixtures" / "golden_blueprint.yaml"),
        "--endpoints", str(tmp_path / "missing.json"),
        "--out", str(out),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 1
    assert "N002" in r.stderr
```

- [ ] **Step 2: Run → FAIL**

Run: `python -m pytest tests/integration/test_form_gen_cli.py -v`
Expected: file not found / collect error

- [ ] **Step 3: Implement CLI**

```python
# scripts/form_gen.py
import argparse
import pathlib
import sys

from blueprint_loader  import load_blueprint, BlueprintError
from endpoints_loader  import load_endpoints, infer_endpoints, cross_check, EndpointsError
from revalidator       import check_search_candidates, check_xml_wellformed, RevalidationError
from form_composer     import compose_form
from menu_dataset_gen  import build_menu_rows, render_menu_dataset
from typedef_patcher   import build_service_entries, render_patch


def _parse_args(argv):
    p = argparse.ArgumentParser(prog="karpathy-rdb-nexacro")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("compile")
    c.add_argument("--blueprint", required=True)
    c.add_argument("--endpoints", default=None)
    c.add_argument("--infer-endpoints", action="store_true")
    c.add_argument("--out", required=True)
    c.add_argument("--frame", default="packageN", choices=["packageN", "minimal"])
    c.add_argument("--strict", action="store_true")
    c.add_argument("--force", action="store_true")
    return p.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv or sys.argv[1:])
    out = pathlib.Path(args.out)
    form_dir   = out / "nxui" / "_form_"
    ds_dir     = out / "nxui" / "_datasets_"
    patch_dir  = out / "patches"
    docs_dir   = out / "docs"
    for d in (form_dir, ds_dir, patch_dir, docs_dir):
        d.mkdir(parents=True, exist_ok=True)

    warnings = []

    try:
        bp = load_blueprint(args.blueprint)
    except BlueprintError as e:
        print(f"[{e}]", file=sys.stderr)
        return 1

    try:
        if args.endpoints:
            ep = load_endpoints(args.endpoints)
        elif args.infer_endpoints:
            ep = infer_endpoints(bp["entities"])
        else:
            raise EndpointsError("N002 --endpoints or --infer-endpoints required")
        cross_check(bp["entities"], ep)
    except EndpointsError as e:
        print(f"[{e}]", file=sys.stderr)
        return 1

    try:
        check_search_candidates(bp["entities"])
    except RevalidationError as e:
        print(f"[{e}]", file=sys.stderr)
        return 1

    # Compose per-entity forms
    ep_by_name = {x["name"]: x for x in ep["entities"]}
    written = []
    for entity in bp["entities"]:
        target = form_dir / f"{entity['name']}.xfdl"
        if target.exists() and not args.force:
            print(f"[N007 overlay conflict: {target} exists — use --force]", file=sys.stderr)
            return 1
        if target.exists() and args.force:
            target.replace(target.with_suffix(target.suffix + ".bak"))
        xfdl = compose_form(entity, ep_by_name[entity["name"]])
        target.write_text(xfdl, encoding="utf-8")
        written.append(target)

    # Aux outputs
    menu_xml = render_menu_dataset(build_menu_rows(bp["entities"]))
    menu_path = ds_dir / "dsMenu.seed.xml"
    menu_path.write_text(menu_xml, encoding="utf-8")

    patch_xml = render_patch(
        build_service_entries(ep["entities"]),
        context_path=ep.get("context_path", "/uiadapter"),
    )
    patch_path = patch_dir / "typedefinition.patch.xml"
    patch_path.write_text(patch_xml, encoding="utf-8")

    # N006 XML wellformed across everything written
    try:
        check_xml_wellformed(written + [menu_path, patch_path])
    except RevalidationError as e:
        print(f"[{e}]", file=sys.stderr)
        return 1

    # nexacro-report.md
    report = ["# nexacro-report", "", f"- project: {bp.get('project','')}", "",
              "| entity | form | endpoints |", "| :-- | :-- | :-- |"]
    for entity in bp["entities"]:
        eps = ep_by_name[entity["name"]]["endpoints"]
        urls = ", ".join(e["http_path"] for e in eps)
        report.append(f"| {entity['name']} | _form_/{entity['name']}.xfdl | {urls} |")
    (docs_dir / "nexacro-report.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    if warnings:
        (docs_dir / "warnings.md").write_text("\n".join(warnings) + "\n", encoding="utf-8")
        if args.strict:
            print("[--strict] warnings present, failing", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run → PASS**

Run: `python -m pytest tests/integration/test_form_gen_cli.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/form_gen.py
git commit -m "feat: form_gen.py CLI orchestrates loaders → composer → outputs"
git add tests/integration/test_form_gen_cli.py
git commit -m "test(integration): CLI smoke for output tree + infer + N002 rejection"
```

### Task 14: overlay.sh + e2e smoke

**Files:**
- Create: `scripts/overlay.sh`
- Create: `tests/e2e/test_overlay_smoke.py`

- [ ] **Step 1: Write `scripts/overlay.sh`**

```bash
#!/usr/bin/env bash
# overlay.sh — copy Stage 4 output onto nexacro-fullstack-starter scaffold
set -euo pipefail

OUT_DIR="${1:?usage: overlay.sh <stage4-out-dir> <project-root>}"
PROJECT_ROOT="${2:?usage: overlay.sh <stage4-out-dir> <project-root>}"

# Forms + datasets
mkdir -p "${PROJECT_ROOT}/nxui/_form_" "${PROJECT_ROOT}/nxui/_datasets_"
cp -f "${OUT_DIR}/nxui/_form_/"*.xfdl              "${PROJECT_ROOT}/nxui/_form_/"
cp -f "${OUT_DIR}/nxui/_datasets_/dsMenu.seed.xml" "${PROJECT_ROOT}/nxui/_datasets_/"

# Patches — typedefinition append (manual review recommended)
echo "[overlay] typedefinition.patch.xml ready at ${OUT_DIR}/patches/ — merge into ${PROJECT_ROOT}/nxui/typedefinition.xml manually or via typedefinition.merge.py"

# Docs
mkdir -p "${PROJECT_ROOT}/docs"
cp -f "${OUT_DIR}/docs/"*.md "${PROJECT_ROOT}/docs/" 2>/dev/null || true

echo "[overlay] done"
```

- [ ] **Step 2: Write e2e smoke test**

```python
# tests/e2e/test_overlay_smoke.py
import json
import pathlib
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_e2e_blueprint_to_overlay(tmp_path):
    out = tmp_path / "out"
    cmd = [
        sys.executable, str(ROOT / "scripts" / "form_gen.py"), "compile",
        "--blueprint", str(ROOT / "tests" / "fixtures" / "golden_blueprint.yaml"),
        "--endpoints", str(ROOT / "tests" / "fixtures" / "golden_endpoints.json"),
        "--out", str(out),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr

    # Verify all emitted XML parses
    targets = [
        out / "nxui" / "_form_" / "customer.xfdl",
        out / "nxui" / "_datasets_" / "dsMenu.seed.xml",
        out / "patches" / "typedefinition.patch.xml",
    ]
    for p in targets:
        assert p.exists()
        ET.parse(p)  # raises if malformed

    # Simulated overlay: copy onto fake scaffold and verify files land
    scaffold = tmp_path / "scaffold"
    (scaffold / "nxui" / "_form_").mkdir(parents=True)
    (scaffold / "nxui" / "_datasets_").mkdir(parents=True)
    shutil.copy(out / "nxui" / "_form_" / "customer.xfdl",
                scaffold / "nxui" / "_form_" / "customer.xfdl")
    shutil.copy(out / "nxui" / "_datasets_" / "dsMenu.seed.xml",
                scaffold / "nxui" / "_datasets_" / "dsMenu.seed.xml")
    assert (scaffold / "nxui" / "_form_" / "customer.xfdl").exists()
```

- [ ] **Step 3: Run → PASS**

Run: `python -m pytest tests/e2e/test_overlay_smoke.py -v`
Expected: 1 passed

- [ ] **Step 4: Run full suite → PASS**

Run: `python -m pytest -v`
Expected: all green

- [ ] **Step 5: Commit per-file**

```bash
git add scripts/overlay.sh
git commit -m "feat: overlay.sh script for scaffold copy"
git add tests/e2e/test_overlay_smoke.py
git commit -m "test(e2e): blueprint → form_gen → overlay simulation"
```

### Task 15: --force / --strict / N007 conflict behavior tests

**Files:**
- Create: `tests/integration/test_cli_flags.py`

- [ ] **Step 1: Write test**

```python
# tests/integration/test_cli_flags.py
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _run(args):
    cmd = [sys.executable, str(ROOT / "scripts" / "form_gen.py"), "compile"] + args
    return subprocess.run(cmd, capture_output=True, text=True)


def test_n007_conflict_without_force(tmp_path):
    out = tmp_path / "out"
    base = ["--blueprint", str(ROOT / "tests" / "fixtures" / "golden_blueprint.yaml"),
            "--endpoints", str(ROOT / "tests" / "fixtures" / "golden_endpoints.json"),
            "--out", str(out)]
    assert _run(base).returncode == 0
    r2 = _run(base)
    assert r2.returncode == 1
    assert "N007" in r2.stderr


def test_force_creates_bak(tmp_path):
    out = tmp_path / "out"
    base = ["--blueprint", str(ROOT / "tests" / "fixtures" / "golden_blueprint.yaml"),
            "--endpoints", str(ROOT / "tests" / "fixtures" / "golden_endpoints.json"),
            "--out", str(out)]
    assert _run(base).returncode == 0
    assert _run(base + ["--force"]).returncode == 0
    assert (out / "nxui" / "_form_" / "customer.xfdl.bak").exists()
```

- [ ] **Step 2: Run → PASS**

Run: `python -m pytest tests/integration/test_cli_flags.py -v`
Expected: 2 passed

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_cli_flags.py
git commit -m "test(integration): N007 conflict + --force backup behavior"
```

---

## Phase 7 — Documentation + release

### Task 16: README + SKILL.md flesh-out

**Files:**
- Modify: `README.md`
- Modify: `.claude/skills/karpathy-rdb-nexacro/SKILL.md`

- [ ] **Step 1: Replace `README.md`**

```markdown
# andrej-karpathy-rdb-nexacro

Stage 4 of the `business-fullstack-creater` pipeline. Generates nexacro xfdl forms
from `_blueprint.yaml` (Stage 1) + `endpoints.json` (Stage 3 v0.1.4+).

## Quick start

```bash
python scripts/form_gen.py compile \
  --blueprint <path>/_blueprint.yaml \
  --endpoints <path>/endpoints.json \
  --out       out/
```

Outputs to:
```
out/nxui/_form_/<entity>.xfdl
out/nxui/_datasets_/dsMenu.seed.xml
out/patches/typedefinition.patch.xml
out/docs/nexacro-report.md
```

Overlay onto a `nexacro-fullstack-starter` scaffold:
```bash
bash scripts/overlay.sh out/ <project-root>/
```

## Flags
- `--infer-endpoints` — synthesize endpoints from blueprint when endpoints.json absent
- `--frame packageN|minimal` — frame style (default packageN MDI)
- `--strict` — fail on type fallbacks
- `--force` — overwrite existing xfdl (writes `.bak` first)

## Validators
| ID | Check |
| :-- | :-- |
| N001 | blueprint version + validation.passed |
| N002 | endpoints.json shape |
| N003 | blueprint ↔ endpoints entity sets match |
| N004 | every entity has ≥1 PK column |
| N005 | every entity has ≥1 searchable column |
| N006 | all emitted XML parses |
| N007 | overlay conflict guard |

## Design contract
See `docs/superpowers/specs/2026-05-14-andrej-karpathy-rdb-nexacro-design.md`
in the `business-fullstack-creater` repo.
```

- [ ] **Step 2: Replace `SKILL.md`**

```markdown
---
name: karpathy-rdb-nexacro
description: Generates entity-per-form nexacro xfdl from blueprint + endpoints.json
---

# karpathy-rdb-nexacro

Stage 4 of the business-fullstack-creater pipeline.

## Inputs
- `_blueprint.yaml` — see `references/blueprint-input-contract.md`
- `endpoints.json` — see `references/endpoints-input-contract.md`

## Outputs
See `references/output-layout.md`.

## Form layout
2-tier — Search panel (top) + editable Grid (middle) + action buttons.
See `references/form-layout.md`.

## Type mapping
See `references/type-mapping-matrix.md`.

## Overlay
See `references/overlay-policy.md`.

## Run
```
python scripts/form_gen.py compile --blueprint <bp> --endpoints <ep> --out <dir>
```
```

- [ ] **Step 3: Commit per-file**

```bash
git add README.md
git commit -m "docs: README with quick-start, flags, validators"
git add .claude/skills/karpathy-rdb-nexacro/SKILL.md
git commit -m "docs(skill): SKILL.md links to all reference docs"
```

### Task 17: Final smoke + v0.1.0 tag

- [ ] **Step 1: Full test suite**

Run: `cd D:\AI\workspace\andrej-karpathy-rdb-nexacro && python -m pytest -v`
Expected: all green, 0 failures

- [ ] **Step 2: Run a real end-to-end against Stage 3 output**

```powershell
$mb = "D:\AI\workspace\andrej-karpathy-rdb-mybatis"
$here = "D:\AI\workspace\andrej-karpathy-rdb-nexacro"
$smoke = "$here\.smoke\stage3-out"
Remove-Item -Recurse -Force $smoke -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force "$smoke" | Out-Null

# 1) Run Stage 3 to produce backend + endpoints.json
python "$mb\scripts\compile.py" compile `
  --blueprint "$mb\tests\fixtures\golden_blueprint.yaml" `
  --ddl-dir   "$mb\tests\fixtures\golden_ddl" `
  --out       "$smoke" --skip-compile --dry-run

# 2) Run Stage 4 against that endpoints.json
python "$here\scripts\form_gen.py" compile `
  --blueprint "$mb\tests\fixtures\golden_blueprint.yaml" `
  --endpoints "$smoke\endpoints.json" `
  --out       "$here\.smoke\stage4-out"
```

Expected: exit code 0, `customer.xfdl` exists, `nexacro-report.md` lists customer.

- [ ] **Step 3: Tag v0.1.0**

```bash
cd D:\AI\workspace\andrej-karpathy-rdb-nexacro
git tag v0.1.0
```

- [ ] **Step 4: Update business-fullstack-creater status doc**

In `D:\AI\workspace\business-fullstack-creater\needs\business-fullstack-creater 플러그인 요구기능.md` (status table section, around line 119-124), add row:

```markdown
| 4 | `andrej-karpathy-rdb-nexacro` | ✅ 완료 (v0.1.0) — `D:\AI\workspace\andrej-karpathy-rdb-nexacro` |
```

(Replace the existing "외부 plugin 사용" row for stage 4.)

```bash
cd D:\AI\workspace\business-fullstack-creater
git add "needs/business-fullstack-creater 플러그인 요구기능.md" 2>nul
git commit -m "docs: Stage 4 plugin v0.1.0 status update" 2>nul
```

> The `business-fullstack-creater` directory is not a git repo per session metadata — if `git add` fails, skip the commit. The edit alone is the deliverable.

---

## Self-Review Notes (post-write)

**Spec coverage check:**
- §3 D1 (2-tier form) → Task 8 form.xfdl.j2
- §3 D2 (packageN frame) → CLI `--frame packageN` default in Task 13
- §3 D3 (entity-independent) → composer renders 1 form per entity, no relation lookups
- §3 D4 (blueprint + endpoints.json) → Tasks 3, 4
- §3 D5 (separate dir + overlay) → Tasks 13, 14
- §3 D6 (fixed matrix + *_yn) → Task 6
- §4.2 endpoints schema → Task 4 (loader) + Task 0.1 (Stage 3 emitter)
- §4.3 output manifest → Task 13 CLI mkdir + writes
- §4.4 plugin layout → Tasks 1, 2
- §5 form template → Task 8
- §6 type matrix → Task 6 (10 sub-cases tested)
- §7 N001-N006 → Tasks 3, 4, 5
- §8 error handling → Task 13 (N007 conflict, --strict, --force) + Task 15 tests
- §9 test strategy (unit/integration/e2e) → Phases 2-6 follow this split
- §10 CLI sig → Task 13 argparse
- §11 Stage 3 v0.1.4 dependency → Phase 0
- §12 plan order matches phase order
- §13 frameLeft schema assumption noted in Task 11

**Type consistency check:**
- `MapResult` fields (`dataset_type`, `size`, `search_component`, `grid_edittype`, `grid_displaytype`, `combo_options`, `fallback`) used consistently from Task 6 onward.
- `compose_form(entity, endpoints_for_entity)` signature matches between Task 9 and Task 13 caller.
- `build_menu_rows(entities)` and `render_menu_dataset(rows)` consistent Task 11 → Task 13.
- `build_service_entries(endpoint_entities)` returns `[{pascal, endpoint_base}]` — consumed by `render_patch` in Task 12; CLI passes `ep["entities"]` (each item has `name` + `endpoint_base`).
- `cross_check(blueprint_entities, endpoints_payload)` raises N003 — same signature in Task 4 and CLI Task 13.

**Placeholder scan:** No `TBD`/`TODO`/`implement later`. Each step has either complete code or a complete command.

---

## Execution

Plan complete and saved to `docs/superpowers/plans/2026-05-14-andrej-karpathy-rdb-nexacro.md`.

Two execution options:

1. **Subagent-Driven (recommended)** — fresh subagent per task with two-stage review (spec compliance + code quality), fast iteration.
2. **Inline Execution** — execute tasks in this session using executing-plans, batch checkpoints.

Which approach?
