# Stage 3 — andrej-karpathy-rdb-mybatis Design Spec

> **Pipeline:** Stage 1 (`andrej-karpathy-rdb-skill`) → Stage 2 (`andrej-karpathy-rdb-ddl`) → **Stage 3 (this spec)** → Stage 4 (`nexacro-claude-skills`)
>
> **Date:** 2026-05-13
> **Author:** business-fullstack-creater
> **Status:** Approved for plan writing

---

## Goal

Generate MyBatis + nexacro uiadapter backend code (controller / service / mapper / domain POJO) from Stage 2 DDL artifacts and Stage 1 blueprint, producing a backend project layer that drops into `nexacro-fullstack-starter` 4.2 canonical scaffold.

## Architecture

Plugin name: **`andrej-karpathy-rdb-mybatis`** at `D:\AI\workspace\andrej-karpathy-rdb-mybatis\`.

Slash command: `/karpathy-rdb-mybatis compile`.

Implementation strategy: **Hybrid (Jinja2 templates + Python helpers)** — same pattern as Stage 2. Templates are flat (no branching), all rowType/column/name logic is precomputed in Python helpers before render.

Output target: nexacro 4.2 canonical package layout under `com.nexacro.uiadapter.{controller, service, service.impl, mapper, domain}`, MyBatis + `SqlSessionTemplate`, Plain POJO `extends NexacroBase` (no Lombok, no JPA), HSQLDB runtime via `schema.sql`/`data.sql`.

---

## Input Contract

| Source | Path (default) | Purpose | Required |
|---|---|---|---|
| Stage 1 blueprint | `wiki/_blueprint.yaml` | entities, relations, business_rules, validation.passed | yes |
| Stage 2 DDL | `db/migrations/V001__create_schema.sql` … `V004__create_constraints.sql` | PostgreSQL DDL bundle | yes |
| Stage 2 seed (optional) | `db/seed/01_*_sample.sql` | preset seed rows | no |

Blueprint must satisfy: `version == 1` AND `validation.passed == true`. DDL bundle must contain all four V001~V004 files.

## Output Contract

Under `--out` (default `backend/`):

```
backend/
├── src/main/java/com/nexacro/uiadapter/
│   ├── controller/<Entity>Controller.java
│   ├── service/<Entity>Service.java
│   ├── service/impl/<Entity>ServiceImpl.java
│   ├── mapper/<Entity>Mapper.java
│   └── domain/<Entity>.java
├── src/main/resources/
│   ├── schema.sql                       # HSQLDB DDL (V001~V004 변환)
│   ├── data.sql                         # seed (V005 변환, 옵션)
│   └── mybatis/mapper/<Entity>Mapper.xml
└── mybatis-report.md
```

Stage 3 only writes the domain layer. The starter's `pom.xml`, `application.yml`, `Application.java`, `config/` are not touched.

---

## Locked Decisions (D1~D11)

| # | Decision |
|---|---|
| D1 | Plugin `andrej-karpathy-rdb-mybatis` at `D:\AI\workspace\andrej-karpathy-rdb-mybatis\` |
| D2 | Java package `com.nexacro.uiadapter.{controller, service, service.impl, mapper, domain}` (4.2 canonical) |
| D3 | Plain POJO `extends NexacroBase`, no Lombok, with `searchCondition`/`searchKeyword`/`searchUseYn` auto-included |
| D4 | Endpoints `/<entity>/select_datalist_map.do`, `/<entity>/save_datalist_map.do` (PDF p.64~70 canonical) |
| D5 | Search input `Map<String,String> searchMap` → output `List<Map<String,Object>>`, dataset name `output1` |
| D6 | WHERE pattern: all-column dynamic equality (`<if test="COL != null and COL != ''"> AND COL = #{COL}</if>`) |
| D7 | `@Transactional` on save methods, `@Transactional(readOnly = true)` on select methods |
| D8 | DDL consumption: V001~V004 merged → `src/main/resources/schema.sql` (HSQLDB dialect converted); seed → `data.sql` |
| D9 | JPA Entity (Stage 2 by-product) excluded from Stage 3 project; Plain POJO only |
| D10 | CLI: `/karpathy-rdb-mybatis compile --blueprint <p> --ddl-dir <p> --out <p>` |
| D11 | Tests: Python snapshot diff + javac compile verification (no Spring Boot boot test) |

