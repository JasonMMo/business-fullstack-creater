import pytest
from scripts.workflow import full_test

def test_decide_label_all_pass():
    layers = {"L1": True, "L2": True, "L3": True, "L4_full": True}
    assert full_test.decide_label(layers) == "풀테스트 그린"

def test_decide_label_l4_partial():
    layers = {"L1": True, "L2": True, "L3": True, "L4_partial": True}
    assert full_test.decide_label(layers) == "라이브 WAS 부분검증"

def test_decide_label_l4_failed():
    layers = {"L1": True, "L2": True, "L3": True, "L4_full": False, "L4_partial": False}
    assert full_test.decide_label(layers) == "JDBC + 빌드까지만 검증"

def test_decide_label_l3_missing():
    layers = {"L1": True, "L2": True}
    assert full_test.decide_label(layers) == "JDBC 까지만 검증"

def test_decide_label_l1_fail_aborts():
    layers = {"L1": False}
    assert full_test.decide_label(layers) == "단위 테스트 실패 — 검증 중단"

def test_lane_default_runner_resolution():
    assert full_test.runner_for("jakarta") == "boot-jdk17-jakarta"
    assert full_test.runner_for("vanilla") == "boot-jdk8-javax"
