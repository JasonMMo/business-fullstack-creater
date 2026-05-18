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


def test_stage2_runs_after_stage1(tmp_path):
    # fake stage1: same shape as test_stage1_preset_writes_blueprint
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
    # fake stage2: positional blueprint + --out OUT
    s2_src = (
        "import sys, pathlib\n"
        "bp = pathlib.Path(sys.argv[1])\n"
        "out = pathlib.Path(sys.argv[sys.argv.index('--out')+1])\n"
        "out.mkdir(parents=True, exist_ok=True)\n"
        "(out / 'ddl_create.sql').write_text('-- generated from ' + bp.name)\n"
    )
    _make_fake_stage(tmp_path, "skill", {"rdb_index.py": s1_src})
    _make_fake_stage(tmp_path, "ddl",   {"ddl_compile.py": s2_src})
    for n in ("mybatis", "nexacro"):
        _make_fake_stage(tmp_path, n, {})
    creator = tmp_path / "creater"; creator.mkdir()
    out = tmp_path / "out"
    args = ScaffoldArgs(
        domain="t", domain_slug="t", wiki_mode="preset", preset="t",
        wiki_path=None, lane="nexacro", default_pattern="D2",
        package="com.example.t", out_dir=out, creator_root=creator,
        stop_after_stage=2,
    )
    report = run_scaffold(args)
    assert report.stages_run == ["stage1", "stage2"]
    assert (out / "2-ddl" / "ddl_create.sql").exists()


def test_stage3_runs_after_stage2(tmp_path):
    # fake stage1
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
    # fake stage2: positional blueprint + --out OUT
    s2_src = (
        "import sys, pathlib\n"
        "bp = pathlib.Path(sys.argv[1])\n"
        "out = pathlib.Path(sys.argv[sys.argv.index('--out')+1])\n"
        "out.mkdir(parents=True, exist_ok=True)\n"
        "(out / 'ddl_create.sql').write_text('-- generated from ' + bp.name)\n"
    )
    # fake stage3: compile subcommand, --blueprint, --ddl-dir, --out, --lane, --package
    s3_src = (
        "import sys, pathlib\n"
        "# argv[1] == 'compile' (subcommand)\n"
        "argv = sys.argv[1:]\n"
        "out = pathlib.Path(argv[argv.index('--out')+1])\n"
        "out.mkdir(parents=True, exist_ok=True)\n"
        "(out / 'mapper.xml').write_text('<mapper/>')\n"
    )
    _make_fake_stage(tmp_path, "skill",   {"rdb_index.py": s1_src})
    _make_fake_stage(tmp_path, "ddl",     {"ddl_compile.py": s2_src})
    _make_fake_stage(tmp_path, "mybatis", {"compile.py": s3_src})
    _make_fake_stage(tmp_path, "nexacro", {})
    creator = tmp_path / "creater"; creator.mkdir()
    out = tmp_path / "out"
    args = ScaffoldArgs(
        domain="t", domain_slug="t", wiki_mode="preset", preset="t",
        wiki_path=None, lane="vanilla", default_pattern="D2",
        package="com.example.t", out_dir=out, creator_root=creator,
        stop_after_stage=3,
    )
    report = run_scaffold(args)
    assert report.stages_run == ["stage1", "stage2", "stage3"]
    assert (out / "3-mybatis" / "mapper.xml").exists()


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