---

## Pipeline (7 stages)

```
[1] Input load
    ├─ blueprint_loader: parse + R001/R002
    └─ ddl_loader: collect V001~V004 + R003

[2] Normalize
    ├─ toposort: FK-aware entity order (reuse Stage 2 toposort)
    ├─ column_classifier: pk / non_pk / searchable + R004
    └─ name_mapper: snake_case ↔ UPPER_SNAKE ↔ PascalCase tables

[3] Precompute (Python helpers, pure functions)
    ├─ _gather_mapper_columns(entity) → {pk:[…], non_pk:[…], all_upper:[…]}
    ├─ _build_save_branches(entity)   → [{rowType:INSERTED, method:insert_xxx_map}, …]
    ├─ _build_search_predicates(entity) → ["AND COL = #{COL}", …]
    └─ _build_domain_fields(entity)   → [{name:customerId, type:String, getter:…}, …]

[4] DDL convert
    ├─ postgres_to_hsqldb: V001~V004 → schema.sql
    └─ seed_to_data: db/seed/*.sql → data.sql (if present)

[5] Code generate (Jinja2 with flat dicts)
    └─ render 6 templates × N entities

[6] Revalidate
    ├─ R005 mapper-xml lint (namespace, id ↔ method)
    └─ R006 javac compile check

[7] Report
    └─ mybatis-report.md + exit code
```

---

## Validation Rules

| ID | Check | On failure |
|---|---|---|
| R001 | blueprint `version == 1` | abort, exit 1 |
| R002 | blueprint `validation.passed == true` | abort, exit 1 + ask user to re-run Stage 1 |
| R003 | `--ddl-dir` contains V001~V004 | abort, exit 1 + ask user to re-run Stage 2 |
| R004 | every entity has ≥ 1 PK column | abort, exit 1 + fix blueprint |
| R005 | mapper XML `namespace` ↔ interface FQCN, `id` ↔ method names | stop pipeline, exit 2, **artifacts preserved** |
| R006 | generated `.java` passes `javac` | warn, exit 2, **artifacts preserved** |

**Priority**: R001 → R002 → R003 → R004 → (codegen) → R005 → R006.

**Preservation**: R001~R004 fail before generation, nothing to preserve. R005/R006 fail after generation, preserve artifacts so the user can debug.

## Error / Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Input contract violation (R001~R004) |
| 2 | Post-generation validation failure (R005/R006), output preserved |
| 3 | Template render or IO exception, partial output cleaned |

---

## PostgreSQL → HSQLDB Dialect Conversion

| Postgres | HSQLDB | Action |
|---|---|---|
| `CREATE SCHEMA IF NOT EXISTS xxx;` | (omit) | drop line, strip `xxx.table` qualifier |
| `SERIAL` / `BIGSERIAL` | `INTEGER GENERATED BY DEFAULT AS IDENTITY` / `BIGINT …` | replace |
| `TIMESTAMP WITH TIME ZONE` | `TIMESTAMP` | replace |
| `NUMERIC(p,s)` | `DECIMAL(p,s)` | replace |
| `TEXT` | `LONGVARCHAR` | replace |
| `BOOLEAN` | `BOOLEAN` | keep |
| `JSONB` | `LONGVARCHAR` | downgrade + warning |
| `gen_random_uuid()` | (omit) | strip DEFAULT + warning |
| `ON DELETE CASCADE` … | identical | keep |

Output assembled into a single `schema.sql` with header comment and section dividers. Seed files under `db/seed/` get identical treatment, concatenated into `data.sql`.

