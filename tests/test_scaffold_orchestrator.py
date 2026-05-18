# tests/test_scaffold_orchestrator.py
import pathlib
import pytest
from scaffold_orchestrator import ScaffoldArgs, run_scaffold, StageFailure

# Minimal .seed.md that _init_wiki_from_preset can parse to produce entities
_MINIMAL_SEED = """\
---
preset: {preset}
version: 1
---

# {preset}

```yaml
type: entity
name: item
display: 항목
domain: [{preset}]
table: item
status: draft
columns:
  - {{ name: id, type: bigserial, pk: true, nullable: false }}
```
"""


def _make_fake_stage(tmp_path, name, scripts, presets=None):
    """Create a fake sibling stage repo.

    scripts : dict[filename -> python source] placed in <repo>/scripts/
    presets : dict[preset_name -> seed_md_text] placed in
              <repo>/.claude/skills/karpathy-rdb/presets/<name>.seed.md
              (only relevant for stage1 / 'skill')
    """
    repo = tmp_path / f"andrej-karpathy-rdb-{name}"
    (repo / "scripts").mkdir(parents=True)
    for fname, src in scripts.items():
        (repo / "scripts" / fname).write_text(src, encoding="utf-8")
    if presets:
        presets_dir = repo / ".claude" / "skills" / "karpathy-rdb" / "presets"
        presets_dir.mkdir(parents=True)
        for preset_name, seed_text in presets.items():
            (presets_dir / f"{preset_name}.seed.md").write_text(
                seed_text, encoding="utf-8"
            )
    return repo


def _make_fake_s1(tmp_path, preset_name):
    """Create a fake stage1 repo with a minimal preset and a compile-only rdb_index."""
    s1_src = (
        "import sys, pathlib\n"
        "wiki_dir = pathlib.Path(sys.argv[2])\n"
        "(wiki_dir / '_blueprint.yaml').write_text('version: 1\\nentities: []\\n')\n"
        "(wiki_dir / 'compile-report.md').write_text('OK\\n')\n"
    )
    seed = _MINIMAL_SEED.format(preset=preset_name)
    return _make_fake_stage(
        tmp_path, "skill",
        {"rdb_index.py": s1_src},
        presets={preset_name: seed},
    )


def test_stage1_preset_writes_blueprint(tmp_path):
    # _init_wiki_from_preset writes entity files; fake rdb_index compile writes _blueprint.yaml
    _make_fake_s1(tmp_path, "주문관리")
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
    _make_fake_s1(tmp_path, "t")
    # fake stage2: positional blueprint + --out OUT
    s2_src = (
        "import sys, pathlib\n"
        "bp = pathlib.Path(sys.argv[1])\n"
        "out = pathlib.Path(sys.argv[sys.argv.index('--out')+1])\n"
        "out.mkdir(parents=True, exist_ok=True)\n"
        "(out / 'ddl_create.sql').write_text('-- generated from ' + bp.name)\n"
    )
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
    _make_fake_s1(tmp_path, "t")
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


def _make_fake_chain_stages(tmp_path):
    """Create fake stages 1-3 needed as prerequisites for stage4 tests."""
    _make_fake_s1(tmp_path, "t")
    s2_src = (
        "import sys, pathlib\n"
        "out = pathlib.Path(sys.argv[sys.argv.index('--out')+1])\n"
        "out.mkdir(parents=True, exist_ok=True)\n"
        "(out / 'ddl_create.sql').write_text('-- ddl')\n"
    )
    s3_src = (
        "import sys, pathlib\n"
        "argv = sys.argv[1:]\n"
        "out = pathlib.Path(argv[argv.index('--out')+1])\n"
        "out.mkdir(parents=True, exist_ok=True)\n"
        "(out / 'mapper.xml').write_text('<mapper/>')\n"
    )
    _make_fake_stage(tmp_path, "ddl",     {"ddl_compile.py": s2_src})
    _make_fake_stage(tmp_path, "mybatis", {"compile.py": s3_src})


