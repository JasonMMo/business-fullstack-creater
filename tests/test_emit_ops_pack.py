"""Growth-71 — tests for scripts/emit_ops_pack.py."""
from __future__ import annotations

import pathlib
import textwrap

import pytest

from scripts import emit_ops_pack as eop


# ---------------------------------------------------------------------------
# Fixture builder — minimal scaffold output (just enough pom.xml to inspect)
# ---------------------------------------------------------------------------

def _write_scaffold(
    out: pathlib.Path,
    *,
    artifact_id: str = "shipping-shell",
    version: str = "0.1.0-SNAPSHOT",
    packaging: str = "war",
    lane: str = "jakarta",
    dialect: str = "postgres",
) -> pathlib.Path:
    shell = out / "shell"
    shell.mkdir(parents=True)
    (shell / "src").mkdir()
    lane_dep = (
        "<dependency><groupId>jakarta.servlet</groupId><artifactId>x</artifactId></dependency>"
        if lane == "jakarta"
        else "<dependency><groupId>javax.servlet</groupId><artifactId>x</artifactId></dependency>"
    )
    dialect_dep = {
        "postgres": "<dependency><groupId>org.postgresql</groupId><artifactId>postgresql</artifactId></dependency>",
        "mysql": "<dependency><groupId>com.mysql</groupId><artifactId>mysql-connector-j</artifactId></dependency>",
        "hsqldb": "<dependency><groupId>org.hsqldb</groupId><artifactId>hsqldb</artifactId></dependency>",
    }[dialect]
    (shell / "pom.xml").write_text(
        textwrap.dedent(
            f"""\
            <?xml version="1.0" encoding="UTF-8"?>
            <project xmlns="http://maven.apache.org/POM/4.0.0">
              <modelVersion>4.0.0</modelVersion>
              <groupId>com.example</groupId>
              <artifactId>{artifact_id}</artifactId>
              <version>{version}</version>
              <packaging>{packaging}</packaging>
              <dependencies>
                {lane_dep}
                {dialect_dep}
              </dependencies>
            </project>
            """
        ),
        encoding="utf-8",
    )
    return shell


# ---------------------------------------------------------------------------
# Inspection
# ---------------------------------------------------------------------------

def test_inspect_jakarta_postgres_war(tmp_path):
    _write_scaffold(tmp_path)
    info = eop.inspect_scaffold(tmp_path / "shell")
    assert info["artifact_id"] == "shipping-shell"
    assert info["packaging"] == "war"
    assert info["lane"] == "jakarta"
    assert info["dialect"] == "postgres"


def test_inspect_javax_mysql_jar(tmp_path):
    _write_scaffold(tmp_path, packaging="jar", lane="javax", dialect="mysql")
    info = eop.inspect_scaffold(tmp_path / "shell")
    assert info["packaging"] == "jar"
    assert info["lane"] == "javax"
    assert info["dialect"] == "mysql"


def test_inspect_missing_pom_raises(tmp_path):
    (tmp_path / "shell").mkdir()
    with pytest.raises(FileNotFoundError, match="pom.xml"):
        eop.inspect_scaffold(tmp_path / "shell")


# ---------------------------------------------------------------------------
# Dockerfile rendering
# ---------------------------------------------------------------------------

def test_dockerfile_war_jakarta_uses_tomcat10(tmp_path):
    _write_scaffold(tmp_path, packaging="war", lane="jakarta")
    info = eop.inspect_scaffold(tmp_path / "shell")
    dockerfile = eop.render_dockerfile(info)
    assert "FROM tomcat:10.1" in dockerfile
    assert "FROM maven:3.9-eclipse-temurin-17 AS builder" in dockerfile
    assert "shipping-shell-0.1.0-SNAPSHOT.war" in dockerfile
    assert "uiadapter.war" in dockerfile


def test_dockerfile_war_javax_uses_tomcat9(tmp_path):
    _write_scaffold(tmp_path, packaging="war", lane="javax")
    info = eop.inspect_scaffold(tmp_path / "shell")
    dockerfile = eop.render_dockerfile(info)
    assert "FROM tomcat:9.0" in dockerfile
    assert "tomcat:10" not in dockerfile


def test_dockerfile_jar_uses_temurin_jre(tmp_path):
    _write_scaffold(tmp_path, packaging="jar")
    info = eop.inspect_scaffold(tmp_path / "shell")
    dockerfile = eop.render_dockerfile(info)
    assert "FROM eclipse-temurin:17-jre" in dockerfile
    assert "ENTRYPOINT" in dockerfile
    assert "app.jar" in dockerfile


# ---------------------------------------------------------------------------
# docker-compose rendering — dialect branching
# ---------------------------------------------------------------------------

def test_compose_postgres_has_db_service_and_volume(tmp_path):
    _write_scaffold(tmp_path, dialect="postgres")
    info = eop.inspect_scaffold(tmp_path / "shell")
    compose = eop.render_compose(info, slug="acme")
    assert "image: postgres:16-alpine" in compose
    assert "ACME_DB_USER" in compose
    assert "depends_on:" in compose
    assert "volumes:" in compose
    assert "pg_isready" in compose


def test_compose_mysql_uses_mysql8(tmp_path):
    _write_scaffold(tmp_path, dialect="mysql")
    info = eop.inspect_scaffold(tmp_path / "shell")
    compose = eop.render_compose(info, slug="legacy")
    assert "image: mysql:8.0" in compose
    assert "LEGACY_DB_USER" in compose
    assert "mysqladmin" in compose


