import pytest
from scripts.workflow import full_test, live_probe, live_runner


def _make_fake_scaffold(root, slug):
    scaffold = root / slug
    ddl = scaffold / "2-ddl"
    ddl.mkdir(parents=True)
    (ddl / "schema.sql").write_text("CREATE TABLE x(id INT);", encoding="utf-8")
    (ddl / "data.sql").write_text("INSERT INTO x VALUES(1);", encoding="utf-8")
    java = scaffold / "3-mybatis" / "src" / "main" / "java" / "com" / "example" / slug
    java.mkdir(parents=True)
    (java / "Dummy.java").write_text("package com.example." + slug + ";\nclass Dummy{}", encoding="utf-8")
    mappers = scaffold / "3-mybatis" / "src" / "main" / "resources" / "mybatis" / "mappers"
    mappers.mkdir(parents=True)
    (mappers / "AccountMapper.xml").write_text("<?xml version='1.0'?><mapper/>", encoding="utf-8")
    return scaffold


def _make_fake_runner(root):
    runner = root / "runner-fake"
    pkg = runner / "src" / "main" / "java" / "com" / "nexacro" / "uiadapter"
    pkg.mkdir(parents=True)
    (pkg / "Application.java").write_text(
        '@SpringBootApplication(scanBasePackages = {"com.nexacro.uiadapter"})\n'
        '@MapperScan(basePackages = {"com.nexacro.uiadapter.mapper"})\n'
        'public class Application {}\n',
        encoding="utf-8",
    )
    (runner / "src" / "main" / "resources" / "mybatis" / "mappers").mkdir(parents=True)
    (runner / "src" / "main" / "resources" / "application.yml").write_text(
        "spring:\n  sql:\n    init:\n      schema-locations: classpath:schema.sql\n"
        "      data-locations: classpath:data.sql\n",
        encoding="utf-8",
    )
    return runner


def test_decide_label_all_pass():
    layers = {"L1": True, "L2": True, "L3": True, "L4_full": True}
    assert full_test.decide_label(layers) == "풀테스트 그린"

def test_decide_label_l4_partial():
    layers = {"L1": True, "L2": True, "L3": True, "L4_partial": True}
    assert full_test.decide_label(layers) == "라이브 WAS 부분검증"

def test_decide_label_l4_failed():
    layers = {"L1": True, "L2": True, "L3": True, "L4_full": False, "L4_partial": False}
    assert full_test.decide_label(layers) == "JDBC + 빌드까지만 검증"

def test_decide_label_l3_missing():
    layers = {"L1": True, "L2": True}
    assert full_test.decide_label(layers) == "JDBC 까지만 검증"

def test_decide_label_l1_fail_aborts():
    layers = {"L1": False}
    assert full_test.decide_label(layers) == "단위 테스트 실패 — 검증 중단"

def test_lane_default_runner_resolution():
    assert full_test.runner_for("jakarta") == "boot-jdk17-jakarta"
    assert full_test.runner_for("vanilla") == "boot-jdk8-javax"


def test_runner_path_for_resolves_to_runner_dir():
    p = full_test.runner_path_for("jakarta")
    assert p.name == "boot-jdk17-jakarta"
    assert "runners" in str(p)


def test_derive_entity_slug_picks_first_mapper(tmp_path):
    (tmp_path / "account-mapper.xml").write_text("", encoding="utf-8")
    (tmp_path / "journalentry-mapper.xml").write_text("", encoding="utf-8")
    assert full_test.derive_entity_slug(tmp_path) == "account"


def test_derive_entity_slug_none_when_empty(tmp_path):
    assert full_test.derive_entity_slug(tmp_path) is None


def test_run_l4_live_full_pass(tmp_path, monkeypatch):
    scaffold = _make_fake_scaffold(tmp_path, "finance")
    runner = _make_fake_runner(tmp_path)
    monkeypatch.setattr(full_test, "runner_path_for", lambda lane: runner)
    monkeypatch.setattr(full_test, "_mvn_rebuild_runner", lambda d: True)

    handle = live_runner.LiveRunnerHandle(process=None, log_path=runner / "was.log", port=8080)
    monkeypatch.setattr(full_test.live_runner, "start_runner", lambda *a, **kw: handle)
    monkeypatch.setattr(full_test.live_runner, "wait_until_ready", lambda *a, **kw: True)
    monkeypatch.setattr(full_test.live_runner, "stop_runner", lambda *a, **kw: None)
    monkeypatch.setattr(
        full_test.live_probe, "probe_endpoint",
        lambda url, **kw: live_probe.ProbeResult(http_status=200, error_code=0, row_count=2, ok=True),
    )

    full, partial = full_test.run_l4_live("jakarta", scaffold)
    assert full is True
    assert partial is True


def test_run_l4_live_partial_when_probe_fails(tmp_path, monkeypatch):
    scaffold = _make_fake_scaffold(tmp_path, "finance")
    runner = _make_fake_runner(tmp_path)
    monkeypatch.setattr(full_test, "runner_path_for", lambda lane: runner)
    monkeypatch.setattr(full_test, "_mvn_rebuild_runner", lambda d: True)
    handle = live_runner.LiveRunnerHandle(process=None, log_path=runner / "was.log", port=8080)
    monkeypatch.setattr(full_test.live_runner, "start_runner", lambda *a, **kw: handle)
    monkeypatch.setattr(full_test.live_runner, "wait_until_ready", lambda *a, **kw: True)
    monkeypatch.setattr(full_test.live_runner, "stop_runner", lambda *a, **kw: None)
    monkeypatch.setattr(
        full_test.live_probe, "probe_endpoint",
        lambda url, **kw: live_probe.ProbeResult(http_status=500, error_code=-999, ok=False),
    )

    full, partial = full_test.run_l4_live("jakarta", scaffold)
    assert full is False
    assert partial is True


def test_run_l4_live_fail_when_runner_doesnt_start(tmp_path, monkeypatch):
    scaffold = _make_fake_scaffold(tmp_path, "finance")
    runner = _make_fake_runner(tmp_path)
    monkeypatch.setattr(full_test, "runner_path_for", lambda lane: runner)
    monkeypatch.setattr(full_test, "_mvn_rebuild_runner", lambda d: True)
    handle = live_runner.LiveRunnerHandle(process=None, log_path=runner / "was.log", port=8080)
    monkeypatch.setattr(full_test.live_runner, "start_runner", lambda *a, **kw: handle)
    monkeypatch.setattr(full_test.live_runner, "wait_until_ready", lambda *a, **kw: False)
    monkeypatch.setattr(full_test.live_runner, "stop_runner", lambda *a, **kw: None)

    full, partial = full_test.run_l4_live("jakarta", scaffold)
    assert full is False
    assert partial is False


def test_run_l4_live_fail_when_rebuild_fails(tmp_path, monkeypatch):
    scaffold = _make_fake_scaffold(tmp_path, "finance")
    runner = _make_fake_runner(tmp_path)
    monkeypatch.setattr(full_test, "runner_path_for", lambda lane: runner)
    monkeypatch.setattr(full_test, "_mvn_rebuild_runner", lambda d: False)
    full, partial = full_test.run_l4_live("jakarta", scaffold)
    assert (full, partial) == (False, False)


def test_run_l4_live_fail_when_runner_dir_missing(tmp_path, monkeypatch):
    scaffold = _make_fake_scaffold(tmp_path, "finance")
    monkeypatch.setattr(full_test, "runner_path_for", lambda lane: tmp_path / "does-not-exist")
    full, partial = full_test.run_l4_live("jakarta", scaffold)
    assert (full, partial) == (False, False)
