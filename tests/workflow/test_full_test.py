import pytest
from scripts.workflow import full_test, live_probe, live_runner, jdbc_smoke


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

    full, partial = full_test.run_l4_live("nexacro", scaffold)
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

    full, partial = full_test.run_l4_live("nexacro", scaffold)
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

    full, partial = full_test.run_l4_live("nexacro", scaffold)
    assert full is False
    assert partial is False


def test_run_l4_live_fail_when_rebuild_fails(tmp_path, monkeypatch):
    scaffold = _make_fake_scaffold(tmp_path, "finance")
    runner = _make_fake_runner(tmp_path)
    monkeypatch.setattr(full_test, "runner_path_for", lambda lane: runner)
    monkeypatch.setattr(full_test, "_mvn_rebuild_runner", lambda d: False)
    full, partial = full_test.run_l4_live("nexacro", scaffold)
    assert (full, partial) == (False, False)


def test_run_l4_live_fail_when_runner_dir_missing(tmp_path, monkeypatch):
    scaffold = _make_fake_scaffold(tmp_path, "finance")
    monkeypatch.setattr(full_test, "runner_path_for", lambda lane: tmp_path / "does-not-exist")
    full, partial = full_test.run_l4_live("nexacro", scaffold)
    assert (full, partial) == (False, False)


# ---- Growth-36: lane-aware probe dispatch (REST JSON for jakarta/javax/vanilla) ----

def _make_stage3_scaffold(root, slug):
    """Mirror real Stage 3 layout: com.nexacro.uiadapter.<slug>, sql under 3-mybatis/resources, mapper singular."""
    scaffold = root / f"{slug}-stage3"
    java_root = scaffold / "3-mybatis" / "src" / "main" / "java" / "com" / "nexacro" / "uiadapter" / slug
    (java_root / "controller").mkdir(parents=True)
    (java_root / "controller" / "LeadController.java").write_text(
        f"package com.nexacro.uiadapter.{slug}.controller;\npublic class LeadController {{}}\n",
        encoding="utf-8",
    )
    res = scaffold / "3-mybatis" / "src" / "main" / "resources"
    res.mkdir(parents=True)
    (res / "schema.sql").write_text("CREATE TABLE lead (id BIGINT);", encoding="utf-8")
    (res / "data.sql").write_text("INSERT INTO lead(id) VALUES(0);", encoding="utf-8")
    mapper_dir = res / "mybatis" / "mapper"
    mapper_dir.mkdir(parents=True)
    (mapper_dir / "LeadMapper.xml").write_text("<?xml version='1.0'?><mapper/>", encoding="utf-8")
    return scaffold


@pytest.mark.parametrize("lane", ["jakarta", "javax", "vanilla"])
def test_run_l4_live_rest_lane_uses_json_probe(lane, tmp_path, monkeypatch):
    """jakarta/javax/vanilla Stage 3 emits /api/<entity> REST → must use probe_endpoint_json, not envelope."""
    scaffold = _make_stage3_scaffold(tmp_path, "sales")
    runner = _make_fake_runner(tmp_path)
    monkeypatch.setattr(full_test, "runner_path_for", lambda lane: runner)
    monkeypatch.setattr(full_test, "_mvn_rebuild_runner", lambda d: True)
    handle = live_runner.LiveRunnerHandle(process=None, log_path=runner / "was.log", port=8080)
    monkeypatch.setattr(full_test.live_runner, "start_runner", lambda *a, **kw: handle)
    monkeypatch.setattr(full_test.live_runner, "wait_until_ready", lambda *a, **kw: True)
    monkeypatch.setattr(full_test.live_runner, "stop_runner", lambda *a, **kw: None)

    json_calls = {"count": 0, "url": None}
    def fake_json_probe(url, **kw):
        json_calls["count"] += 1
        json_calls["url"] = url
        return live_probe.ProbeResult(http_status=200, error_code=0, row_count=3, ok=True)
    def envelope_should_not_be_called(url, **kw):
        raise AssertionError(f"envelope probe must not run for lane={lane}; url={url}")

    monkeypatch.setattr(full_test.live_probe, "probe_endpoint_json", fake_json_probe)
    monkeypatch.setattr(full_test.live_probe, "probe_endpoint", envelope_should_not_be_called)

    full, partial = full_test.run_l4_live(lane, scaffold)
    assert full is True and partial is True
    assert json_calls["count"] == 1
    assert json_calls["url"] == "http://localhost:8080/api/lead"


