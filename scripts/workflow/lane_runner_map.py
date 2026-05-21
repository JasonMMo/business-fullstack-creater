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


# Growth-40/42: CRUD round-trip dispatch.
#   REST   — POST `/api/<entity>` with _rowType (jakarta/javax/vanilla)
#   ENVELOPE — POST `/uiadapter/<entity>/save_datalist_map.do` with <Row Type=...> (nexacro)
_LANE_CRUD_KIND = {
    "nexacro": "envelope",
    "jakarta": "rest",
    "javax": "rest",
    "vanilla": "rest",
}

def lane_crud_kind(lane: str) -> str:
    """Return the CRUD wire-protocol the lane speaks: 'rest', 'envelope', or 'none'."""
    if lane not in _LANE_CRUD_KIND:
        raise ValueError(f"unknown lane: {lane}. valid: {sorted(_LANE_CRUD_KIND)}")
    return _LANE_CRUD_KIND[lane]

def lane_supports_crud(lane: str) -> bool:
    """Backward-compat shim — True iff the lane has any CRUD dispatch (rest OR envelope)."""
    return lane_crud_kind(lane) in ("rest", "envelope")
