import shutil
from pathlib import Path

import pytest

from scripts.workflow import jdbc_smoke


def _write_min_sql(scaffold: Path, *, stage3: bool = False) -> tuple[Path, Path]:
    if stage3:
        res = scaffold / "3-mybatis" / "src" / "main" / "resources"
    else:
        res = scaffold / "2-ddl"
    res.mkdir(parents=True)
    schema = res / "schema.sql"
    data = res / "data.sql"
    schema.write_text("CREATE TABLE t(id INT PRIMARY KEY, name VARCHAR(20))^^", encoding="utf-8")
    data.write_text("INSERT INTO t VALUES (1, 'a')^^INSERT INTO t VALUES (2, 'b')^^", encoding="utf-8")
    return schema, data


def test_discover_sql_prefers_stage3(tmp_path):
    scaffold = tmp_path / "s"
    _write_min_sql(scaffold, stage3=True)
    schema, data = jdbc_smoke.discover_sql(scaffold)
    assert "3-mybatis" in str(schema)
    assert "3-mybatis" in str(data)


def test_discover_sql_falls_back_to_2ddl(tmp_path):
    scaffold = tmp_path / "s"
    _write_min_sql(scaffold, stage3=False)
    schema, data = jdbc_smoke.discover_sql(scaffold)
    assert schema.parent.name == "2-ddl"


def test_discover_sql_returns_none_when_missing(tmp_path):
    assert jdbc_smoke.discover_sql(tmp_path) == (None, None)


def test_find_hsqldb_jar_honors_env(tmp_path, monkeypatch):
    fake = tmp_path / "hsqldb.jar"
    fake.write_text("")
    monkeypatch.setenv("HSQLDB_JAR", str(fake))
    assert jdbc_smoke.find_hsqldb_jar() == fake


def test_find_hsqldb_jar_env_missing_falls_through(tmp_path, monkeypatch):
    monkeypatch.setenv("HSQLDB_JAR", str(tmp_path / "nope.jar"))
    # may still hit a fallback path on this dev machine; just assert it doesn't raise
    jdbc_smoke.find_hsqldb_jar()


def test_run_smoke_skips_when_no_jar(tmp_path, monkeypatch):
    s, d = _write_min_sql(tmp_path / "s")
    monkeypatch.setattr(jdbc_smoke, "find_hsqldb_jar", lambda: None)
    r = jdbc_smoke.run_smoke(s, d)
    assert r.skipped is True
    assert r.ok is True  # skipped doesn't block downstream layers
    assert "HSQLDB_JAR" in r.reason


def test_run_smoke_skips_when_no_java(tmp_path, monkeypatch):
    s, d = _write_min_sql(tmp_path / "s")
    monkeypatch.setattr(jdbc_smoke, "find_hsqldb_jar", lambda: tmp_path / "fake.jar")
    (tmp_path / "fake.jar").write_text("")
    monkeypatch.setattr(jdbc_smoke.shutil, "which", lambda x: None)
    r = jdbc_smoke.run_smoke(s, d, java_exe="java-missing")
    assert r.skipped is True
    assert "java-missing" in r.reason


def test_run_smoke_reports_missing_schema(tmp_path, monkeypatch):
    monkeypatch.setattr(jdbc_smoke, "find_hsqldb_jar", lambda: tmp_path / "fake.jar")
    (tmp_path / "fake.jar").write_text("")
    r = jdbc_smoke.run_smoke(tmp_path / "no-schema.sql", tmp_path / "no-data.sql")
    assert r.ok is False
    assert "schema missing" in r.reason


_HSQLDB_JAR = jdbc_smoke.find_hsqldb_jar()


@pytest.mark.skipif(_HSQLDB_JAR is None or shutil.which("java") is None,
                    reason="no hsqldb jar or java on PATH")
def test_run_smoke_real_hsqldb_schema_data_pass(tmp_path):
    s, d = _write_min_sql(tmp_path / "s")
    r = jdbc_smoke.run_smoke(s, d)
    assert r.ok is True, f"stderr: {r.stderr}\nstdout: {r.stdout}"
    assert "schema+data applied OK" in r.stdout


@pytest.mark.skipif(_HSQLDB_JAR is None or shutil.which("java") is None,
                    reason="no hsqldb jar or java on PATH")
def test_run_smoke_real_hsqldb_invariant_pass(tmp_path):
    s, d = _write_min_sql(tmp_path / "s")
    r = jdbc_smoke.run_smoke(s, d, invariant="SELECT COUNT(*) FROM t=2")
    assert r.ok is True, f"stderr: {r.stderr}\nstdout: {r.stdout}"
    assert "invariant OK" in r.stdout


@pytest.mark.skipif(_HSQLDB_JAR is None or shutil.which("java") is None,
                    reason="no hsqldb jar or java on PATH")
def test_run_smoke_real_hsqldb_invariant_fail(tmp_path):
    s, d = _write_min_sql(tmp_path / "s")
    r = jdbc_smoke.run_smoke(s, d, invariant="SELECT COUNT(*) FROM t=99")
    assert r.ok is False
    assert "invariant FAIL" in r.stderr


@pytest.mark.skipif(_HSQLDB_JAR is None or shutil.which("java") is None,
                    reason="no hsqldb jar or java on PATH")
def test_run_smoke_real_hsqldb_bad_schema_fails(tmp_path):
    res = tmp_path / "s" / "2-ddl"
    res.mkdir(parents=True)
    (res / "schema.sql").write_text("CREATE TABL bad_syntax(", encoding="utf-8")
    (res / "data.sql").write_text("", encoding="utf-8")
    r = jdbc_smoke.run_smoke(res / "schema.sql", res / "data.sql")
    assert r.ok is False
    assert "FAIL" in r.stderr