def test_run_l4_live_nexacro_lane_uses_envelope_probe(tmp_path, monkeypatch):
    """nexacro lane → POST `/uiadapter/<entity>/select_datalist_map.do` envelope."""
    scaffold = _make_fake_scaffold(tmp_path, "finance")
    runner = _make_fake_runner(tmp_path)
    monkeypatch.setattr(full_test, "runner_path_for", lambda lane: runner)
    monkeypatch.setattr(full_test, "_mvn_rebuild_runner", lambda d: True)
    handle = live_runner.LiveRunnerHandle(process=None, log_path=runner / "was.log", port=8080)
    monkeypatch.setattr(full_test.live_runner, "start_runner", lambda *a, **kw: handle)
    monkeypatch.setattr(full_test.live_runner, "wait_until_ready", lambda *a, **kw: True)
    monkeypatch.setattr(full_test.live_runner, "stop_runner", lambda *a, **kw: None)

    envelope_calls = {"url": None}
    def fake_envelope(url, **kw):
        envelope_calls["url"] = url
        return live_probe.ProbeResult(http_status=200, error_code=0, row_count=1, ok=True)
    def json_should_not_be_called(url, **kw):
        raise AssertionError(f"REST JSON probe must not run for nexacro lane; url={url}")

    monkeypatch.setattr(full_test.live_probe, "probe_endpoint", fake_envelope)
    monkeypatch.setattr(full_test.live_probe, "probe_endpoint_json", json_should_not_be_called)

    full, partial = full_test.run_l4_live("nexacro", scaffold)
    assert full is True
    assert envelope_calls["url"] == "http://localhost:8080/uiadapter/account/select_datalist_map.do"


# ---- Growth-37: L1 empty-skip guard + L2 real JDBC smoke wiring ----

def test_run_l1_pytest_fails_when_no_sibling_repos_exist(monkeypatch, tmp_path):
    """If every sibling repo is missing, L1 must FAIL — silent-pass would cascade."""
    monkeypatch.setattr(full_test, "SIBLING_REPOS", [tmp_path / "ghost-a", tmp_path / "ghost-b"])
    assert full_test.run_l1_pytest() is False


def test_run_l2_jdbc_fails_when_no_schema_or_data(tmp_path):
    """run_l2_jdbc must FAIL (not silently pass) when scaffold lacks schema/data."""
    assert full_test.run_l2_jdbc(tmp_path / "empty") is False


def test_run_l2_jdbc_passes_when_smoke_skipped(tmp_path, monkeypatch):
    """Missing HSQLDB_JAR → SKIPPED but L2 returns True (does not block L3/L4)."""
    scaffold = tmp_path / "s"
    (scaffold / "2-ddl").mkdir(parents=True)
    (scaffold / "2-ddl" / "schema.sql").write_text("CREATE TABLE t(id INT);", encoding="utf-8")
    (scaffold / "2-ddl" / "data.sql").write_text("", encoding="utf-8")
    monkeypatch.setattr(full_test.jdbc_smoke, "run_smoke",
                        lambda s, d: jdbc_smoke.SmokeResult(ok=True, skipped=True, reason="test-skip"))
    assert full_test.run_l2_jdbc(scaffold) is True


def test_run_l2_jdbc_fails_on_smoke_error(tmp_path, monkeypatch):
    scaffold = tmp_path / "s"
    (scaffold / "2-ddl").mkdir(parents=True)
    (scaffold / "2-ddl" / "schema.sql").write_text("CREATE TABLE t(id INT);", encoding="utf-8")
    (scaffold / "2-ddl" / "data.sql").write_text("", encoding="utf-8")
    monkeypatch.setattr(full_test.jdbc_smoke, "run_smoke",
                        lambda s, d: jdbc_smoke.SmokeResult(ok=False, reason="exit 1", stderr="bad SQL"))
    assert full_test.run_l2_jdbc(scaffold) is False