def test_compose_hsqldb_has_no_db_service(tmp_path):
    _write_scaffold(tmp_path, dialect="hsqldb")
    info = eop.inspect_scaffold(tmp_path / "shell")
    compose = eop.render_compose(info, slug="tiny")
    assert "image: postgres" not in compose
    assert "image: mysql" not in compose
    assert "depends_on:" not in compose
    # Still has the app service
    assert "app:" in compose


# ---------------------------------------------------------------------------
# .env rendering
# ---------------------------------------------------------------------------

def test_env_postgres_includes_db_block(tmp_path):
    _write_scaffold(tmp_path, dialect="postgres")
    info = eop.inspect_scaffold(tmp_path / "shell")
    env = eop.render_env_example(info, slug="acme")
    assert "APP_PORT=8080" in env
    assert "ACME_DB_HOST=db" in env
    assert "ACME_DB_PORT=5432" in env


def test_env_mysql_uses_3306(tmp_path):
    _write_scaffold(tmp_path, dialect="mysql")
    info = eop.inspect_scaffold(tmp_path / "shell")
    env = eop.render_env_example(info, slug="legacy")
    assert "LEGACY_DB_PORT=3306" in env


def test_env_hsqldb_skips_db_block(tmp_path):
    _write_scaffold(tmp_path, dialect="hsqldb")
    info = eop.inspect_scaffold(tmp_path / "shell")
    env = eop.render_env_example(info, slug="tiny")
    assert "embedded" in env
    assert "DB_HOST" not in env


# ---------------------------------------------------------------------------
# SOP rendering — Korean runbook
# ---------------------------------------------------------------------------

def test_sop_korean_runbook_present(tmp_path):
    _write_scaffold(tmp_path, dialect="postgres")
    info = eop.inspect_scaffold(tmp_path / "shell")
    sop = eop.render_sop(info, slug="acme")
    assert "배포 SOP — acme" in sop
    assert "docker compose up -d" in sop
    assert "ACME_DB_USER" in sop
    assert "트러블슈팅" in sop


def test_sop_embedded_dialect_skips_db_creds(tmp_path):
    _write_scaffold(tmp_path, dialect="hsqldb")
    info = eop.inspect_scaffold(tmp_path / "shell")
    sop = eop.render_sop(info, slug="tiny")
    assert "embedded" in sop
    assert "TINY_DB_USER" not in sop


# ---------------------------------------------------------------------------
# Profile override
# ---------------------------------------------------------------------------

def test_profile_overrides_slug_and_dialect(tmp_path):
    _write_scaffold(tmp_path, dialect="postgres", artifact_id="shipping-shell")
    profile = {
        "version": 1,
        "customer": {"slug": "acme"},
        "ddl": {"dialect": "mysql"},
    }
    ops = eop.emit(tmp_path, profile=profile, force=True)
    compose = (ops / "docker-compose.yml").read_text(encoding="utf-8")
    env = (ops / ".env.example").read_text(encoding="utf-8")
    sop = (ops / "DEPLOY-SOP.md").read_text(encoding="utf-8")
    # MySQL took effect even though pom signaled postgres
    assert "image: mysql:8.0" in compose
    # ACME slug → env prefix
    assert "ACME_DB_USER" in compose
    assert "ACME_DB_USER" in env
    assert "배포 SOP — acme" in sop


# ---------------------------------------------------------------------------
# emit() driver — all-4-artifact contract + idempotency
# ---------------------------------------------------------------------------

def test_emit_writes_all_four_artifacts(tmp_path):
    _write_scaffold(tmp_path)
    ops = eop.emit(tmp_path)
    assert (ops / "Dockerfile").exists()
    assert (ops / "docker-compose.yml").exists()
    assert (ops / ".env.example").exists()
    assert (ops / "DEPLOY-SOP.md").exists()


def test_emit_refuses_to_clobber_without_force(tmp_path):
    _write_scaffold(tmp_path)
    eop.emit(tmp_path)
    with pytest.raises(FileExistsError, match="--force"):
        eop.emit(tmp_path)
    # --force overwrites
    eop.emit(tmp_path, force=True)


def test_emit_accepts_shell_dir_directly(tmp_path):
    shell = _write_scaffold(tmp_path)
    ops = eop.emit(shell)  # callers may pass the shell/ itself
    assert (ops / "Dockerfile").exists()


# ---------------------------------------------------------------------------
# Profile loader contract
# ---------------------------------------------------------------------------

def test_load_profile_rejects_v2(tmp_path):
    p = tmp_path / "bad.yaml"
    p.write_text("version: 2\ncustomer: {slug: x}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="version: 1"):
        eop._load_profile(p)


def test_load_profile_returns_none_when_path_is_none():
    assert eop._load_profile(None) is None


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def test_cli_writes_ops_dir(tmp_path, capsys):
    _write_scaffold(tmp_path)
    rc = eop.main([str(tmp_path)])
    assert rc == 0
    assert "wrote" in capsys.readouterr().out
    assert (tmp_path / "shell" / "ops" / "Dockerfile").exists()


def test_cli_force_overwrite(tmp_path):
    _write_scaffold(tmp_path)
    assert eop.main([str(tmp_path)]) == 0
    assert eop.main([str(tmp_path)]) == 1  # existing ops/, no --force
    assert eop.main([str(tmp_path), "--force"]) == 0


def test_cli_rejects_missing_out_dir(tmp_path, capsys):
    rc = eop.main([str(tmp_path / "nope")])
    assert rc == 2
    assert "not a directory" in capsys.readouterr().err