---

## File Output Formats

Reference entity: `customer` with PK `customer_id`, columns `customer_id, name, email, status`.

### domain/Customer.java

```java
package com.nexacro.uiadapter.domain;

import com.nexacro.uiadapter.spring.core.data.NexacroBase;

public class Customer extends NexacroBase {

    private String customerId;
    private String name;
    private String email;
    private String status;

    private String searchCondition;
    private String searchKeyword;
    private String searchUseYn;

    public String getCustomerId() { return customerId; }
    public void setCustomerId(String customerId) { this.customerId = customerId; }
    // … remaining getter/setter
}
```

### mapper/CustomerMapper.java

```java
package com.nexacro.uiadapter.mapper;

import java.util.List;
import java.util.Map;

public interface CustomerMapper {
    List<Map<String, Object>> select_customer_datalist_map(Map<String, String> searchMap);
    void insert_customer_map(Map<String, Object> customer);
    void update_customer_map(Map<String, Object> customer);
    void delete_customer_map(Map<String, Object> customer);
}
```

### mapper/CustomerMapper.xml

```xml
<?xml version="1.0" encoding="UTF-8" ?>
<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN"
        "http://mybatis.org/dtd/mybatis-3-mapper.dtd">
<mapper namespace="com.nexacro.uiadapter.mapper.CustomerMapper">

  <select id="select_customer_datalist_map" parameterType="java.util.Map"
          resultType="java.util.Map">
    SELECT CUSTOMER_ID, NAME, EMAIL, STATUS
      FROM TB_CUSTOMER
     WHERE 1=1
    <if test="CUSTOMER_ID != null and CUSTOMER_ID != ''"> AND CUSTOMER_ID = #{CUSTOMER_ID}</if>
    <if test="NAME != null and NAME != ''"> AND NAME = #{NAME}</if>
    <if test="EMAIL != null and EMAIL != ''"> AND EMAIL = #{EMAIL}</if>
    <if test="STATUS != null and STATUS != ''"> AND STATUS = #{STATUS}</if>
  </select>

  <insert id="insert_customer_map" parameterType="java.util.Map">
    INSERT INTO TB_CUSTOMER (CUSTOMER_ID, NAME, EMAIL, STATUS)
    VALUES (#{CUSTOMER_ID}, #{NAME}, #{EMAIL}, #{STATUS})
  </insert>

  <update id="update_customer_map" parameterType="java.util.Map">
    UPDATE TB_CUSTOMER
       SET NAME = #{NAME},
           EMAIL = #{EMAIL},
           STATUS = #{STATUS}
     WHERE CUSTOMER_ID = #{CUSTOMER_ID}
  </update>

  <delete id="delete_customer_map" parameterType="java.util.Map">
    DELETE FROM TB_CUSTOMER WHERE CUSTOMER_ID = #{CUSTOMER_ID}
  </delete>

</mapper>
```

### service/CustomerService.java

```java
package com.nexacro.uiadapter.service;

import java.util.List;
import java.util.Map;

public interface CustomerService {
    List<Map<String, Object>> select_customer_datalist_map(Map<String, String> searchMap);
    void save_customer_datalist_map(List<Map<String, Object>> dataList);
}
```

### service/impl/CustomerServiceImpl.java