def test_run_l2_jdbc_passes_on_smoke_ok(tmp_path, monkeypatch):
    scaffold = tmp_path / "s"
    (scaffold / "2-ddl").mkdir(parents=True)
    (scaffold / "2-ddl" / "schema.sql").write_text("CREATE TABLE t(id INT);", encoding="utf-8")
    (scaffold / "2-ddl" / "data.sql").write_text("", encoding="utf-8")
    monkeypatch.setattr(full_test.jdbc_smoke, "run_smoke",
                        lambda s, d: jdbc_smoke.SmokeResult(ok=True, stdout="[L2] OK"))
    assert full_test.run_l2_jdbc(scaffold) is True


# ---- Growth-38: L3 pom search generalization + lane pre-validation ----

def test_find_pom_prefers_overlay(tmp_path):
    """5-overlay/pom.xml wins when both overlay and 3-mybatis pom exist."""
    (tmp_path / "5-overlay").mkdir()
    overlay = tmp_path / "5-overlay" / "pom.xml"
    overlay.write_text("<project/>", encoding="utf-8")
    (tmp_path / "3-mybatis").mkdir()
    (tmp_path / "3-mybatis" / "pom.xml").write_text("<project/>", encoding="utf-8")
    assert full_test._find_pom(tmp_path) == overlay


def test_find_pom_falls_back_to_3mybatis(tmp_path):
    """When 5-overlay is absent (Stage 3-only scaffold), 3-mybatis/pom.xml is used."""
    (tmp_path / "3-mybatis").mkdir()
    p = tmp_path / "3-mybatis" / "pom.xml"
    p.write_text("<project/>", encoding="utf-8")
    assert full_test._find_pom(tmp_path) == p


def test_find_pom_falls_back_to_root(tmp_path):
    """Root pom.xml is the last fallback (legacy fixture layout)."""
    p = tmp_path / "pom.xml"
    p.write_text("<project/>", encoding="utf-8")
    assert full_test._find_pom(tmp_path) == p


def test_find_pom_returns_none_when_missing(tmp_path):
    assert full_test._find_pom(tmp_path) is None


def test_run_l3_mvn_fails_when_no_pom_anywhere(tmp_path):
    assert full_test.run_l3_mvn(tmp_path) is False


def test_run_l3_mvn_uses_3mybatis_pom_when_overlay_absent(tmp_path, monkeypatch):
    """Verify L3 actually drives mvn on the 3-mybatis pom when overlay is absent."""
    pom = tmp_path / "3-mybatis" / "pom.xml"
    pom.parent.mkdir()
    pom.write_text("<project/>", encoding="utf-8")

    captured = {}
    class _Result:
        returncode = 0
    def fake_run(cmd, cwd, capture_output, text, timeout):
        captured["cwd"] = cwd
        captured["cmd"] = cmd
        return _Result()
    monkeypatch.setattr(full_test.subprocess, "run", fake_run)
    assert full_test.run_l3_mvn(tmp_path) is True
    assert captured["cwd"] == pom.parent


def test_run_rejects_unknown_lane(tmp_path, monkeypatch):
    """run() must fail fast with clear error before L1/L2/L3, not somewhere deep in L4."""
    # Make scaffold-finder return a real dir so the lane check is what trips
    fake = tmp_path / "scaffold"
    fake.mkdir()
    monkeypatch.setattr(full_test, "find_latest_scaffold", lambda: fake)
    with pytest.raises(ValueError, match="unknown lane"):
        full_test.run("not-a-real-lane")


# ---- Growth-39: --json output mode + structured result ----

