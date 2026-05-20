# tests/test_shell_mode_cli.py
"""CLI + orchestrator wiring for --shell-mode / --nexacrolib-from (Growth-16 P3)."""
import pathlib
import subprocess
import sys

import pytest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SCAFFOLD_CLI = REPO_ROOT / "scripts" / "scaffold_cli.py"
NEXACRO_SKILL = (
    REPO_ROOT.parent
    / "andrej-karpathy-rdb-nexacro"
    / ".claude" / "skills" / "karpathy-rdb-nexacro" / "patterns"
)


# ---------------------------------------------------------------------------
# CLI surface
# ---------------------------------------------------------------------------

class TestCliShellFlags:
    def _help(self) -> str:
        r = subprocess.run(
            [sys.executable, str(SCAFFOLD_CLI), "--help"],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, r.stderr
        return r.stdout

    def test_help_mentions_shell_mode(self):
        assert "--shell-mode" in self._help()

    def test_help_mentions_nexacrolib_from(self):
        assert "--nexacrolib-from" in self._help()

    def test_help_lists_shell_mode_choices(self):
        body = self._help()
        # argparse renders choices either as "{none,MDI,SDI}" or in the metavar
        assert "none" in body and "MDI" in body and "SDI" in body

    def test_invalid_shell_mode_rejected(self, tmp_path):
        r = subprocess.run(
            [
                sys.executable, str(SCAFFOLD_CLI),
                "--domain", "shipping",
                "--package", "com.example.shipping",
                "--out", str(tmp_path / "out"),
                "--wiki-mode", "preset", "--preset", "배송관리",
                "--shell-mode", "BOGUS",
            ],
            capture_output=True, text=True,
        )
        assert r.returncode != 0
        assert "BOGUS" in r.stderr or "invalid choice" in r.stderr.lower()


# ---------------------------------------------------------------------------
# ScaffoldArgs surface
# ---------------------------------------------------------------------------

class TestScaffoldArgsShellFields:
    def test_defaults(self):
        from scaffold_orchestrator import ScaffoldArgs
        a = ScaffoldArgs(
            domain="x", domain_slug="x", wiki_mode="preset",
            preset="p", wiki_path=None, lane="nexacro",
            default_pattern="D2", package="com.example.x",
            out_dir=pathlib.Path("/tmp/out"),
            creator_root=pathlib.Path("/tmp/c"),
        )
        assert a.shell_mode == "none"
        assert a.nexacrolib_from is None
        assert a.shell_app_id == "packageN"


# ---------------------------------------------------------------------------
# Orchestrator stage-5 branch — gated on sibling repo availability
# ---------------------------------------------------------------------------

pytestmark_real = pytest.mark.skipif(
    not NEXACRO_SKILL.exists(),
    reason="nexacro sibling repo not present",
)


@pytestmark_real
def test_stage5_shell_mode_renders_shell_into_target(tmp_path, monkeypatch):
    """When --shell-mode=MDI is set, _run_stage5 must dispatch the
    nexacro-shell adapter and produce nxui/packageN/ files in target_dir.

    We bypass real Stage 1–4 by stubbing the stage runners and only exercise
    stage5 with a minimal blueprint.
    """
    import scaffold_orchestrator as orch
    import yaml as _yaml

    # Prepare out_dir with a minimal 1-wiki/_blueprint.yaml so _run_stage5
    # can load entities without running Stage 1.
    out = tmp_path / "out"
    (out / "1-wiki").mkdir(parents=True)
    (out / "1-wiki" / "_blueprint.yaml").write_text(
        _yaml.safe_dump({
            "version": 1,
            "entities": [
                {"name": "delivery", "label_ko": "배송"},
                {"name": "courier",  "label_ko": "택배사"},
            ],
        }, allow_unicode=True),
        encoding="utf-8",
    )

    target = tmp_path / "newproj"
    target.mkdir()

    # Use real stage_paths via fake creator pointing at the actual workspace
    creator = REPO_ROOT  # business-fullstack-creater itself

    args = orch.ScaffoldArgs(
        domain="배송관리", domain_slug="shipping",
        wiki_mode="preset", preset="배송관리", wiki_path=None,
        lane="nexacro", default_pattern="D2",
        package="com.example.shipping", out_dir=out,
        creator_root=creator,
        stop_after_stage=5,
        target_project=target,
        overlay_force=False,
        ui="nexacro",
        shell_mode="MDI",
    )

    # Skip stages 1–4
    for fn in ("_run_stage1", "_run_stage2", "_run_stage3", "_run_stage4"):
        monkeypatch.setattr(orch, fn, lambda *a, **k: None)

    report = orch.run_scaffold(args)

    pkg = target / "nxui" / "packageN"
    assert (pkg / "frame" / "frameMain.xfdl").exists()
    assert (pkg / "frame" / "frameMDI.xfdl").exists()
    assert (pkg / "typedefinition.xml").exists()
    assert (pkg / "packageN.xadl").exists()
    # overlay_report should reflect a shell pass
    assert report.overlay_report is not None
    assert report.overlay_report.get("shell_variant") == "MDI"


@pytestmark_real
def test_stage5_nexacrolib_from_copies_tree(tmp_path, monkeypatch):
    """--nexacrolib-from <path> copies the given tree into target/nxui/nexacrolib/."""
    import scaffold_orchestrator as orch
    import yaml as _yaml

    out = tmp_path / "out"
    (out / "1-wiki").mkdir(parents=True)
    (out / "1-wiki" / "_blueprint.yaml").write_text(
        "version: 1\nentities: []\n", encoding="utf-8"
    )

    # Fake nexacrolib source
    lib = tmp_path / "fake-nxlib"
    (lib / "components").mkdir(parents=True)
    (lib / "components" / "Grid.xcdl").write_text("<Grid/>", encoding="utf-8")
    (lib / "manifest.xml").write_text("<manifest/>", encoding="utf-8")

    target = tmp_path / "proj"
    target.mkdir()

    creator = REPO_ROOT
    args = orch.ScaffoldArgs(
        domain="shipping", domain_slug="shipping",
        wiki_mode="preset", preset="배송관리", wiki_path=None,
        lane="nexacro", default_pattern="D2",
        package="com.example.shipping", out_dir=out,
        creator_root=creator,
        stop_after_stage=5,
        target_project=target,
        overlay_force=False,
        ui="nexacro",
        shell_mode="MDI",
        nexacrolib_from=lib,
    )

    for fn in ("_run_stage1", "_run_stage2", "_run_stage3", "_run_stage4"):
        monkeypatch.setattr(orch, fn, lambda *a, **k: None)

    orch.run_scaffold(args)

    copied = target / "nxui" / "nexacrolib"
    assert (copied / "components" / "Grid.xcdl").exists()
    assert (copied / "manifest.xml").exists()
