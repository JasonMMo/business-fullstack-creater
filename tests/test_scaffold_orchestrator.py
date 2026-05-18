# tests/test_scaffold_orchestrator.py
import pathlib
import pytest
from scaffold_orchestrator import ScaffoldArgs, run_scaffold, StageFailure


def _make_fake_stage(tmp_path, name, scripts):
    """scripts: dict[name -> python source]"""
    repo = tmp_path / f"andrej-karpathy-rdb-{name}"
    (repo / "scripts").mkdir(parents=True)
    for fname, src in scripts.items():
        (repo / "scripts" / fname).write_text(src, encoding="utf-8")
    return repo


def test_stage1_preset_writes_blueprint(tmp_path):
    # fake stage1: rdb_index.py compile <wiki> writes _blueprint.yaml
    s1_src = (
        "import sys, pathlib\n"
        "args = sys.argv[1:]\n"
        "if args[0] == 'init':\n"
        "    out = pathlib.Path(args[1]); out.mkdir(parents=True, exist_ok=True)\n"
        "    (out / '_schema.md').write_text('---\\ntype: schema\\n---\\n')\n"
        "elif args[0] == 'compile':\n"
        "    out = pathlib.Path(args[1])\n"
        "    (out / '_blueprint.yaml').write_text('version: 1\\nentities: []\\n')\n"
        "    (out / 'compile-report.md').write_text('OK\\n')\n"
    )
    s1 = _make_fake_stage(tmp_path, "skill", {"rdb_index.py": s1_src})
    for n in ("ddl", "mybatis", "nexacro"):
        _make_fake_stage(tmp_path, n, {})  # empty
    creator = tmp_path / "creater"; creator.mkdir()

    out = tmp_path / "out"
    args = ScaffoldArgs(
        domain="주문관리", domain_slug="order", wiki_mode="preset",
        preset="주문관리", wiki_path=None, lane="nexacro",
        default_pattern="D2", package="com.example.order", out_dir=out,
        creator_root=creator, stop_after_stage=1,
    )
    report = run_scaffold(args)
    assert (out / "1-wiki" / "_blueprint.yaml").exists()
    assert report.stages_run == ["stage1"]


def test_missing_wiki_mode_raises(tmp_path):
    creator = tmp_path / "creater"; creator.mkdir()
    args = ScaffoldArgs(
        domain="x", domain_slug="x", wiki_mode=None,
        preset=None, wiki_path=None, lane="nexacro",
        default_pattern="D2", package="com.example.x", out_dir=tmp_path/"out",
        creator_root=creator, stop_after_stage=1,
    )
    with pytest.raises(ValueError) as exc:
        run_scaffold(args)
    assert "wiki_mode" in str(exc.value)
