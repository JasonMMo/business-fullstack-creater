# business-fullstack-creater

> A **5-stage code generation orchestrator** that turns a one-line business request (`"build a customer-management workspace"`) into a nexacroN + Spring Boot + RDB 3-tier project.

[한국어](README.md) · English

| | |
|---|---|
| **Status** | 4 lanes (vanilla / javax / jakarta / nexacro) × 14 domains — full-test green |
| **Accumulated** | 14 domains · 11 frontend patterns · 4 backend lanes · 3 dialects · 2 UI overlays |
| **Trap guards** | `/diagnose` enforces 6 static cross-layer regression guards (G-47/48/50a/50b/58/61) |
| **Tests** | 440 green (workflow 281 + non-workflow 159) |

For depth see [`docs/USER-GUIDE.md`](docs/USER-GUIDE.md) (95K) — this document is an entry-point overview.

---

## 1. What it builds

A 5-stage pipeline that drives four sibling repos in sequence:

```
Stage 1  rdb-skill     natural language → _blueprint.yaml
Stage 2  rdb-ddl       blueprint → DDL/seed (postgres/hsqldb/mysql)
Stage 3  rdb-mybatis   DB → Java backend + endpoints.json (4 lanes)
Stage 4  rdb-nexacro   endpoints → XFDL form/dataset (nexacro lane only)
Stage 5  overlay       lay Stage 2-4 artifacts over runner skeleton → war
```

Outputs:
- `out/<domain>/` — schema.sql · mapper.xml · Controller.java · Service.java · XFDL form
- `scaffold-report.md` — per-stage PASS/SKIP/FAIL label
- `~/.karpathy-rdb/catalog/<domain>/` — global catalog accumulation (compounding)

## 2. Core principle — 6-axis compounding accumulation

This is a **growth project**: assets accumulate in proportion to usage. Every time a new domain is added or a known one is revisited, we deepen the same six axes:

| Axis | Accumulation site |
|---|---|
| **skill** (Stage 1) | `andrej-karpathy-rdb-skill/.claude/skills/karpathy-rdb/presets/*.seed.md` |
| **ddl** (Stage 2) | `andrej-karpathy-rdb-ddl/catalogs/preset-catalog.yaml` |
| **mybatis** (Stage 3) | `andrej-karpathy-rdb-mybatis/templates/<lane>/` |
| **nexacro** (Stage 4+5) | `andrej-karpathy-rdb-nexacro/patterns/` |
| **creater** (orchestrator) | `business-fullstack-creater/.claude/commands/` + `scripts/workflow/` |
| **customer** (6th, Growth-63) | `business-fullstack-creater/profiles/<slug>.yaml` — one YAML per customer bundles package / URL / JDBC / lane / UI conventions; `/scaffold --customer-profile <name>` applies them consistently across Stages 1–5 |

`learn-log.md` §0 (Layer Ownership Card) holds the current accumulated state — trap count, open feedback items, and verification milestones in a single table.

Principle-violation warning signs: *"just this once"* / *"we'll clean it up later"*. When those phrases surface, stop and route the work into a catalog / template / preset first. See [`CLAUDE.md`](CLAUDE.md) for the full operating discipline.

## 3. Quick Start

```powershell
# 0. Environment preflight (sibling repos + INDEX.md + runners + JDK + 6 cross-layer guards)
python -m scripts.workflow.diagnose

# 1. List the 14 domain candidates
python -m scripts.workflow.list_domains

# 2. Generate a domain — keep Korean domain + ASCII slug/package separate (Growth-51 trap)
python scripts/scaffold_cli.py `
  --domain 고객관리 --slug customer --package com.example.customer `
  --lane jakarta --dialect hsqldb `
  --out ./out/customer --wiki-mode preset --preset 고객관리

# 3. 4-tier full-test (L1 pytest + L2 JDBC + L3 Maven + L4 live WAS HTTP 200)
python -m scripts.workflow.full_test jakarta out/customer

# 4. Rebuild the static portal (14-domain tile grid + L1 preview + L2 zip + L3 snippet)
python -m scripts.workflow.web_index
```

Inside Claude Code the same flow is exposed as slash commands:
```
/orient → /diagnose → /list-domains → /scaffold <domain> → /full-test <lane> <domain>
```

## 4. lane × dialect × overlay matrix

| lane | runner | Verification | Default `--ui` |
|---|---|---|---|
| **nexacro** | `boot-jdk17-jakarta` | ✅ Growth-42 (envelope CRUD) | nexacro |
| **jakarta** | `boot-jdk17-jakarta` | ✅ Growth-28 / Growth-31 | nexacro |
| **javax** | `boot-jdk8-javax` | ✅ Growth-49 (3 stacked fixes) | nexacro |
| **vanilla** | (no dedicated runner — javax-host) | ✅ Growth-50 (first REST end-to-end) | react (Growth-59 lane-aware default) |

If `--ui` is omitted the overlay is picked from lane intent. Dialect is `--dialect {postgres,hsqldb,mysql}`.

## 5. Asset-exposure harness — 4-point chain

A new user landing in the repo should see "where do I touch first" in a single screen. Four entry points surface the accumulated assets:

| Point | Command | Asset surfaced |
|---|---|---|
| **Entry** | `/orient` | USER-GUIDE one-line pitch + Layer Ownership Card + latest Growth |
| **Pre-flight** | `/diagnose` | 6-axis sibling repos + INDEX.md + runners + JDK + 7 regression guards |
| **Execution** | `/full-test` | 4-tier PASS/FAIL + lane × runner matrix |
| **Post-failure** | `recovery_hint` | One-line next command per failing layer |

Additionally `/web-build` (Growth-55) produces a static portal at `docs/index.html` — external users browse all 14 domains' assets (DDL/Mapper/Controller/Service preview + L2 zip + L3 copy-paste snippet) without cloning.

## 6. 4-tier full-test contract

When `/full-test <lane> <scaffold>` runs:

| Tier | Check | Label |
|---|---|---|
| **L1** | sibling-repo pytest rc=0 (4 repos) | unit-green |
| **L2** | HSQLDB schema + seed via JDBC executes | jdbc-green |
| **L3** | `mvn package` rc=0 | build-green |
| **L4** | live WAS HTTP 200 + ErrorCode=0 + rows≥1 (+ envelope/REST CRUD round-trip) | live-green |

L1-L4 all PASS = **full-test green**. Cleanup is automatic (since the Growth-54 `cleanup_runner` fix).

## 7. Directory map

```
.claude/commands/        9 slash commands
scripts/workflow/        full_test · live_* · lane_runner_map · web_index · diagnose · orient · ...
scripts/scaffold_cli.py  CLI entry point
scripts/scaffold_orchestrator.py  Stage 1→5 orchestration
docs/USER-GUIDE.md       Unified guide (95K)
docs/index.html          Static portal entry
learn-log.md             Activity ledger (§0 accumulated state, §4 traps, §6 Growth history)
tests/                   workflow 281 + others 159 = 440 green
```

## 8. References

- **Operating principles**: [`CLAUDE.md`](CLAUDE.md) — invariant 6-axis compounding rules
- **Activity ledger**: [`learn-log.md`](learn-log.md) — Growth accumulation / traps / regression guards
- **Unified guide**: [`docs/USER-GUIDE.md`](docs/USER-GUIDE.md) — Quick Start + Stage reference + troubleshooting
- **Static portal**: `docs/index.html` (open in a browser)
- **Older Growths**: `wiki/learn-log-archive-*.md`