def _stub_all_layers_pass(monkeypatch, tmp_path):
    """Helper: mock every layer so main()/run() finish without doing real work."""
    fake = tmp_path / "scaffold-x"
    fake.mkdir()
    monkeypatch.setattr(full_test, "find_latest_scaffold", lambda: fake)
    monkeypatch.setattr(full_test, "run_l1_pytest", lambda: True)
    monkeypatch.setattr(full_test, "run_l2_jdbc", lambda s: True)
    monkeypatch.setattr(full_test, "run_l3_mvn", lambda s: True)
    monkeypatch.setattr(full_test, "run_l4_live", lambda lane, s, **kw: (True, True))
    # silence cleanup + learn-log side-effects
    monkeypatch.setattr(full_test.cleanup_runner, "run", lambda lane: {"ok": True})
    monkeypatch.setattr(full_test.cleanup_runner, "format_report", lambda r: "[cleanup] ok")
    monkeypatch.setattr(full_test.learn_log, "latest_growth_num", lambda: 99)
    monkeypatch.setattr(full_test.learn_log, "update_label", lambda n, label: None)
    return fake


def test_run_returns_result_object_with_layers(tmp_path, monkeypatch):
    """run() returns a FullTestResult dataclass (not bare string) with layers/lane/scaffold."""
    fake = _stub_all_layers_pass(monkeypatch, tmp_path)
    result = full_test.run("jakarta")
    assert result.label == "풀테스트 그린"
    assert result.layers["L1"] is True
    assert result.layers["L2"] is True
    assert result.layers["L3"] is True
    assert result.layers["L4_full"] is True
    assert result.lane == "jakarta"
    assert str(result.scaffold) == str(fake)


def test_full_test_result_str_is_label(tmp_path, monkeypatch):
    """str(result) == label keeps `print(run(...))` callers working unchanged."""
    _stub_all_layers_pass(monkeypatch, tmp_path)
    result = full_test.run("jakarta")
    assert str(result) == result.label