def test_stage4_uses_endpoints_when_present(tmp_path):
    """When endpoints.json exists stage3 emits it; stage4 must receive --endpoints <path>."""
    _make_fake_chain_stages(tmp_path)

    # fake stage3 that ALSO writes endpoints.json
    s3_with_ep_src = (
        "import sys, pathlib\n"
        "argv = sys.argv[1:]\n"
        "out = pathlib.Path(argv[argv.index('--out')+1])\n"
        "out.mkdir(parents=True, exist_ok=True)\n"
        "(out / 'mapper.xml').write_text('<mapper/>')\n"
        "(out / 'endpoints.json').write_text('{\"endpoints\":[]}')\n"
    )
    # Overwrite the mybatis fake with one that emits endpoints.json
    (tmp_path / "andrej-karpathy-rdb-mybatis" / "scripts" / "compile.py").write_text(
        s3_with_ep_src, encoding="utf-8"
    )

    # fake stage4: write argv.txt so we can assert on it
    s4_src = (
        "import sys, pathlib\n"
        "argv = sys.argv[1:]\n"
        "out = pathlib.Path(argv[argv.index('--out')+1])\n"
        "out.mkdir(parents=True, exist_ok=True)\n"
        "(out / 'argv.txt').write_text(' '.join(argv))\n"
    )
    _make_fake_stage(tmp_path, "nexacro", {"form_gen.py": s4_src})

    creator = tmp_path / "creater"; creator.mkdir()
    out = tmp_path / "out"
    args = ScaffoldArgs(
        domain="t", domain_slug="t", wiki_mode="preset", preset="t",
        wiki_path=None, lane="nexacro", default_pattern="D2",
        package="com.example.t", out_dir=out, creator_root=creator,
        stop_after_stage=4,
    )
    report = run_scaffold(args)
    assert report.stages_run == ["stage1", "stage2", "stage3", "stage4"]
    argv_txt = (out / "4-nexacro" / "argv.txt").read_text(encoding="utf-8")
    assert "--endpoints" in argv_txt
    assert "--infer-endpoints" not in argv_txt
    assert "endpoints.json" in argv_txt


def test_stage4_uses_infer_when_no_endpoints(tmp_path):
    """When endpoints.json absent, stage4 must receive --infer-endpoints."""
    _make_fake_chain_stages(tmp_path)

    # fake stage4: write argv.txt
    s4_src = (
        "import sys, pathlib\n"
        "argv = sys.argv[1:]\n"
        "out = pathlib.Path(argv[argv.index('--out')+1])\n"
        "out.mkdir(parents=True, exist_ok=True)\n"
        "(out / 'argv.txt').write_text(' '.join(argv))\n"
    )
    _make_fake_stage(tmp_path, "nexacro", {"form_gen.py": s4_src})

    creator = tmp_path / "creater"; creator.mkdir()
    out = tmp_path / "out"
    args = ScaffoldArgs(
        domain="t", domain_slug="t", wiki_mode="preset", preset="t",
        wiki_path=None, lane="nexacro", default_pattern="D2",
        package="com.example.t", out_dir=out, creator_root=creator,
        stop_after_stage=4,
    )
    report = run_scaffold(args)
    assert report.stages_run == ["stage1", "stage2", "stage3", "stage4"]
    argv_txt = (out / "4-nexacro" / "argv.txt").read_text(encoding="utf-8")
    assert "--infer-endpoints" in argv_txt
    assert "--endpoints" not in argv_txt


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


def test_scaffold_report_written_on_success(tmp_path):
    """Full 4-stage run writes scaffold-report.md with all stage markers."""
    _make_fake_chain_stages(tmp_path)

    s4_src = (
        "import sys, pathlib\n"
        "argv = sys.argv[1:]\n"
        "out = pathlib.Path(argv[argv.index('--out')+1])\n"
        "out.mkdir(parents=True, exist_ok=True)\n"
        "(out / 'argv.txt').write_text(' '.join(argv))\n"
    )
    _make_fake_stage(tmp_path, "nexacro", {"form_gen.py": s4_src})

    creator = tmp_path / "creater"; creator.mkdir()
    out = tmp_path / "out"
    args = ScaffoldArgs(
        domain="주문관리", domain_slug="order", wiki_mode="preset",
        preset="t",  # matches the preset in _make_fake_chain_stages/_make_fake_s1
        wiki_path=None, lane="nexacro",
        default_pattern="D2", package="com.example.order", out_dir=out,
        creator_root=creator, stop_after_stage=4,
    )
    run_scaffold(args)

    report_path = out / "scaffold-report.md"
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "주문관리" in content
    assert "stage1" in content
    assert "stage4" in content
    assert "D2" in content
    assert "FAILED" not in content
    assert "다음 단계" in content


def test_scaffold_report_written_on_failure(tmp_path):
    """When stage2 exits non-zero, scaffold-report.md is written with FAILED marker and StageFailure is raised."""
    _make_fake_s1(tmp_path, "주문관리")
    # stage2: exits 1 (simulates failure)
    s2_fail_src = (
        "import sys\n"
        "sys.stderr.write('ddl_compile error: invalid blueprint\\n')\n"
        "sys.exit(1)\n"
    )
    _make_fake_stage(tmp_path, "ddl",   {"ddl_compile.py": s2_fail_src})
    for n in ("mybatis", "nexacro"):
        _make_fake_stage(tmp_path, n, {})
    creator = tmp_path / "creater"; creator.mkdir()
    out = tmp_path / "out"
    args = ScaffoldArgs(
        domain="주문관리", domain_slug="order", wiki_mode="preset",
        preset="주문관리", wiki_path=None, lane="nexacro",
        default_pattern="D2", package="com.example.order", out_dir=out,
        creator_root=creator, stop_after_stage=4,
    )

    with pytest.raises(StageFailure):
        run_scaffold(args)

    report_path = out / "scaffold-report.md"
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "FAILED: stage2" in content
    assert "stage1" in content
    assert "stage3" not in content
    assert "stage4" not in content
