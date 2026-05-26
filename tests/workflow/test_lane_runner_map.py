import pytest
from scripts.workflow.lane_runner_map import (
    resolve_runner, lane_label_suffix, lane_probe_url, lane_probe_kind,
)

@pytest.mark.parametrize("lane,runner", [
    ("jakarta", "boot-jdk17-jakarta"),
    ("javax", "boot-jdk8-javax"),
    ("nexacro", "boot-jdk17-jakarta"),
    ("vanilla", "boot-jdk8-javax"),
])
def test_resolve_runner_known(lane, runner):
    assert resolve_runner(lane) == runner

def test_resolve_runner_unknown_raises():
    with pytest.raises(ValueError, match=r"unknown lane: kotlin"):
        resolve_runner("kotlin")

def test_vanilla_label_suffix_marks_host_validation():
    assert lane_label_suffix("vanilla") == " → javax-host 검증"
    assert lane_label_suffix("jakarta") == ""


# ---- Growth-36: lane-aware probe dispatch (nexacro envelope vs REST JSON) ----

@pytest.mark.parametrize("lane,kind", [
    ("nexacro", "nexacro"),
    ("jakarta", "rest"),
    ("javax", "rest"),
    ("vanilla", "rest"),
])
def test_lane_probe_kind(lane, kind):
    assert lane_probe_kind(lane) == kind


def test_lane_probe_url_nexacro_uses_uiadapter_envelope():
    assert lane_probe_url("nexacro", 8080, "account") == \
        "http://localhost:8080/uiadapter/account/select_datalist_map.do"


@pytest.mark.parametrize("lane", ["jakarta", "javax", "vanilla"])
def test_lane_probe_url_rest_uses_api_path(lane):
    # Growth-50 (T-Probe-CtxPath-Missing): runners set context-path=/uiadapter,
    # so REST routes resolve under /uiadapter/api/<entity>, not /api/<entity>.
    assert lane_probe_url(lane, 8080, "lead") == "http://localhost:8080/uiadapter/api/lead"


def test_lane_probe_url_unknown_lane_raises():
    with pytest.raises(ValueError, match="unknown lane"):
        lane_probe_url("kotlin", 8080, "x")


# ---- Growth-48: T-Probe-LaneRunner-Mismatch — scaffold_lane overrides runner lane ----

from scripts.workflow.lane_runner_map import lane_crud_kind, lane_supports_crud


def test_scaffold_lane_overrides_for_probe_kind():
    """nexacro scaffold deployed on javax runner — probe must follow scaffold."""
    assert lane_probe_kind("javax", scaffold_lane="nexacro") == "nexacro"
    assert lane_probe_kind("jakarta", scaffold_lane="nexacro") == "nexacro"


def test_scaffold_lane_overrides_for_probe_url():
    """probe URL is the envelope path when scaffold_lane=nexacro, regardless of runner."""
    assert lane_probe_url("javax", 8080, "customer", scaffold_lane="nexacro") == \
        "http://localhost:8080/uiadapter/customer/select_datalist_map.do"


def test_scaffold_lane_overrides_for_crud_kind():
    assert lane_crud_kind("javax", scaffold_lane="nexacro") == "envelope"
    assert lane_crud_kind("nexacro", scaffold_lane="jakarta") == "rest"


def test_scaffold_lane_none_preserves_legacy_behavior():
    """Omitting scaffold_lane (or passing None) is exactly the pre-Growth-48 API."""
    assert lane_probe_kind("javax", scaffold_lane=None) == "rest"
    assert lane_probe_kind("javax") == "rest"
    assert lane_probe_url("nexacro", 8080, "x", scaffold_lane=None) == \
        "http://localhost:8080/uiadapter/x/select_datalist_map.do"
    assert lane_crud_kind("javax") == "rest"
    assert lane_supports_crud("javax") is True


def test_scaffold_lane_unknown_value_raises():
    with pytest.raises(ValueError, match="unknown lane: kotlin"):
        lane_probe_kind("javax", scaffold_lane="kotlin")
    with pytest.raises(ValueError, match="unknown lane: kotlin"):
        lane_crud_kind("javax", scaffold_lane="kotlin")
