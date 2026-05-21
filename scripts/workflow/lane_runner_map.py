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


# Growth-36: probe dispatch. Stage 3 emits two controller shapes:
#   nexacro lane → POST `/uiadapter/<entity>/select_datalist_map.do` + XML envelope
#   jakarta/javax/vanilla → GET `/api/<entity>` returning List<Map>
_LANE_PROBE_KIND = {
    "nexacro": "nexacro",
    "jakarta": "rest",
    "javax": "rest",
    "vanilla": "rest",
}

def lane_probe_kind(lane: str) -> str:
    if lane not in _LANE_PROBE_KIND:
        raise ValueError(f"unknown lane: {lane}. valid: {sorted(_LANE_PROBE_KIND)}")
    return _LANE_PROBE_KIND[lane]

def lane_probe_url(lane: str, port: int, entity: str) -> str:
    kind = lane_probe_kind(lane)
    if kind == "nexacro":
        return f"http://localhost:{port}/uiadapter/{entity}/select_datalist_map.do"
    return f"http://localhost:{port}/api/{entity}"
