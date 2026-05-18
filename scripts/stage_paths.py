import pathlib
from dataclasses import dataclass
import yaml


class StagePathError(Exception):
    pass


@dataclass
class StagePaths:
    stage1: pathlib.Path
    stage2: pathlib.Path
    stage3: pathlib.Path
    stage4: pathlib.Path


_SIBLING_NAMES = {
    "stage1": "andrej-karpathy-rdb-skill",
    "stage2": "andrej-karpathy-rdb-ddl",
    "stage3": "andrej-karpathy-rdb-mybatis",
    "stage4": "andrej-karpathy-rdb-nexacro",
}


def resolve_stage_paths(creator_root):
    creator_root = pathlib.Path(creator_root).resolve()
    cfg_file = creator_root / "config" / "stage-paths.yaml"
    overrides = {}
    if cfg_file.exists():
        overrides = yaml.safe_load(cfg_file.read_text(encoding="utf-8")) or {}

    resolved = {}
    for key, sibling in _SIBLING_NAMES.items():
        if key in overrides:
            p = pathlib.Path(overrides[key]).expanduser().resolve()
        else:
            p = (creator_root.parent / sibling).resolve()
        if not p.exists():
            raise StagePathError(
                f"{key} repository not found at {p} "
                f"(override config/stage-paths.yaml or place repo at sibling path)"
            )
        resolved[key] = p
    return StagePaths(**resolved)