def test_main_json_mode_emits_structured_json(tmp_path, monkeypatch, capsys):
    """--json: stdout is parseable JSON with label/layers/lane/scaffold; exit 0 on green."""
    import json
    _stub_all_layers_pass(monkeypatch, tmp_path)
    rc = full_test.main(["jakarta", "--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["label"] == "풀테스트 그린"
    assert payload["lane"] == "jakarta"
    assert payload["layers"]["L4_full"] is True
    assert "scaffold" in payload
    assert rc == 0


def test_main_text_mode_prints_label_line(tmp_path, monkeypatch, capsys):
    """Without --json, the legacy `LABEL: ...` text line is preserved."""
    _stub_all_layers_pass(monkeypatch, tmp_path)
    rc = full_test.main(["jakarta"])
    captured = capsys.readouterr()
    assert "LABEL: 풀테스트 그린" in captured.out
    assert rc == 0


def test_main_json_mode_keeps_human_output_off_stdout(tmp_path, monkeypatch, capsys):
    """--json: layer progress prints (cleanup banner etc.) must not pollute stdout JSON."""
    import json
    _stub_all_layers_pass(monkeypatch, tmp_path)
    full_test.main(["jakarta", "--json"])
    captured = capsys.readouterr()
    # stdout must be a single JSON document, fully parseable end-to-end
    json.loads(captured.out)  # would raise if anything else got mixed in


def test_main_nonzero_exit_when_not_full_green(tmp_path, monkeypatch, capsys):
    """Anything short of 풀테스트 그린 → exit code != 0 so CI can branch on it."""
    fake = tmp_path / "s"; fake.mkdir()
    monkeypatch.setattr(full_test, "find_latest_scaffold", lambda: fake)
    monkeypatch.setattr(full_test, "run_l1_pytest", lambda: True)
    monkeypatch.setattr(full_test, "run_l2_jdbc", lambda s: True)
    monkeypatch.setattr(full_test, "run_l3_mvn", lambda s: True)
    monkeypatch.setattr(full_test, "run_l4_live", lambda lane, s, **kw: (False, True))
    monkeypatch.setattr(full_test.cleanup_runner, "run", lambda lane: {"ok": True})
    monkeypatch.setattr(full_test.cleanup_runner, "format_report", lambda r: "")
    monkeypatch.setattr(full_test.learn_log, "latest_growth_num", lambda: 99)
    monkeypatch.setattr(full_test.learn_log, "update_label", lambda n, label: None)
    rc = full_test.main(["jakarta", "--json"])
    assert rc != 0


# ---------- Growth-40: CRUD enrichment wiring ----------

def test_run_passes_layers_to_run_l4_live(tmp_path, monkeypatch):
    """run() must pass the layers dict so run_l4_live can write L4_crud/L4_crud_reason."""
    fake = tmp_path / "s"; fake.mkdir()
    captured = {}

    def fake_l4(lane, scaffold, layers=None):
        captured["layers_passed"] = layers
        # simulate run_l4_live writing CRUD enrichment
        if layers is not None:
            layers["L4_crud"] = True
            layers["L4_crud_reason"] = ""
        return (True, True)

    monkeypatch.setattr(full_test, "find_latest_scaffold", lambda: fake)
    monkeypatch.setattr(full_test, "run_l1_pytest", lambda: True)
    monkeypatch.setattr(full_test, "run_l2_jdbc", lambda s: True)
    monkeypatch.setattr(full_test, "run_l3_mvn", lambda s: True)
    monkeypatch.setattr(full_test, "run_l4_live", fake_l4)
    monkeypatch.setattr(full_test.cleanup_runner, "run", lambda lane: {"ok": True})
    monkeypatch.setattr(full_test.cleanup_runner, "format_report", lambda r: "")
    monkeypatch.setattr(full_test.learn_log, "latest_growth_num", lambda: 99)
    monkeypatch.setattr(full_test.learn_log, "update_label", lambda n, label: None)

    result = full_test.run("jakarta")
    assert captured["layers_passed"] is not None
    assert captured["layers_passed"] is result.layers  # same dict — mutation flows through
    assert result.layers["L4_crud"] is True


def test_json_output_includes_l4_crud(tmp_path, monkeypatch, capsys):
    """--json payload includes CRUD enrichment fields when L4 wrote them."""
    import json
    fake = tmp_path / "s"; fake.mkdir()

    def fake_l4(lane, scaffold, layers=None):
        if layers is not None:
            layers["L4_crud"] = False
            layers["L4_crud_reason"] = "insert failed (status=500, affected=-1)"
        return (True, True)

    monkeypatch.setattr(full_test, "find_latest_scaffold", lambda: fake)
    monkeypatch.setattr(full_test, "run_l1_pytest", lambda: True)
    monkeypatch.setattr(full_test, "run_l2_jdbc", lambda s: True)
    monkeypatch.setattr(full_test, "run_l3_mvn", lambda s: True)
    monkeypatch.setattr(full_test, "run_l4_live", fake_l4)
    monkeypatch.setattr(full_test.cleanup_runner, "run", lambda lane: {"ok": True})
    monkeypatch.setattr(full_test.cleanup_runner, "format_report", lambda r: "")
    monkeypatch.setattr(full_test.learn_log, "latest_growth_num", lambda: 99)
    monkeypatch.setattr(full_test.learn_log, "update_label", lambda n, label: None)

    full_test.main(["jakarta", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["layers"]["L4_crud"] is False
    assert "insert failed" in payload["layers"]["L4_crud_reason"]


def test_run_l4_live_writes_crud_for_rest_lane_when_layers_provided(tmp_path, monkeypatch):
    """REST lane: when caller passes layers and probe succeeds, CRUD round-trip runs.

    Uses the full run_l4_live (not a stub) but mocks: discover/overlay/build/start/ready/probe/crud.
    """
    from scripts.workflow import live_overlay, live_runner, live_probe, live_crud as lc

    scaffold = tmp_path / "scaffold"; scaffold.mkdir()
    data_sql = tmp_path / "data.sql"; data_sql.touch()
    mapper_dir = tmp_path / "mappers"; mapper_dir.mkdir()
    runner_dir = tmp_path / "runner"; runner_dir.mkdir()
    java_src = tmp_path / "java"; java_src.mkdir()

    plan = live_overlay.OverlayPlan(
        domain_slug="lead",
        schema_sql=tmp_path / "schema.sql",
        data_sql=data_sql,
        mapper_xml_dir=mapper_dir,
        java_src=java_src,
    )

    monkeypatch.setattr(full_test, "runner_path_for", lambda lane: runner_dir)
    monkeypatch.setattr(live_overlay, "discover_scaffold", lambda d: plan)
    monkeypatch.setattr(
        live_overlay, "apply_overlay",
        lambda r, p: type("X", (), {"files_written": [], "files_edited": []})(),
    )
    monkeypatch.setattr(full_test, "_mvn_rebuild_runner", lambda d: True)
    handle = type("H", (), {"port": 8080, "log_path": tmp_path / "x.log"})()
    monkeypatch.setattr(live_runner, "start_runner", lambda d: handle)
    monkeypatch.setattr(live_runner, "wait_until_ready", lambda h, **kw: True)
    monkeypatch.setattr(live_runner, "stop_runner", lambda h: None)
    monkeypatch.setattr(full_test, "derive_entity_slug", lambda d: "lead")

    verdict = type("V", (), {"http_status": 200, "error_code": 0, "row_count": 3, "ok": True})()
    monkeypatch.setattr(live_probe, "probe_endpoint_json", lambda url, **kw: verdict)

    monkeypatch.setattr(lc, "build_insert_template", lambda sql, ent: ({"id": 999001, "code": "L"}, 999001))
    monkeypatch.setattr(
        lc, "crud_roundtrip_rest",
        lambda url, insert_row, pk_column, pk_value, **kw: lc.CrudResult(ok=True, reason=""),
    )

    layers: dict = {}
    full, partial = full_test.run_l4_live("jakarta", scaffold, layers=layers)
    assert full is True
    assert layers["L4_crud"] is True
    assert layers["L4_crud_reason"] == ""


def test_run_l4_live_crud_skipped_when_layers_not_provided(tmp_path, monkeypatch):
    """Back-compat: legacy 2-arg call (no layers) skips CRUD entirely."""
    from scripts.workflow import live_overlay, live_runner, live_probe, live_crud as lc

    scaffold = tmp_path / "scaffold"; scaffold.mkdir()
    runner_dir = tmp_path / "runner"; runner_dir.mkdir()
    java_src = tmp_path / "java"; java_src.mkdir()
    plan = live_overlay.OverlayPlan(
        domain_slug="lead",
        schema_sql=tmp_path / "schema.sql",
        data_sql=tmp_path / "data.sql",
        mapper_xml_dir=tmp_path / "mappers",
        java_src=java_src,
    )
    plan.mapper_xml_dir.mkdir()

    monkeypatch.setattr(full_test, "runner_path_for", lambda lane: runner_dir)
    monkeypatch.setattr(live_overlay, "discover_scaffold", lambda d: plan)
    monkeypatch.setattr(
        live_overlay, "apply_overlay",
        lambda r, p: type("X", (), {"files_written": [], "files_edited": []})(),
    )
    monkeypatch.setattr(full_test, "_mvn_rebuild_runner", lambda d: True)
    handle = type("H", (), {"port": 8080, "log_path": tmp_path / "x.log"})()
    monkeypatch.setattr(live_runner, "start_runner", lambda d: handle)
    monkeypatch.setattr(live_runner, "wait_until_ready", lambda h, **kw: True)
    monkeypatch.setattr(live_runner, "stop_runner", lambda h: None)
    monkeypatch.setattr(full_test, "derive_entity_slug", lambda d: "lead")
    verdict = type("V", (), {"http_status": 200, "error_code": 0, "row_count": 3, "ok": True})()
    monkeypatch.setattr(live_probe, "probe_endpoint_json", lambda url, **kw: verdict)

    called = {"n": 0}
    monkeypatch.setattr(
        lc, "build_insert_template",
        lambda *a, **kw: (called.__setitem__("n", called["n"] + 1), None)[1],
    )

    full, partial = full_test.run_l4_live("jakarta", scaffold)
    assert full is True
    assert called["n"] == 0  # CRUD module never touched when layers not passed


def test_run_l4_live_crud_records_missing_template(tmp_path, monkeypatch):
    """REST lane: when no MERGE template found, layers records skip reason."""
    from scripts.workflow import live_overlay, live_runner, live_probe, live_crud as lc

    scaffold = tmp_path / "scaffold"; scaffold.mkdir()
    runner_dir = tmp_path / "runner"; runner_dir.mkdir()
    java_src = tmp_path / "java"; java_src.mkdir()
    plan = live_overlay.OverlayPlan(
        domain_slug="lead",
        schema_sql=tmp_path / "schema.sql",
        data_sql=tmp_path / "data.sql",
        mapper_xml_dir=tmp_path / "mappers",
        java_src=java_src,
    )
    plan.mapper_xml_dir.mkdir()

    monkeypatch.setattr(full_test, "runner_path_for", lambda lane: runner_dir)
    monkeypatch.setattr(live_overlay, "discover_scaffold", lambda d: plan)
    monkeypatch.setattr(
        live_overlay, "apply_overlay",
        lambda r, p: type("X", (), {"files_written": [], "files_edited": []})(),
    )
    monkeypatch.setattr(full_test, "_mvn_rebuild_runner", lambda d: True)
    handle = type("H", (), {"port": 8080, "log_path": tmp_path / "x.log"})()
    monkeypatch.setattr(live_runner, "start_runner", lambda d: handle)
    monkeypatch.setattr(live_runner, "wait_until_ready", lambda h, **kw: True)
    monkeypatch.setattr(live_runner, "stop_runner", lambda h: None)
    monkeypatch.setattr(full_test, "derive_entity_slug", lambda d: "lead")
    verdict = type("V", (), {"http_status": 200, "error_code": 0, "row_count": 3, "ok": True})()
    monkeypatch.setattr(live_probe, "probe_endpoint_json", lambda url, **kw: verdict)

    monkeypatch.setattr(lc, "build_insert_template", lambda *a, **kw: None)

    layers: dict = {}
    full_test.run_l4_live("jakarta", scaffold, layers=layers)
    assert layers["L4_crud"] is False
    assert "no MERGE template" in layers["L4_crud_reason"]


def test_run_l4_live_crud_skipped_for_nexacro_lane(tmp_path, monkeypatch):
    """Nexacro lane: CRUD enrichment is deferred to a future Growth — must NOT run."""
    from scripts.workflow import live_overlay, live_runner, live_probe, live_crud as lc

    scaffold = tmp_path / "scaffold"; scaffold.mkdir()
    runner_dir = tmp_path / "runner"; runner_dir.mkdir()
    java_src = tmp_path / "java"; java_src.mkdir()
    plan = live_overlay.OverlayPlan(
        domain_slug="lead",
        schema_sql=tmp_path / "schema.sql",
        data_sql=tmp_path / "data.sql",
        mapper_xml_dir=tmp_path / "mappers",
        java_src=java_src,
    )
    plan.mapper_xml_dir.mkdir()

    monkeypatch.setattr(full_test, "runner_path_for", lambda lane: runner_dir)
    monkeypatch.setattr(live_overlay, "discover_scaffold", lambda d: plan)
    monkeypatch.setattr(
        live_overlay, "apply_overlay",
        lambda r, p: type("X", (), {"files_written": [], "files_edited": []})(),
    )
    monkeypatch.setattr(full_test, "_mvn_rebuild_runner", lambda d: True)
    handle = type("H", (), {"port": 8080, "log_path": tmp_path / "x.log"})()
    monkeypatch.setattr(live_runner, "start_runner", lambda d: handle)
    monkeypatch.setattr(live_runner, "wait_until_ready", lambda h, **kw: True)
    monkeypatch.setattr(live_runner, "stop_runner", lambda h: None)
    monkeypatch.setattr(full_test, "derive_entity_slug", lambda d: "lead")
    verdict = type("V", (), {"http_status": 200, "error_code": 0, "row_count": 3, "ok": True})()
    monkeypatch.setattr(live_probe, "probe_endpoint", lambda url, **kw: verdict)

    called = {"n": 0}
    monkeypatch.setattr(lc, "build_insert_template", lambda *a, **kw: (called.__setitem__("n", called["n"] + 1), None)[1])

    layers: dict = {}
    full_test.run_l4_live("nexacro", scaffold, layers=layers)
    assert called["n"] == 0
    assert "L4_crud" not in layers