```java
package com.nexacro.uiadapter.service.impl;

import java.util.List;
import java.util.Map;

import org.mybatis.spring.SqlSessionTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.nexacro.java.xapi.data.DataSet;
import com.nexacro.uiadapter.spring.core.data.DataSetRowTypeAccessor;
import com.nexacro.uiadapter.mapper.CustomerMapper;
import com.nexacro.uiadapter.service.CustomerService;

@Service("customerService")
public class CustomerServiceImpl implements CustomerService {

    @Autowired
    private SqlSessionTemplate sqlSession;

    @Override
    @Transactional(readOnly = true)
    public List<Map<String, Object>> select_customer_datalist_map(Map<String, String> searchMap) {
        CustomerMapper mapper = sqlSession.getMapper(CustomerMapper.class);
        return mapper.select_customer_datalist_map(searchMap);
    }

    @Override
    @Transactional
    public void save_customer_datalist_map(List<Map<String, Object>> dataList) {
        CustomerMapper mapper = sqlSession.getMapper(CustomerMapper.class);
        for (Map<String, Object> customer : dataList) {
            int rowType = Integer.parseInt(String.valueOf(customer.get(DataSetRowTypeAccessor.NAME)));
            if (rowType == DataSet.ROW_TYPE_INSERTED) {
                mapper.insert_customer_map(customer);
            } else if (rowType == DataSet.ROW_TYPE_UPDATED) {
                mapper.update_customer_map(customer);
            } else if (rowType == DataSet.ROW_TYPE_DELETED) {
                mapper.delete_customer_map(customer);
            }
        }
    }
}
```

### controller/CustomerController.java

```java
package com.nexacro.uiadapter.controller;

import java.util.List;
import java.util.Map;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.RequestMapping;

import com.nexacro.uiadapter.spring.core.data.NexacroResult;
import com.nexacro.uiadapter.spring.core.data.ParamDataSet;
import com.nexacro.uiadapter.spring.core.NexacroException;
import com.nexacro.uiadapter.service.CustomerService;

@Controller
public class CustomerController {

    @Autowired
    private CustomerService customerService;

    @RequestMapping(value = "/customer/select_datalist_map.do")
    public NexacroResult select_datalist_map(
            @ParamDataSet(name = "dsSearch", required = false) Map<String, String> searchMap)
            throws NexacroException {
        List<Map<String, Object>> list = customerService.select_customer_datalist_map(searchMap);
        NexacroResult result = new NexacroResult();
        result.addDataSet("output1", list);
        return result;
    }

    @RequestMapping(value = "/customer/save_datalist_map.do")
    public NexacroResult save_datalist_map(
            @ParamDataSet(name = "dataList") List<Map<String, Object>> dataList)
            throws NexacroException {
        customerService.save_customer_datalist_map(dataList);
        return new NexacroResult();
    }
}
```

### schema.sql (HSQLDB)

```sql
-- Generated from db/migrations/V001~V004 (postgres → hsqldb)

CREATE TABLE TB_CUSTOMER (
  CUSTOMER_ID VARCHAR(36) NOT NULL,
  NAME        VARCHAR(100),
  EMAIL       VARCHAR(200),
  STATUS      VARCHAR(20),
  CONSTRAINT PK_TB_CUSTOMER PRIMARY KEY (CUSTOMER_ID)
);

CREATE INDEX IX_TB_CUSTOMER_EMAIL ON TB_CUSTOMER (EMAIL);

ALTER TABLE TB_ADDRESS
  ADD CONSTRAINT FK_TB_ADDRESS_CUSTOMER
  FOREIGN KEY (CUSTOMER_ID) REFERENCES TB_CUSTOMER (CUSTOMER_ID);
```

---

## Plugin Repository Layout

