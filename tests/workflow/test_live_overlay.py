"""Tests for live_overlay — jakarta runner 5-point overlay."""
from pathlib import Path
import pytest
from scripts.workflow import live_overlay


@pytest.fixture
def fake_runner(tmp_path):
    """Build a minimal stand-in for boot-jdk17-jakarta runner."""
    runner = tmp_path / "runner"
    (runner / "src" / "main" / "java" / "com" / "nexacro" / "uiadapter").mkdir(parents=True)
    (runner / "src" / "main" / "resources" / "mybatis" / "mappers").mkdir(parents=True)
    app = runner / "src" / "main" / "java" / "com" / "nexacro" / "uiadapter" / "Application.java"
    app.write_text(
        "package com.nexacro.uiadapter;\n"
        "@SpringBootApplication(scanBasePackages = {\"com.nexacro.uiadapter\"})\n"
        "@MapperScan(basePackages = {\"com.nexacro.uiadapter.mapper\"})\n"
        "public class Application {}\n",
        encoding="utf-8",
    )
    yml = runner / "src" / "main" / "resources" / "application.yml"
    yml.write_text(
        "spring:\n"
        "  sql:\n"
        "    init:\n"
        "      schema-locations: classpath:schema.sql\n"
        "      data-locations: classpath:data.sql\n"
        "      separator: \"^^\"\n",
        encoding="utf-8",
    )
    return runner


@pytest.fixture
def fake_scaffold(tmp_path):
    """Build a minimal stand-in scaffold output (Stage 2 + Stage 3)."""
    scaffold = tmp_path / "scaffold"
    java = scaffold / "3-mybatis" / "src" / "main" / "java" / "com" / "example" / "finance"
    java.mkdir(parents=True)
    (java / "controller").mkdir()
    (java / "controller" / "AccountController.java").write_text(
        "package com.example.finance.controller;\npublic class AccountController {}\n",
        encoding="utf-8",
    )
    ddl = scaffold / "2-ddl"
    ddl.mkdir(parents=True)
    (ddl / "schema.sql").write_text(
        "CREATE TABLE account (id BIGINT IDENTITY PRIMARY KEY, code VARCHAR(40));\n"
        "CREATE TABLE journal_entry (id BIGINT IDENTITY PRIMARY KEY);\n",
        encoding="utf-8",
    )
    (ddl / "data.sql").write_text(
        "MERGE INTO account USING (VALUES(0,'1000'),(1,'4000')) AS s(id,code) "
        "ON account.id=s.id WHEN NOT MATCHED THEN INSERT VALUES(s.id,s.code);\n",
        encoding="utf-8",
    )
    mappers = scaffold / "3-mybatis" / "src" / "main" / "resources" / "mybatis" / "mappers"
    mappers.mkdir(parents=True)
    (mappers / "AccountMapper.xml").write_text(
        "<?xml version='1.0'?><mapper namespace='com.example.finance.mapper.AccountMapper'/>",
        encoding="utf-8",
    )
    return scaffold


def test_discover_scaffold_finds_paths(fake_scaffold):
    plan = live_overlay.discover_scaffold(fake_scaffold, "finance")
    assert plan.domain_slug == "finance"
    assert plan.schema_sql.exists()
    assert plan.data_sql.exists()
    assert plan.mapper_xml_dir.exists()
    assert plan.java_src.exists()
    java_files = list(plan.java_src.rglob("*.java"))
    assert any(f.name == "AccountController.java" for f in java_files)


def test_discover_scaffold_missing_ddl_raises(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(FileNotFoundError, match="schema.sql"):
        live_overlay.discover_scaffold(empty, "finance")


def test_apply_overlay_writes_5_points(fake_runner, fake_scaffold):
    plan = live_overlay.discover_scaffold(fake_scaffold, "finance")
    result = live_overlay.apply_overlay(fake_runner, plan)
    # 1. Application.java edited
    app = fake_runner / "src/main/java/com/nexacro/uiadapter/Application.java"
    text = app.read_text(encoding="utf-8")
    assert "com.example.finance" in text
    # 2. application.yml has appended schema/data locations
    yml = fake_runner / "src/main/resources/application.yml"
    yml_text = yml.read_text(encoding="utf-8")
    assert "finance-schema.sql" in yml_text
    assert "finance-data.sql" in yml_text
    # 3+4. domain-scoped sql files created with ^^ separator
    schema_out = fake_runner / "src/main/resources/finance-schema.sql"
    data_out = fake_runner / "src/main/resources/finance-data.sql"
    assert schema_out.exists() and data_out.exists()
    assert ";" not in schema_out.read_text(encoding="utf-8").rstrip()
    assert "^^" in schema_out.read_text(encoding="utf-8")
    # 5. mapper XML renamed kebab-case
    mapper_out = fake_runner / "src/main/resources/mybatis/mappers/account-mapper.xml"
    assert mapper_out.exists()
    # Java source copied
    java_copy = fake_runner / "src/main/java/com/example/finance/controller/AccountController.java"
    assert java_copy.exists()
    # Result tracks all writes
    assert len(result.files_written) >= 4
    assert len(result.files_edited) == 2


def test_apply_overlay_idempotent_application_java(fake_runner, fake_scaffold):
    plan = live_overlay.discover_scaffold(fake_scaffold, "finance")
    live_overlay.apply_overlay(fake_runner, plan)
    live_overlay.apply_overlay(fake_runner, plan)
    app_text = (fake_runner / "src/main/java/com/nexacro/uiadapter/Application.java").read_text(encoding="utf-8")
    # com.example.finance must appear exactly once in scanBasePackages and once in @MapperScan
    assert app_text.count("\"com.example.finance\"") == 1
    assert app_text.count("\"com.example.finance.mapper\"") == 1


def test_apply_overlay_yml_idempotent(fake_runner, fake_scaffold):
    plan = live_overlay.discover_scaffold(fake_scaffold, "finance")
    live_overlay.apply_overlay(fake_runner, plan)
    live_overlay.apply_overlay(fake_runner, plan)
    yml_text = (fake_runner / "src/main/resources/application.yml").read_text(encoding="utf-8")
    assert yml_text.count("finance-schema.sql") == 1
    assert yml_text.count("finance-data.sql") == 1


def test_pascalcase_to_kebab_naming():
    assert live_overlay._pascal_to_kebab("AccountMapper.xml") == "account-mapper.xml"
    assert live_overlay._pascal_to_kebab("JournalEntryMapper.xml") == "journalentry-mapper.xml"
    assert live_overlay._pascal_to_kebab("LedgerEntryMapper.xml") == "ledgerentry-mapper.xml"
