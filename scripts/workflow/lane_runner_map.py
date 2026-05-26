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
#   jakarta/javax/vanilla → GET `/uiadapter/api/<entity>` returning List<Map>
#
# Growth-50 (T-Probe-CtxPath-Missing): all nexacroN-fullstack runners (boot/mvc,
# javax/jakarta, plain/egov4/egov5) set `server.servlet.context-path: /uiadapter`
# in application.yml. The nexacro envelope path always carried the prefix; the
# REST path didn't, so vanilla/jakarta/javax probes hit a 404 against
# `/api/<entity>` instead of `/uiadapter/api/<entity>`. Prefix added.
#
# Growth-48 (T-Probe-LaneRunner-Mismatch): the wire-protocol is decided by the
# *scaffold* lane (what Stage 3 codegen emitted), not by the *runner* lane
# (which Spring Boot version hosts the WAR). The two coincide in the common
# case but diverge for e.g. nexacro scaffold deployed on a boot-jdk8-javax
# runner via --uia-namespace=spring. All probe/CRUD dispatchers therefore
# accept an optional `scaffold_lane` override; when supplied it wins over the
# `lane` arg (which keeps meaning "runner lane" everywhere else in this map).
_LANE_PROBE_KIND = {
    "nexacro": "nexacro",
    "jakarta": "rest",
    "javax": "rest",
    "vanilla": "rest",
}

def _effective_lane(lane: str, scaffold_lane: str | None) -> str:
    return scaffold_lane if scaffold_lane is not None else lane

def lane_probe_kind(lane: str, scaffold_lane: str | None = None) -> str:
    eff = _effective_lane(lane, scaffold_lane)
    if eff not in _LANE_PROBE_KIND:
        raise ValueError(f"unknown lane: {eff}. valid: {sorted(_LANE_PROBE_KIND)}")
    return _LANE_PROBE_KIND[eff]

def lane_probe_url(lane: str, port: int, entity: str, scaffold_lane: str | None = None) -> str:
    kind = lane_probe_kind(lane, scaffold_lane)
    if kind == "nexacro":
        return f"http://localhost:{port}/uiadapter/{entity}/select_datalist_map.do"
    return f"http://localhost:{port}/uiadapter/api/{entity}"


# Growth-40/42: CRUD round-trip dispatch.
#   REST   — POST `/api/<entity>` with _rowType (jakarta/javax/vanilla)
#   ENVELOPE — POST `/uiadapter/<entity>/save_datalist_map.do` with <Row Type=...> (nexacro)
_LANE_CRUD_KIND = {
    "nexacro": "envelope",
    "jakarta": "rest",
    "javax": "rest",
    "vanilla": "rest",
}

def lane_crud_kind(lane: str, scaffold_lane: str | None = None) -> str:
    """Return the CRUD wire-protocol the lane speaks: 'rest', 'envelope', or 'none'.

    Growth-48: `scaffold_lane` overrides `lane` when supplied — wire-protocol
    is a property of the scaffold (what Stage 3 emitted), not the runner.
    """
    eff = _effective_lane(lane, scaffold_lane)
    if eff not in _LANE_CRUD_KIND:
        raise ValueError(f"unknown lane: {eff}. valid: {sorted(_LANE_CRUD_KIND)}")
    return _LANE_CRUD_KIND[eff]

def lane_supports_crud(lane: str, scaffold_lane: str | None = None) -> bool:
    """Backward-compat shim — True iff the lane has any CRUD dispatch (rest OR envelope)."""
    return lane_crud_kind(lane, scaffold_lane) in ("rest", "envelope")