```
andrej-karpathy-rdb-mybatis/
├── .claude/
│   ├── plugin.json
│   ├── commands/karpathy-rdb-mybatis.md
│   └── skills/karpathy-rdb-mybatis/
│       ├── SKILL.md
│       ├── references/
│       │   ├── blueprint-input-contract.md
│       │   ├── nexacro-uiadapter-spec.md
│       │   └── output-layout.md
│       └── templates/
│           ├── domain/entity.java.j2
│           ├── mapper/mapper-interface.java.j2
│           ├── mapper/mapper.xml.j2
│           ├── service/service-interface.java.j2
│           ├── service/service-impl.java.j2
│           ├── controller/controller.java.j2
│           └── ddl/{schema.sql.j2, data.sql.j2}
├── scripts/
│   ├── compile.py              # CLI entry point
│   ├── blueprint_loader.py
│   ├── ddl_loader.py
│   ├── postgres_to_hsqldb.py
│   ├── name_mapper.py
│   ├── column_classifier.py
│   ├── precompute.py
│   ├── codegen.py
│   ├── revalidator.py
│   └── reporter.py
├── tests/
│   ├── fixtures/{golden_blueprint/, golden_ddl/, expected_output/}
│   ├── test_blueprint_loader.py
│   ├── test_ddl_loader.py
│   ├── test_name_mapper.py
│   ├── test_column_classifier.py
│   ├── test_postgres_to_hsqldb.py
│   ├── test_precompute.py
│   ├── test_codegen.py
│   ├── test_revalidator.py
│   ├── test_reporter.py
│   └── test_golden_path.py
├── README.md
├── INSTALL-FOR-AI.md
└── pyproject.toml
```

---

## CLI

```
/karpathy-rdb-mybatis compile [flags]
```

| Flag | Default | Purpose |
|---|---|---|
| `--blueprint` | `wiki/_blueprint.yaml` | Stage 1 output |
| `--ddl-dir` | `db/migrations` | Stage 2 output |
| `--out` | `backend/` | output root |
| `--package` | `com.nexacro.uiadapter` | Java base package |
| `--table-prefix` | `TB_` | sanity-check only — warns if any blueprint `entity.table` does not start with this prefix; not applied automatically (blueprint `table` is authoritative) |
| `--skip-compile` | false | skip R006 javac |
| `--dry-run` | false | report only, no file write |

Environment: `NEXACRO_LIBS_DIR` for javac classpath (jars: `nexacro-uiadapter`, `mybatis-spring`, `spring-context`). If unset, R006 is skipped with a warning.

---

## Test Strategy (TDD)

| Test file | Target | Key cases |
|---|---|---|
| `test_blueprint_loader.py` | R001/R002 | `version=2` reject / `validation.passed=false` reject / golden pass |
| `test_ddl_loader.py` | R003 | missing V003 reject / all present pass |
| `test_name_mapper.py` | name conversion | `customer_id`↔`CUSTOMER_ID`↔`customerId`↔`Customer` round-trip |
| `test_column_classifier.py` | R004 + classification | zero-PK reject / composite-PK / non_pk split |
| `test_postgres_to_hsqldb.py` | dialect conversion | SERIAL → IDENTITY / SCHEMA strip / JSONB downgrade warning / CHECK preserved |
| `test_precompute.py` | helpers | `_gather_mapper_columns` / `_build_save_branches` / `_build_search_predicates` dict shape |
| `test_codegen.py` | template render | single-entity 6 files → snapshot diff |
| `test_revalidator.py` | R005/R006 | XML namespace mismatch detected / intentionally broken `.java` → javac fail caught |
| `test_reporter.py` | report | all sections present / exit code consistency |
| `test_golden_path.py` | E2E | golden blueprint + golden DDL → `expected_output/` snapshot match + javac 0 errors |

**Golden fixtures**: Reuse Stage 2 `golden_blueprint`. Commit Stage 2 V001~V004 output as `golden_ddl/`. `expected_output/` locked after first sanity-checked run.

**Dependencies**: `pyyaml`, `jinja2` (same as Stage 2), plus `subprocess` for javac. No external build tool dependency.

---

## Out of Scope (Stage 3)

- Custom business logic beyond CRUD (Stage 4 nexacro screens may add via xeni)
- Detail-level (select_detail_map) endpoint — only `select_datalist_map` and `save_datalist_map` per D4
- JPA Entity generation — explicitly excluded (D9)
- Spring Boot integration test / boot test — explicitly excluded (D11)
- PostgreSQL runtime artifacts (Flyway in `db/migration/`) — schema.sql for HSQLDB only (D8)

## Next Stage

Stage 4 (`nexacro-claude-skills`) consumes the generated controller endpoints + blueprint to scaffold nexacro forms.
