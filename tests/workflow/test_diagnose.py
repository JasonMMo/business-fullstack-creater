"""Tests for diagnose.py — Growth-52 (2026-05-26).

Each check is isolated against a synthetic workspace under tmp_path so the
suite doesn't depend on the real sibling repos. CLI smoke verifies exit codes
and JSON output shape.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.workflow import diagnose
from scripts.workflow.diagnose import Check


def _make_workspace(tmp_path: Path) -> tuple[Path, Path]:
    """Build a fake workspace with all sibling repos present.

    Returns (workspace_root, creater_root).
    """
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    for dirname in diagnose.LAYER_REPOS.values():
        (workspace / dirname).mkdir()
    # rdb-skill INDEX.md with 14 fake domains
    idx_dir = (
        workspace
        / "andrej-karpathy-rdb-skill"
        / ".claude"
        / "skills"
        / "karpathy-rdb"
        / "presets"
    )
    idx_dir.mkdir(parents=True)
    body = "# Preset Catalog\n\n"
    for i in range(14):
        body += f"## 도메인{i}\n- 한 줄: example\n\n"
    body += "## 매칭 알고리즘\n\n1. ...\n"
    (idx_dir / "INDEX.md").write_text(body, encoding="utf-8")
    # creater root + learn-log
    creater_root = workspace / "business-fullstack-creater"
    creater_root.mkdir()
    (creater_root / "learn-log.md").write_text(
        "# learn-log\n\n## 0. Layer Ownership Card\n\n| 축 |\n|---|\n",
        encoding="utf-8",
    )
    # runners + application.yml with /uiadapter context-path (G-50a guard)
    runners = workspace / "nexacroN-fullstack" / "samples" / "runners"
    runners.mkdir(parents=True)
    for name in diagnose.EXPECTED_RUNNERS:
        runner = runners / name
        runner.mkdir()
        res = runner / "src" / "main" / "resources"
        res.mkdir(parents=True)
        (res / "application.yml").write_text(
            "server:\n  servlet:\n    context-path: /uiadapter\n",
            encoding="utf-8",
        )
    # mybatis templates with {{ uia_namespace }} (G-47 guard)
    mybatis_tpl = (
        workspace
        / "andrej-karpathy-rdb-mybatis"
        / ".claude"
        / "skills"
        / "karpathy-rdb-mybatis"
        / "templates"
    )
    ctrl = mybatis_tpl / "controller"
    ctrl.mkdir(parents=True)
    (ctrl / "controller.java.j2").write_text(
        "import {{ lib_prefix }}.{{ uia_namespace }}.core.NexacroException;\n",
        encoding="utf-8",
    )
    svc = mybatis_tpl / "service"
    svc.mkdir(parents=True)
    (svc / "service-impl.java.j2").write_text(
        "import {{ lib_prefix }}.{{ uia_namespace }}.core.data.DataSetRowTypeAccessor;\n",
        encoding="utf-8",
    )
    # creater scripts with G-50b + G-48 guard strings
    scripts = creater_root / "scripts" / "workflow"
    scripts.mkdir(parents=True)
    (scripts / "lane_runner_map.py").write_text(
        'def lane_probe_url(...): return f"http://localhost:{port}/uiadapter/api/{entity}"\n',
        encoding="utf-8",
    )
    (scripts / "full_test.py").write_text(
        "scaffold_lane = live_overlay.discover_scaffold_lane(scaffold_dir)\n"
        "url = lane_probe_url(lane, port, entity, scaffold_lane=scaffold_lane)\n",
        encoding="utf-8",
    )
    # G-58 guard: scaffold_orchestrator.py with vanilla Stage 4 skip gate
    # G-74 guard: ops_pack auto-emit wiring (Growth-74 M3 Slice b)
    (creater_root / "scripts" / "scaffold_orchestrator.py").write_text(
        'def _run_stage4(args, stage_paths, report):\n'
        '    if args.lane == "vanilla":\n'
        '        report.stages_run.append("stage4-skipped-vanilla")\n'
        '        return\n'
        '\n'
        '# Growth-74 (M3 Slice b)\n'
        'def _run_emit_ops_pack(args, report):\n'
        '    import emit_ops_pack\n'
        '    if False:\n'
        '        report.stages_run.append("ops_pack-skipped-no-shell")\n'
        '        report.stages_run.append("ops_pack-failed")\n'
        '\n'
        'def run_scaffold(args):\n'
        '    _run_emit_ops_pack(args, report)\n',
        encoding="utf-8",
    )
    # G-61 guard: web_index._default_source_resolver with domain_slug=None
    (scripts / "web_index.py").write_text(
        "def _default_source_resolver(entry):\n"
        "    plan = discover_scaffold(scaffold_root, domain_slug=None)\n",
        encoding="utf-8",
    )
    # G-62 guard: scaffold_cli.py with customer-profile wiring (Growth-63)
    # G-63 guard: version != 1 condition present (Growth-65)
    (creater_root / "scripts" / "scaffold_cli.py").write_text(
        "def load_customer_profile(slug, *, profiles_root=None):\n"
        "    if version != 1: raise ValueError('expected 1')\n"
        'parser.add_argument("--customer-profile")\n'
        "args = ScaffoldArgs(customer_profile=profile)\n",
        encoding="utf-8",
    )
    # G-69 guard: web/adapters/scaffold_runner.py 가 subprocess.run 으로 scaffold_cli
    # 호출 + web/routes/domain.py 가 scaffold_runner.run 사용 (Growth-69)
    web_adapters = creater_root / "web" / "adapters"
    web_adapters.mkdir(parents=True, exist_ok=True)
    (web_adapters / "scaffold_runner.py").write_text(
        "import subprocess\n"
        "from web.settings import get_settings\n"
        "def run(request, *, timeout_sec=300):\n"
        "    cli_path = get_settings().scaffold_cli_path  # scaffold_cli.py\n"
        "    subprocess.run([cli_path], cwd='.')\n",
        encoding="utf-8",
    )
    web_routes = creater_root / "web" / "routes"
    web_routes.mkdir(parents=True, exist_ok=True)
    (web_routes / "domain.py").write_text(
        "from web.adapters import scaffold_runner\n"
        "def post():\n    result = scaffold_runner.run(req)\n",
        encoding="utf-8",
    )
    # G-70 guard: scripts/extract_target_profile.py emits v1 customer profile
    # (Growth-70 M5 Slice C). build_profile must stamp version: 1 + slug,
    # dump_profile header must reference Growth-70.
    # G-78 guard: same file also supports Gradle input (Growth-78 M5 Slice C-b)
    # — parse_gradle helper + Groovy/Kotlin regexes + settings.gradle fallback.
    scripts_dir = creater_root / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    (scripts_dir / "extract_target_profile.py").write_text(
        '"""Growth-70 + Growth-78 + Growth-81 extractor stub for diagnose test fixture."""\n'
        "import re\n"
        "_GRADLE_GROUP_RE = re.compile(r'group')\n"
        "_GRADLE_ROOT_NAME_RE = re.compile(r'rootProject.name')\n"
        "def _gradle_lane(raw): return 'jakarta'\n"
        "def _find_gradle_build(d):\n"
        "    # supports build.gradle.kts and build.gradle\n"
        "    return None\n"
        "def parse_gradle(p):\n"
        "    return {'group_id': None}\n"
        "def build_profile(project_dir, slug='x'):\n"
        '    return {"version": 1, "customer": {"slug": slug}}\n'
        "def dump_profile(profile):\n"
        '    return "# Auto-extracted Growth-70\\n"\n'
        "# Growth-81 multi-module support\n"
        "_GRADLE_INCLUDE_RE = re.compile(r'include')\n"
        "def _parse_includes(text): return []\n"
        "def _extract_modules(d): return []\n",
        encoding="utf-8",
    )
    # G-71 guard: scripts/emit_ops_pack.py emits all 4 ops artifacts +
    # multi-stage Docker builder (Growth-71 M3 Ops Pack).
    # G-76 guard: same file also carries Vault Agent sidecar contract markers
    # (Growth-76 M3 Slice d) — 3 render_vault_* helpers + AppRole + SOP §9 +
    # 3 emitted artifact names.
    # G-77 guard: same file also carries Keycloak/OIDC SSO sidecar markers
    # (Growth-77 M3 Slice e) — 3 render_sso_* helpers + Keycloak image +
    # SOP §10 + 3 SSO artifact names + OIDC env contract.
    (scripts_dir / "emit_ops_pack.py").write_text(
        '"""Growth-71 + Growth-76 + Growth-77 + Growth-80 ops pack emitter stub."""\n'
        "def render_dockerfile(info):\n"
        '    return "FROM maven:3.9-eclipse-temurin-17 AS builder\\n"\n'
        "def render_compose(info, slug):\n"
        '    return "services:\\n  app:\\n"\n'
        "def render_env_example(info, slug):\n"
        '    return "APP_PORT=8080\\n"\n'
        "def render_sop(info, slug):\n"
        '    return "# 배포 SOP\\n"\n'
        "def render_vault_hcl(info, slug):\n"
        '    return \'method "approle" {}\'\n'
        "def render_vault_env_tmpl(info, slug):\n    return ''\n"
        "def render_vault_compose(info, slug):\n"
        '    return "# docker-compose.vault.yml\\n# vault-agent.hcl\\n# env.tmpl\\n"\n'
        "_VAULT_SOP_SECTION = '## 9. Vault Agent sidecar'\n"
        "def render_sso_compose(info, slug):\n"
        '    return "image: quay.io/keycloak/keycloak:24.0\\n"\n'
        "def render_sso_realm(info, slug, *, clients=None, ldap=None):\n    return '{}'\n"
        "def render_sso_env_example(info, slug):\n"
        '    return "OIDC_ISSUER_URI=http://keycloak:8080/realms/x\\n"\n'
        "_SSO_SOP_SECTION = '## 10. Keycloak/OIDC SSO sidecar'\n"
        "# docker-compose.sso.yml keycloak-realm.json Growth-77\n"
        "# Growth-80 marker: multi-client + LDAP federation\n"
        "_SSO_LDAP_COMPONENT_TPL = 'org.keycloak.storage.UserStorageProvider'\n"
        "def _render_client_json(client):\n    return '{}'\n"
        "sso_ldap = False  # emit() parameter placeholder\n",
        encoding="utf-8",
    )
    # G-72 guard: scripts/workflow/status_board.py exposes compute() +
    # render_status_section() + STATUS_BOARD_CSS + extract_trap_guards_count
    # (Growth-72 M2 Exec Status Board).
    (scripts / "status_board.py").write_text(
        '"""Growth-72 status board stub."""\n'
        "STATUS_BOARD_CSS = '.status-board{}'\n"
        "def compute(*a, **k):\n    return object()\n"
        "def render_status_section(board):\n    return ''\n"
        "def extract_trap_guards_count(text):\n    return 0\n",
        encoding="utf-8",
    )
    # G-75 guard: web/routes/ops.py exposes /{run_id}/ops.zip route + reads
    # shell/ops/ via zip_emitter (Growth-75 M3 Slice c). web/app.py includes
    # ops_router.
    (web_routes / "ops.py").write_text(
        '"""Growth-75 ops download route stub."""\n'
        'from web.adapters import zip_emitter\n'
        '@router.get("/{run_id}/ops.zip")\n'
        'def domain_ops_download(run_id):\n'
        '    ops_dir = out_dir / "shell" / "ops"\n'
        '    return zip_emitter.emit(ops_dir)\n',
        encoding="utf-8",
    )
    # G-79 guard: web/routes/target.py exposes /target/upload + adapter delegates
    # to scripts/extract_target_profile (Growth-79 M5 Slice C-c). web/app.py
    # includes target_router. Adapter MUST NOT re-implement parse_pom/parse_gradle.
    (web_routes / "target.py").write_text(
        '"""Growth-79 target upload route stub."""\n'
        '# Growth-82\n'
        'import difflib\n'
        'from web.adapters import target_extractor\n'
        '@router.get("/upload")\n'
        'def target_upload_get():\n'
        '    return target_extractor.extract_from_zip(b"")\n'
        '# X-Requested-With check for XHR mode\n',
        encoding="utf-8",
    )
    (web_adapters / "target_extractor.py").write_text(
        '"""Growth-79 target extractor adapter stub."""\n'
        'import extract_target_profile\n'
        'def extract_from_zip(payload):\n'
        '    profile = extract_target_profile.build_profile(None)\n'
        '    return extract_target_profile.dump_profile(profile)\n',
        encoding="utf-8",
    )
    (creater_root / "web" / "app.py").write_text(
        "from web.routes.ops import router as ops_router\n"
        "from web.routes.target import router as target_router\n"
        "application.include_router(ops_router)\n"
        "application.include_router(target_router)\n",
        encoding="utf-8",
    )
    # G-82 guard: target_upload.js + target_upload_partial.html stubs
    js_dir = creater_root / "web" / "static" / "js"
    js_dir.mkdir(parents=True, exist_ok=True)
    (js_dir / "target_upload.js").write_text(
        "// Growth-82: XHR upload with progress indicator\n"
        "var xhr = new XMLHttpRequest();\n",
        encoding="utf-8",
    )
    templates_dir = creater_root / "web" / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    existing_upload = templates_dir / "target_upload.html"
    if not existing_upload.exists():
        existing_upload.write_text(
            "<!-- target_upload.html stub -->\n"
            "<!-- target_upload.js -->\n"
            "<!-- upload-progress -->\n",
            encoding="utf-8",
        )
    else:
        # Append markers if not present
        content = existing_upload.read_text(encoding="utf-8")
        if "target_upload.js" not in content:
            content += "\n<!-- target_upload.js -->\n"
        if "upload-progress" not in content:
            content += "\n<!-- upload-progress -->\n"
        existing_upload.write_text(content, encoding="utf-8")
    (templates_dir / "target_upload_partial.html").write_text(
        "{# Growth-82 partial #}\n"
        '<section class="extraction-result">stub</section>\n',
        encoding="utf-8",
    )
    return workspace, creater_root


def test_check_layer_repos_all_pass(tmp_path):
    workspace, _ = _make_workspace(tmp_path)
    results = diagnose.check_layer_repos(workspace)
    assert all(c.status == "PASS" for c in results)
    assert {c.name for c in results} == {
        f"layer/{axis}" for axis in diagnose.LAYER_REPOS
    }


def test_check_layer_repos_fail_when_missing(tmp_path):
    workspace = tmp_path / "empty"
    workspace.mkdir()
    results = diagnose.check_layer_repos(workspace)
    assert all(c.status == "FAIL" for c in results)
    # every failing check carries a recovery hint
    assert all(c.hint for c in results)


def test_check_preset_catalog_pass(tmp_path):
    workspace, _ = _make_workspace(tmp_path)
    c = diagnose.check_preset_catalog(workspace)
    assert c.status == "PASS"
    assert "14 domains" in c.detail


def test_check_preset_catalog_fail_when_index_missing(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    c = diagnose.check_preset_catalog(workspace)
    assert c.status == "FAIL"
    assert c.hint


def test_check_preset_catalog_warn_when_too_few(tmp_path):
    workspace, _ = _make_workspace(tmp_path)
    idx = (
        workspace
        / "andrej-karpathy-rdb-skill"
        / ".claude"
        / "skills"
        / "karpathy-rdb"
        / "presets"
        / "INDEX.md"
    )
    idx.write_text("# Catalog\n\n## one\n\n## 매칭\n", encoding="utf-8")
    c = diagnose.check_preset_catalog(workspace)
    assert c.status == "WARN"


def test_check_learn_log_pass(tmp_path):
    _, creater_root = _make_workspace(tmp_path)
    c = diagnose.check_learn_log(creater_root)
    assert c.status == "PASS"


def test_check_learn_log_warn_when_no_section_zero(tmp_path):
    creater_root = tmp_path / "creater"
    creater_root.mkdir()
    (creater_root / "learn-log.md").write_text("# log\n\n## 1. other\n", encoding="utf-8")
    c = diagnose.check_learn_log(creater_root)
    assert c.status == "WARN"


def test_check_learn_log_fail_when_missing(tmp_path):
    creater_root = tmp_path / "creater"
    creater_root.mkdir()
    c = diagnose.check_learn_log(creater_root)
    assert c.status == "FAIL"


def test_check_runners_pass_when_clean(tmp_path):
    workspace, _ = _make_workspace(tmp_path)
    results = diagnose.check_runners(workspace)
    assert all(c.status == "PASS" for c in results)


def test_check_runners_warn_when_stale_overlay(tmp_path):
    workspace, _ = _make_workspace(tmp_path)
    overlay = (
        workspace
        / "nexacroN-fullstack"
        / "samples"
        / "runners"
        / "boot-jdk17-jakarta"
        / "src"
        / "main"
        / "java"
        / "com"
        / "example"
    )
    overlay.mkdir(parents=True)
    results = diagnose.check_runners(workspace)
    stale = next(c for c in results if c.name == "runner/boot-jdk17-jakarta")
    assert stale.status == "WARN"
    assert "cleanup_runner" in stale.hint


def test_check_runners_fail_when_root_missing(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    results = diagnose.check_runners(workspace)
    assert len(results) == 1
    assert results[0].status == "FAIL"


def test_check_cross_layer_coherence_pass(tmp_path):
    workspace, creater_root = _make_workspace(tmp_path)
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "PASS"
    assert (
        "21 trap guards intact (G-47/48/50a/50b/58/61/62/63/69/70/71/72/74/75/76/77/78/79/80/81/82)"
        in c.detail
    )


def test_check_cross_layer_coherence_fail_g47_uia_namespace_lost(tmp_path):
    workspace, creater_root = _make_workspace(tmp_path)
    ctrl = (
        workspace
        / "andrej-karpathy-rdb-mybatis"
        / ".claude"
        / "skills"
        / "karpathy-rdb-mybatis"
        / "templates"
        / "controller"
        / "controller.java.j2"
    )
    ctrl.write_text(
        "import com.nexacro.uiadapter.jakarta.core.NexacroException;\n",
        encoding="utf-8",
    )
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-47" in c.detail


def test_check_cross_layer_coherence_fail_g50a_runner_yml_missing_ctxpath(tmp_path):
    workspace, creater_root = _make_workspace(tmp_path)
    yml = (
        workspace
        / "nexacroN-fullstack"
        / "samples"
        / "runners"
        / "boot-jdk17-jakarta"
        / "src"
        / "main"
        / "resources"
        / "application.yml"
    )
    yml.write_text("server:\n  port: 8080\n", encoding="utf-8")
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-50a" in c.detail and "boot-jdk17-jakarta" in c.detail


def test_check_cross_layer_coherence_fail_g50b_lane_runner_map_lost_prefix(tmp_path):
    workspace, creater_root = _make_workspace(tmp_path)
    (creater_root / "scripts" / "workflow" / "lane_runner_map.py").write_text(
        'def lane_probe_url(...): return f"http://localhost:{port}/api/{entity}"\n',
        encoding="utf-8",
    )
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-50b" in c.detail


def test_check_cross_layer_coherence_fail_g48_full_test_lost_wiring(tmp_path):
    workspace, creater_root = _make_workspace(tmp_path)
    (creater_root / "scripts" / "workflow" / "full_test.py").write_text(
        "url = lane_probe_url(lane, port, entity)\n",
        encoding="utf-8",
    )
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-48" in c.detail


def test_check_cross_layer_coherence_fail_g58_vanilla_skip_lost(tmp_path):
    # Growth-59: G-58 regression guard — scaffold_orchestrator.py must keep
    # vanilla Stage 4 auto-skip gate, else /scaffold --lane vanilla breaks again
    # on Stage 4 N002 unsupported version: 2.
    workspace, creater_root = _make_workspace(tmp_path)
    (creater_root / "scripts" / "scaffold_orchestrator.py").write_text(
        "def _run_stage4(args, stage_paths, report):\n"
        "    subprocess.run(['python', 'form_gen.py'])\n",
        encoding="utf-8",
    )
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-58" in c.detail


def test_check_cross_layer_coherence_fail_g58_missing_orchestrator(tmp_path):
    workspace, creater_root = _make_workspace(tmp_path)
    (creater_root / "scripts" / "scaffold_orchestrator.py").unlink()
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-58 guard" in c.detail


def test_check_cross_layer_coherence_fail_g61_web_index_slug_regression(tmp_path):
    # Growth-62: G-61 regression guard — web_index._default_source_resolver must
    # pass domain_slug=None (not entry.domain) else Controller/Service preview
    # silently falls back to placeholder on Korean catalog dirs (T-Web-CatalogSlugMismatch).
    workspace, creater_root = _make_workspace(tmp_path)
    (creater_root / "scripts" / "workflow" / "web_index.py").write_text(
        "def _default_source_resolver(entry):\n"
        "    plan = discover_scaffold(scaffold_root, domain_slug=entry.domain)\n",
        encoding="utf-8",
    )
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-61" in c.detail


def test_check_cross_layer_coherence_fail_g61_missing_web_index(tmp_path):
    workspace, creater_root = _make_workspace(tmp_path)
    (creater_root / "scripts" / "workflow" / "web_index.py").unlink()
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-61 guard" in c.detail


def test_check_cross_layer_coherence_fail_g62_scaffold_cli_lost_wiring(tmp_path):
    # Growth-63: G-62 regression guard — scaffold_cli.py must keep customer
    # profile loader + --customer-profile flag + version:1 enforcement +
    # ScaffoldArgs forwarding, else the 6th axis (customer) silently regresses.
    workspace, creater_root = _make_workspace(tmp_path)
    (creater_root / "scripts" / "scaffold_cli.py").write_text(
        "def main():\n    pass\n",
        encoding="utf-8",
    )
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-62" in c.detail


def test_check_cross_layer_coherence_fail_g62_missing_scaffold_cli(tmp_path):
    workspace, creater_root = _make_workspace(tmp_path)
    (creater_root / "scripts" / "scaffold_cli.py").unlink()
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-62 guard" in c.detail


def test_check_cross_layer_coherence_fail_g63_version_check_lost(tmp_path):
    # Growth-65: G-63 regression guard — scaffold_cli.py must keep the
    # `version != 1` condition in load_customer_profile; removing it causes
    # future-schema profiles (version: 2) to be silently accepted.
    workspace, creater_root = _make_workspace(tmp_path)
    (creater_root / "scripts" / "scaffold_cli.py").write_text(
        "def load_customer_profile(slug, *, profiles_root=None):\n"
        "    if version < 0: raise ValueError('expected 1')\n"
        'parser.add_argument("--customer-profile")\n'
        "args = ScaffoldArgs(customer_profile=profile)\n",
        encoding="utf-8",
    )
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-63" in c.detail


def test_check_cross_layer_coherence_fail_g63_missing_scaffold_cli(tmp_path):
    workspace, creater_root = _make_workspace(tmp_path)
    (creater_root / "scripts" / "scaffold_cli.py").unlink()
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-63 guard" in c.detail


def test_check_cross_layer_coherence_fail_g69_runner_lost_subprocess(tmp_path):
    # Growth-69: G-69 regression guard — web/adapters/scaffold_runner.py must
    # invoke scripts/scaffold_cli.py via subprocess. Re-implementing scaffold
    # logic in the web layer bypasses the 6-axis compounding.
    workspace, creater_root = _make_workspace(tmp_path)
    (creater_root / "web" / "adapters" / "scaffold_runner.py").write_text(
        "def run(request, *, timeout_sec=300):\n"
        "    return reimplemented_scaffold(request)\n",
        encoding="utf-8",
    )
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-69" in c.detail


def test_check_cross_layer_coherence_fail_g69_missing_runner(tmp_path):
    workspace, creater_root = _make_workspace(tmp_path)
    (creater_root / "web" / "adapters" / "scaffold_runner.py").unlink()
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-69 guard" in c.detail


def test_check_cross_layer_coherence_fail_g69_domain_route_lost_call(tmp_path):
    # Web 경로가 scaffold_runner.run 을 호출하지 않으면 adapter 우회 가능 — 트랩.
    workspace, creater_root = _make_workspace(tmp_path)
    (creater_root / "web" / "routes" / "domain.py").write_text(
        "def post():\n    return reimplemented_scaffold()\n",
        encoding="utf-8",
    )
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-69" in c.detail


def test_check_cross_layer_coherence_fail_g70_missing_extractor(tmp_path):
    # Growth-70: G-70 guard — scripts/extract_target_profile.py absent breaks
    # M5 input path (target_project → customer profile YAML).
    workspace, creater_root = _make_workspace(tmp_path)
    (creater_root / "scripts" / "extract_target_profile.py").unlink()
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-70 guard" in c.detail


def test_check_cross_layer_coherence_fail_g70_lost_version_stamp(tmp_path):
    # Extractor that no longer stamps `"version": 1` would emit profiles that
    # fail load_customer_profile's G-62/G-63 pin — silent corruption.
    workspace, creater_root = _make_workspace(tmp_path)
    (creater_root / "scripts" / "extract_target_profile.py").write_text(
        '"""Growth-70 extractor — broken."""\n'
        "def build_profile(project_dir, slug='x'):\n"
        '    return {"customer": {"slug": slug}}  # missing version stamp\n'
        "def dump_profile(profile):\n"
        '    return "# Auto-extracted Growth-70\\n"\n',
        encoding="utf-8",
    )
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-70" in c.detail


def test_check_cross_layer_coherence_fail_g70_lost_header(tmp_path):
    # Header that no longer references Growth-70 — provenance loss.
    workspace, creater_root = _make_workspace(tmp_path)
    (creater_root / "scripts" / "extract_target_profile.py").write_text(
        "def build_profile(project_dir, slug='x'):\n"
        '    return {"version": 1, "customer": {"slug": slug}}\n'
        "def dump_profile(profile):\n"
        '    return "# Auto-extracted profile\\n"  # Growth- marker dropped\n',
        encoding="utf-8",
    )
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-70" in c.detail


def test_check_cross_layer_coherence_fail_g71_missing_emitter(tmp_path):
    # Growth-71: G-71 guard — scripts/emit_ops_pack.py absent breaks the
    # M3 Ops Pack 1-hour deploy scenario for the IT-담당자 persona.
    workspace, creater_root = _make_workspace(tmp_path)
    (creater_root / "scripts" / "emit_ops_pack.py").unlink()
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-71 guard" in c.detail


def test_check_cross_layer_coherence_fail_g71_lost_multistage_builder(tmp_path):
    # Multi-stage Docker builder pattern dropped — single-stage Dockerfile
    # would require the IT persona to install Maven/JDK locally, breaking
    # the "no dev environment" M-Ops acceptance criterion.
    workspace, creater_root = _make_workspace(tmp_path)
    (creater_root / "scripts" / "emit_ops_pack.py").write_text(
        '"""Growth-71 ops pack emitter stub — broken."""\n'
        "def render_dockerfile(info):\n"
        '    return "FROM tomcat:10.1\\n"  # no builder stage\n'
        "def render_compose(info, slug):\n"
        '    return "services:\\n  app:\\n"\n'
        "def render_env_example(info, slug):\n"
        '    return "APP_PORT=8080\\n"\n'
        "def render_sop(info, slug):\n"
        '    return "# 배포 SOP\\n"\n',
        encoding="utf-8",
    )
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-71" in c.detail


def test_check_cross_layer_coherence_fail_g71_lost_render_function(tmp_path):
    # Dropping any of the 4 render_* functions means one ops artifact is
    # never emitted — the pack becomes incomplete.
    workspace, creater_root = _make_workspace(tmp_path)
    (creater_root / "scripts" / "emit_ops_pack.py").write_text(
        '"""Growth-71 ops pack emitter — render_sop dropped."""\n'
        "def render_dockerfile(info):\n"
        '    return "FROM maven:3.9-eclipse-temurin-17 AS builder\\n"\n'
        "def render_compose(info, slug):\n"
        '    return "services:\\n  app:\\n"\n'
        "def render_env_example(info, slug):\n"
        '    return "APP_PORT=8080\\n"\n',
        encoding="utf-8",
    )
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-71" in c.detail


def test_check_cross_layer_coherence_fail_g72_missing_status_board(tmp_path):
    # Growth-72: G-72 guard — scripts/workflow/status_board.py absent breaks
    # the M2 Exec Status Board (portal status section disappears).
    workspace, creater_root = _make_workspace(tmp_path)
    (creater_root / "scripts" / "workflow" / "status_board.py").unlink()
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-72 guard" in c.detail


def test_check_cross_layer_coherence_fail_g72_lost_render_function(tmp_path):
    # Dropping render_status_section means the portal HTML fragment is never
    # emitted — CEO 페르소나가 누적 자산을 볼 수 없게 된다.
    workspace, creater_root = _make_workspace(tmp_path)
    (creater_root / "scripts" / "workflow" / "status_board.py").write_text(
        '"""Growth-72 status board — render dropped."""\n'
        "STATUS_BOARD_CSS = ''\n"
        "def compute(*a, **k):\n    return object()\n"
        "def extract_trap_guards_count(text):\n    return 0\n",
        encoding="utf-8",
    )
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-72" in c.detail


def test_check_cross_layer_coherence_fail_g72_lost_growth_marker(tmp_path):
    # Dropping the Growth-72 provenance marker loses the audit trail back to
    # the milestone that introduced the contract.
    workspace, creater_root = _make_workspace(tmp_path)
    (creater_root / "scripts" / "workflow" / "status_board.py").write_text(
        '"""status board — provenance dropped."""\n'
        "STATUS_BOARD_CSS = ''\n"
        "def compute(*a, **k):\n    return object()\n"
        "def render_status_section(board):\n    return ''\n"
        "def extract_trap_guards_count(text):\n    return 0\n",
        encoding="utf-8",
    )
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-72" in c.detail


def test_check_cross_layer_coherence_fail_g74_missing_orchestrator(tmp_path):
    # Growth-74: G-74 guard — scaffold_orchestrator.py absent breaks ops_pack
    # auto-emit (M3 Slice b). Already triggers G-58, but G-74 must also fire.
    workspace, creater_root = _make_workspace(tmp_path)
    (creater_root / "scripts" / "scaffold_orchestrator.py").unlink()
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-74 guard" in c.detail


def test_check_cross_layer_coherence_fail_g74_lost_helper(tmp_path):
    # Dropping _run_emit_ops_pack helper means Stage 5 PASS no longer auto-emits
    # the ops pack — IT-담당자 페르소나는 다시 수동 emit_ops_pack 호출에 의존.
    workspace, creater_root = _make_workspace(tmp_path)
    (creater_root / "scripts" / "scaffold_orchestrator.py").write_text(
        'def _run_stage4(args, stage_paths, report):\n'
        '    if args.lane == "vanilla":\n'
        '        report.stages_run.append("stage4-skipped-vanilla")\n'
        '        return\n'
        '\n'
        '# Growth-74 marker present but helper deleted\n'
        'def run_scaffold(args):\n'
        '    pass\n',
        encoding="utf-8",
    )
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-74" in c.detail


def test_check_cross_layer_coherence_fail_g74_lost_skip_marker(tmp_path):
    # Dropping the `ops_pack-skipped-no-shell` marker means the orchestrator can
    # no longer signal forward-compatible skip — _write_report rendering breaks.
    workspace, creater_root = _make_workspace(tmp_path)
    (creater_root / "scripts" / "scaffold_orchestrator.py").write_text(
        'def _run_stage4(args, stage_paths, report):\n'
        '    if args.lane == "vanilla":\n'
        '        report.stages_run.append("stage4-skipped-vanilla")\n'
        '        return\n'
        '\n'
        '# Growth-74 (M3 Slice b) — helper kept, but markers stripped\n'
        'def _run_emit_ops_pack(args, report):\n'
        '    import emit_ops_pack\n'
        '    report.stages_run.append("ops_pack-failed")\n'
        '\n'
        'def run_scaffold(args):\n'
        '    _run_emit_ops_pack(args, report)\n',
        encoding="utf-8",
    )
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-74" in c.detail


def test_check_cross_layer_coherence_fail_g75_missing_route(tmp_path):
    # Growth-75: G-75 guard — web/routes/ops.py absent breaks the M3 Slice c
    # promise that IT-담당자 페르소나 can download just the ops pack zip.
    workspace, creater_root = _make_workspace(tmp_path)
    (creater_root / "web" / "routes" / "ops.py").unlink()
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-75 guard" in c.detail


def test_check_cross_layer_coherence_fail_g75_reinvokes_emit(tmp_path):
    # If web/routes/ops.py imports emit_ops_pack, it violates the Growth-74
    # single-source contract (orchestrator owns emit; route only reads).
    workspace, creater_root = _make_workspace(tmp_path)
    (creater_root / "web" / "routes" / "ops.py").write_text(
        '"""Growth-75 ops download route stub — bad: re-invokes emit."""\n'
        "from web.adapters import zip_emitter\n"
        "import emit_ops_pack\n"
        '@router.get("/{run_id}/ops.zip")\n'
        "def domain_ops_download(run_id):\n"
        '    emit_ops_pack.emit(out_dir)\n'
        '    return zip_emitter.emit(out_dir / "shell" / "ops")\n',
        encoding="utf-8",
    )
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-75 regression" in c.detail
    assert "re-invokes emit_ops_pack" in c.detail


def test_check_cross_layer_coherence_fail_g75_app_does_not_include_router(tmp_path):
    # web/app.py must include ops_router for the route to be active.
    workspace, creater_root = _make_workspace(tmp_path)
    (creater_root / "web" / "app.py").write_text(
        "# ops_router not included — regression\n",
        encoding="utf-8",
    )
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-75" in c.detail
    assert "ops_router" in c.detail


def test_check_cross_layer_coherence_fail_g76_missing_vault_helpers(tmp_path):
    # Growth-76: G-76 guard — emit_ops_pack.py without Vault Agent sidecar
    # contract markers breaks the M3 Slice d promise (IT-담당자 Vault 위임).
    workspace, creater_root = _make_workspace(tmp_path)
    (creater_root / "scripts" / "emit_ops_pack.py").write_text(
        '"""ops pack emitter without Growth-76 Vault contract."""\n'
        "def render_dockerfile(info):\n"
        '    return "FROM maven:3.9-eclipse-temurin-17 AS builder\\n"\n'
        "def render_compose(info, slug):\n    return ''\n"
        "def render_env_example(info, slug):\n    return ''\n"
        "def render_sop(info, slug):\n    return ''\n",
        encoding="utf-8",
    )
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-76 regression" in c.detail
    assert "render_vault_hcl" in c.detail


def test_check_cross_layer_coherence_fail_g76_missing_approle(tmp_path):
    # If render_vault_hcl drops the AppRole auth method, enterprise on-prem
    # deployments lose their Vault auth contract.
    workspace, creater_root = _make_workspace(tmp_path)
    (creater_root / "scripts" / "emit_ops_pack.py").write_text(
        '"""Growth-71 + Growth-76 stub — but missing AppRole."""\n'
        "def render_dockerfile(info):\n"
        '    return "FROM maven:3.9-eclipse-temurin-17 AS builder\\n"\n'
        "def render_compose(info, slug):\n    return ''\n"
        "def render_env_example(info, slug):\n    return ''\n"
        "def render_sop(info, slug):\n    return ''\n"
        "def render_vault_hcl(info, slug):\n    return ''  # no approle\n"
        "def render_vault_env_tmpl(info, slug):\n    return ''\n"
        "def render_vault_compose(info, slug):\n"
        '    return "# docker-compose.vault.yml\\n# vault-agent.hcl\\n# env.tmpl\\n"\n'
        "_VAULT_SOP_SECTION = '## 9. Vault Agent sidecar'\n",
        encoding="utf-8",
    )
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-76 regression" in c.detail
    assert "approle" in c.detail


def test_check_cross_layer_coherence_fail_g76_emit_file_missing(tmp_path):
    # scripts/emit_ops_pack.py file removed entirely — both G-71 and G-76
    # surface; we assert G-76 message presence.
    workspace, creater_root = _make_workspace(tmp_path)
    (creater_root / "scripts" / "emit_ops_pack.py").unlink()
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-76 guard" in c.detail


def test_check_cross_layer_coherence_fail_g77_missing_sso_helpers(tmp_path):
    # If render_sso_* helpers vanish, IT-담당자 loses the Keycloak sidecar
    # opt-in promised by M3 Slice e.
    workspace, creater_root = _make_workspace(tmp_path)
    (creater_root / "scripts" / "emit_ops_pack.py").write_text(
        '"""stub without sso helpers."""\n'
        "def render_dockerfile(info):\n"
        '    return "FROM maven:3.9-eclipse-temurin-17 AS builder\\n"\n'
        "def render_compose(info, slug):\n    return ''\n"
        "def render_env_example(info, slug):\n    return ''\n"
        "def render_sop(info, slug):\n    return ''\n"
        "def render_vault_hcl(info, slug):\n"
        '    return \'method "approle" {}\'\n'
        "def render_vault_env_tmpl(info, slug):\n    return ''\n"
        "def render_vault_compose(info, slug):\n"
        '    return "# docker-compose.vault.yml\\n# vault-agent.hcl\\n# env.tmpl\\n"\n'
        "_VAULT_SOP_SECTION = '## 9. Vault Agent sidecar'\n"
        "# Growth-76 Growth-77 markers present in comments only\n",
        encoding="utf-8",
    )
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-77 regression" in c.detail
    assert "render_sso_compose" in c.detail


def test_check_cross_layer_coherence_fail_g77_missing_keycloak_image(tmp_path):
    # If the Keycloak image marker disappears (e.g., switched to a private
    # registry without leaving the contract reference), G-77 must fire.
    workspace, creater_root = _make_workspace(tmp_path)
    (creater_root / "scripts" / "emit_ops_pack.py").write_text(
        '"""stub with sso helpers but no keycloak image marker."""\n'
        "def render_dockerfile(info):\n"
        '    return "FROM maven:3.9-eclipse-temurin-17 AS builder\\n"\n'
        "def render_compose(info, slug):\n    return ''\n"
        "def render_env_example(info, slug):\n    return ''\n"
        "def render_sop(info, slug):\n    return ''\n"
        "def render_vault_hcl(info, slug):\n"
        '    return \'method "approle" {}\'\n'
        "def render_vault_env_tmpl(info, slug):\n    return ''\n"
        "def render_vault_compose(info, slug):\n"
        '    return "# docker-compose.vault.yml\\n# vault-agent.hcl\\n# env.tmpl\\n"\n'
        "_VAULT_SOP_SECTION = '## 9. Vault Agent sidecar'\n"
        "def render_sso_compose(info, slug):\n    return ''  # no quay image\n"
        "def render_sso_realm(info, slug):\n    return '{}'\n"
        "def render_sso_env_example(info, slug):\n"
        '    return "OIDC_ISSUER_URI=x\\n"\n'
        "_SSO_SOP_SECTION = '## 10. Keycloak/OIDC SSO sidecar'\n"
        "# docker-compose.sso.yml keycloak-realm.json Growth-77\n",
        encoding="utf-8",
    )
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-77 regression" in c.detail
    assert "quay.io/keycloak/keycloak" in c.detail


def test_check_cross_layer_coherence_fail_g77_emit_artifact_name_missing(tmp_path):
    # If any of the 3 SSO artifact filenames is removed from the source
    # (e.g., docker-compose.sso.yml reference lost), G-77 must fire.
    workspace, creater_root = _make_workspace(tmp_path)
    (creater_root / "scripts" / "emit_ops_pack.py").write_text(
        '"""stub with sso helpers but missing one artifact name."""\n'
        "def render_dockerfile(info):\n"
        '    return "FROM maven:3.9-eclipse-temurin-17 AS builder\\n"\n'
        "def render_compose(info, slug):\n    return ''\n"
        "def render_env_example(info, slug):\n    return ''\n"
        "def render_sop(info, slug):\n    return ''\n"
        "def render_vault_hcl(info, slug):\n"
        '    return \'method "approle" {}\'\n'
        "def render_vault_env_tmpl(info, slug):\n    return ''\n"
        "def render_vault_compose(info, slug):\n"
        '    return "# docker-compose.vault.yml\\n# vault-agent.hcl\\n# env.tmpl\\n"\n'
        "_VAULT_SOP_SECTION = '## 9. Vault Agent sidecar'\n"
        "def render_sso_compose(info, slug):\n"
        '    return "image: quay.io/keycloak/keycloak:24.0\\n"\n'
        "def render_sso_realm(info, slug):\n    return '{}'\n"
        "def render_sso_env_example(info, slug):\n"
        '    return "OIDC_ISSUER_URI=x\\n"\n'
        "_SSO_SOP_SECTION = '## 10. Keycloak/OIDC SSO sidecar'\n"
        "# keycloak-realm.json marker present; sso compose filename absent.\n"
        "# Growth-77\n",
        encoding="utf-8",
    )
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-77 regression" in c.detail
    assert "docker-compose.sso.yml" in c.detail


def test_check_cross_layer_coherence_fail_g78_missing_parse_gradle(tmp_path):
    # If parse_gradle helper is stripped from extract_target_profile.py,
    # G-78 must fire — Gradle input front-end is gone.
    workspace, creater_root = _make_workspace(tmp_path)
    (creater_root / "scripts" / "extract_target_profile.py").write_text(
        '"""Growth-70 only — Growth-78 Gradle support removed."""\n'
        "def build_profile(project_dir, slug='x'):\n"
        '    return {"version": 1, "customer": {"slug": slug}}\n'
        "def dump_profile(profile):\n"
        '    return "# Auto-extracted Growth-70\\n"\n',
        encoding="utf-8",
    )
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-78 regression" in c.detail
    assert "parse_gradle" in c.detail


def test_check_cross_layer_coherence_fail_g78_missing_kts_marker(tmp_path):
    # If the Kotlin DSL filename marker disappears (e.g., someone drops
    # .kts support and only handles Groovy), G-78 must fire.
    workspace, creater_root = _make_workspace(tmp_path)
    (creater_root / "scripts" / "extract_target_profile.py").write_text(
        '"""Growth-70 + Growth-78 partial — KTS marker stripped."""\n'
        "import re\n"
        "_GRADLE_GROUP_RE = re.compile(r'group')\n"
        "_GRADLE_ROOT_NAME_RE = re.compile(r'rootProject.name')\n"
        "def _gradle_lane(raw): return 'jakarta'\n"
        "def _find_gradle_build(d):\n"
        "    # only supports Groovy DSL; KTS dropped\n"
        "    return None\n"
        "def parse_gradle(p):\n"
        "    return {'group_id': None}\n"
        "def build_profile(project_dir, slug='x'):\n"
        '    return {"version": 1, "customer": {"slug": slug}}\n'
        "def dump_profile(profile):\n"
        '    return "# Auto-extracted Growth-70\\n"\n',
        encoding="utf-8",
    )
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-78 regression" in c.detail
    assert "build.gradle.kts" in c.detail


def test_check_cross_layer_coherence_fail_g79_adapter_reimplements_parser(tmp_path):
    # If target_extractor.py defines its own parse_pom/parse_gradle (instead of
    # delegating to scripts/extract_target_profile.py), G-79 must fire — the
    # single-source contract for the web upload path is broken.
    workspace, creater_root = _make_workspace(tmp_path)
    (creater_root / "web" / "adapters" / "target_extractor.py").write_text(
        '"""Growth-79 stub — but reimplements parser locally."""\n'
        "import extract_target_profile\n"
        "def parse_pom(path): return {}\n"
        "def extract_from_zip(payload):\n"
        '    return extract_target_profile.dump_profile({})\n',
        encoding="utf-8",
    )
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-79 regression" in c.detail
    assert "re-implements" in c.detail


def test_check_cross_layer_coherence_fail_g79_app_missing_target_router(tmp_path):
    # If web/app.py forgets to include target_router, G-79 must fire — the
    # /target/upload route is unreachable and M5 Slice C-c web path is dead.
    workspace, creater_root = _make_workspace(tmp_path)
    (creater_root / "web" / "app.py").write_text(
        "from web.routes.ops import router as ops_router\n"
        "application.include_router(ops_router)\n",
        encoding="utf-8",
    )
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-79 regression" in c.detail
    assert "target_router" in c.detail


def test_check_cross_layer_coherence_fail_g80_missing_ldap_marker(tmp_path):
    # G-80 guard: if _SSO_LDAP_COMPONENT_TPL or other G-80 markers vanish,
    # LDAP federation contract is broken and G-80 regression must fire.
    workspace, creater_root = _make_workspace(tmp_path)
    (creater_root / "scripts" / "emit_ops_pack.py").write_text(
        '"""stub missing G-80 LDAP markers."""\n'
        "def render_dockerfile(info):\n"
        '    return "FROM maven:3.9-eclipse-temurin-17 AS builder\\n"\n'
        "def render_compose(info, slug):\n    return ''\n"
        "def render_env_example(info, slug):\n    return ''\n"
        "def render_sop(info, slug):\n    return ''\n"
        "def render_vault_hcl(info, slug):\n"
        '    return \'method "approle" {}\'\n'
        "def render_vault_env_tmpl(info, slug):\n    return ''\n"
        "def render_vault_compose(info, slug):\n"
        '    return "# docker-compose.vault.yml\\n# vault-agent.hcl\\n# env.tmpl\\n"\n'
        "_VAULT_SOP_SECTION = '## 9. Vault Agent sidecar'\n"
        "def render_sso_compose(info, slug):\n"
        '    return "image: quay.io/keycloak/keycloak:24.0\\n"\n'
        "def render_sso_realm(info, slug, *, clients=None, ldap=None):\n    return '{}'\n"
        "def render_sso_env_example(info, slug):\n"
        '    return "OIDC_ISSUER_URI=http://keycloak:8080/realms/x\\n"\n'
        "_SSO_SOP_SECTION = '## 10. Keycloak/OIDC SSO sidecar'\n"
        "# docker-compose.sso.yml keycloak-realm.json Growth-77\n"
        "# G-80 markers intentionally omitted to trigger regression\n",
        encoding="utf-8",
    )
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-80 regression" in c.detail


def test_check_cross_layer_coherence_pass_g80(tmp_path):
    # G-80 guard: real source has all markers -> PASS (uses default _make_workspace stub)
    workspace, creater_root = _make_workspace(tmp_path)
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "PASS"
    assert "21 trap guards intact" in c.detail
    assert c.detail.endswith("/82)")


def test_check_cross_layer_coherence_pass_g81(tmp_path):
    # G-81 guard: workspace with all G-81 markers present → PASS
    workspace, creater_root = _make_workspace(tmp_path)
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "PASS"
    assert "21 trap guards intact" in c.detail
    assert c.detail.endswith("/82)")


def test_check_cross_layer_coherence_fail_g81_extract(tmp_path):
    # G-81 guard: include-parser marker absent → G-81 regression fires
    workspace, creater_root = _make_workspace(tmp_path)
    scripts_dir = creater_root / "scripts"
    # Overwrite stub with all G-70/G-78 markers but without the include-parser helper to trigger G-81
    (scripts_dir / "extract_target_profile.py").write_text(
        '"""Growth-70 + Growth-78 extractor stub — multi-module helpers absent."""\n'
        "import re\n"
        "_GRADLE_GROUP_RE = re.compile(r'group')\n"
        "_GRADLE_ROOT_NAME_RE = re.compile(r'rootProject.name')\n"
        "def _gradle_lane(raw): return 'jakarta'\n"
        "def _find_gradle_build(d):\n"
        "    # supports build.gradle.kts and build.gradle\n"
        "    return None\n"
        "def parse_gradle(p):\n"
        "    return {'group_id': None}\n"
        "def build_profile(project_dir, slug='x'):\n"
        '    return {"version": 1, "customer": {"slug": slug}}\n'
        "def dump_profile(profile):\n"
        '    return "# Auto-extracted Growth-70\\n"\n'
        "# Growth-78 markers\n"
        "# rootProject.name build.gradle.kts build.gradle Growth-78\n"
        "# Growth-81 multi-module support\n"
        "_GRADLE_INCLUDE_RE = re.compile(r'include')\n"
        "# stub omits the include-parser and module-extractor helpers\n"
        "def _extract_modules(d): return []\n",
        encoding="utf-8",
    )
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-81 regression" in c.detail


def test_check_cross_layer_coherence_pass_g82(tmp_path):
    # G-82 guard: all G-82 markers present → PASS
    workspace, creater_root = _make_workspace(tmp_path)
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "PASS"
    assert "21 trap guards intact" in c.detail
    assert c.detail.endswith("/82)")


def test_check_cross_layer_coherence_fail_g82_missing_js(tmp_path):
    # G-82 guard: target_upload.js missing → G-82 FAIL
    workspace, creater_root = _make_workspace(tmp_path)
    js = creater_root / "web" / "static" / "js" / "target_upload.js"
    js.unlink()
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-82" in c.detail


def test_check_cross_layer_coherence_fail_g82_missing_partial(tmp_path):
    # G-82 guard: target_upload_partial.html missing → G-82 FAIL
    workspace, creater_root = _make_workspace(tmp_path)
    partial = creater_root / "web" / "templates" / "target_upload_partial.html"
    partial.unlink()
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-82" in c.detail


def test_check_cross_layer_coherence_fail_g82_missing_marker(tmp_path):
    # G-82 guard: Growth-82 marker absent from target.py → FAIL
    workspace, creater_root = _make_workspace(tmp_path)
    route = creater_root / "web" / "routes" / "target.py"
    content = route.read_text(encoding="utf-8").replace("Growth-82", "Growth-XX")
    route.write_text(content, encoding="utf-8")
    c = diagnose.check_cross_layer_coherence(
        workspace=workspace, creater_root=creater_root
    )
    assert c.status == "FAIL"
    assert "G-82" in c.detail


def test_format_table_summary_lines():
    checks = [
        Check("a", "PASS", "ok"),
        Check("b", "WARN", "soft", hint="run x"),
        Check("c", "FAIL", "hard", hint="run y"),
    ]
    out = diagnose.format_table(checks)
    assert "OK" in out and "!" in out and "X" in out
    assert "run x" in out and "run y" in out
    assert "1 FAIL" in out


def test_format_table_all_pass():
    checks = [Check("a", "PASS"), Check("b", "PASS")]
    out = diagnose.format_table(checks)
    assert "All 2 checks PASS" in out


def test_format_table_empty():
    assert diagnose.format_table([]) == "(no checks ran)"


def test_main_exit_code_zero_when_no_fail(tmp_path, monkeypatch, capsys):
    workspace, creater_root = _make_workspace(tmp_path)
    monkeypatch.setattr(diagnose, "WORKSPACE", workspace)
    monkeypatch.setattr(diagnose, "CREATER_ROOT", creater_root)
    # Stub JDK to PASS to keep test deterministic across CI machines.
    monkeypatch.setattr(
        diagnose, "check_jdk", lambda: Check("jdk", "PASS", "stubbed")
    )
    rc = diagnose.main([])
    assert rc == 0


def test_main_exit_code_one_when_any_fail(tmp_path, monkeypatch, capsys):
    workspace = tmp_path / "empty"
    workspace.mkdir()
    creater_root = tmp_path / "creater"
    creater_root.mkdir()
    monkeypatch.setattr(diagnose, "WORKSPACE", workspace)
    monkeypatch.setattr(diagnose, "CREATER_ROOT", creater_root)
    monkeypatch.setattr(
        diagnose, "check_jdk", lambda: Check("jdk", "PASS", "stubbed")
    )
    rc = diagnose.main([])
    assert rc == 1


def test_main_json_output_shape(tmp_path, monkeypatch, capsys):
    workspace, creater_root = _make_workspace(tmp_path)
    monkeypatch.setattr(diagnose, "WORKSPACE", workspace)
    monkeypatch.setattr(diagnose, "CREATER_ROOT", creater_root)
    monkeypatch.setattr(
        diagnose, "check_jdk", lambda: Check("jdk", "PASS", "stubbed")
    )
    rc = diagnose.main(["--json"])
    captured = capsys.readouterr()
    assert rc == 0
    data = json.loads(captured.out)
    assert isinstance(data, list)
    assert all({"name", "status", "detail", "hint"} <= set(d) for d in data)
    assert any(d["name"] == "preset-catalog" for d in data)
