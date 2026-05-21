import pytest
from scripts.workflow import growth_start

def test_start_appends_row_and_returns_number(tmp_learn_log):
    n = growth_start.start("vanilla lane 라이브 검증", today="2026-05-21")
    assert n == 33
    body = tmp_learn_log.read_text(encoding="utf-8")
    assert "| Growth-33 | 2026-05-21 | vanilla lane 라이브 검증 (in_progress) |" in body

def test_start_empty_name_raises():
    with pytest.raises(ValueError, match="name is required"):
        growth_start.start("")

def test_start_whitespace_name_raises():
    with pytest.raises(ValueError, match="name is required"):
        growth_start.start("   ")
