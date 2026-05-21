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
    assert lane_probe_url(lane, 8080, "lead") == "http://localhost:8080/api/lead"


def test_lane_probe_url_unknown_lane_raises():
    with pytest.raises(ValueError, match="unknown lane"):
        lane_probe_url("kotlin", 8080, "x")
