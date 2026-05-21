import pytest
from scripts.workflow.lane_runner_map import resolve_runner, lane_label_suffix

@pytest.mark.parametrize("lane,runner", [
    ("jakarta", "boot-jdk17-jakarta"),
    ("javax", "boot-jdk8-javax"),
    ("nexacro", "boot-jdk17-jakarta"),
    ("vanilla", "boot-jdk8-javax"),
])
def test_resolve_runner_known(lane, runner):
    assert resolve_runner(lane) == runner

def test_resolve_runner_unknown_raises():
    with pytest.raises(ValueError, match="unknown lane"):
        resolve_runner("kotlin")

def test_vanilla_label_suffix_marks_host_validation():
    assert lane_label_suffix("vanilla") == " → javax-host 검증"
    assert lane_label_suffix("jakarta") == ""
