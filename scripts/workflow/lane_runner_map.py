"""Lane → default runner mapping. Single source of truth (mirrors CLAUDE.md §3.12)."""

LANE_RUNNER_MAP = {
    "jakarta": "boot-jdk17-jakarta",
    "javax": "boot-jdk8-javax",
    "nexacro": "boot-jdk17-jakarta",
    "vanilla": "boot-jdk8-javax",
}

_LABEL_SUFFIX = {
    "vanilla": " → javax-host 검증",
}

def resolve_runner(lane: str) -> str:
    if lane not in LANE_RUNNER_MAP:
        raise ValueError(f"unknown lane: {lane}. valid: {sorted(LANE_RUNNER_MAP)}")
    return LANE_RUNNER_MAP[lane]

def lane_label_suffix(lane: str) -> str:
    return _LABEL_SUFFIX.get(lane, "")
