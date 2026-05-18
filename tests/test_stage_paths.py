import pathlib
import pytest
from stage_paths import resolve_stage_paths, StagePathError, StagePaths


def test_resolve_from_sibling_convention(tmp_path):
    creator = tmp_path / "business-fullstack-creater"
    creator.mkdir()
    for n in ("skill", "ddl", "mybatis", "nexacro"):
        (tmp_path / f"andrej-karpathy-rdb-{n}").mkdir()
    sp = resolve_stage_paths(creator_root=creator)
    assert sp.stage1.name == "andrej-karpathy-rdb-skill"
    assert sp.stage4.name == "andrej-karpathy-rdb-nexacro"


def test_explicit_config_wins(tmp_path):
    creator = tmp_path / "creater"
    creator.mkdir()
    cfg_dir = creator / "config"
    cfg_dir.mkdir()
    s1 = tmp_path / "custom-skill"
    s1.mkdir()
    for n in ("ddl", "mybatis", "nexacro"):
        (tmp_path / f"andrej-karpathy-rdb-{n}").mkdir()
    (cfg_dir / "stage-paths.yaml").write_text(
        f"stage1: {s1.as_posix()}\n", encoding="utf-8"
    )
    sp = resolve_stage_paths(creator_root=creator)
    assert sp.stage1 == s1


def test_missing_stage_raises(tmp_path):
    creator = tmp_path / "creater"
    creator.mkdir()
    (tmp_path / "andrej-karpathy-rdb-skill").mkdir()
    with pytest.raises(StagePathError) as exc:
        resolve_stage_paths(creator_root=creator)
    assert "stage2" in str(exc.value) or "ddl" in str(exc.value)
