import pytest
from scripts.workflow import learn_log

def test_latest_growth_num_finds_max(tmp_learn_log):
    assert learn_log.latest_growth_num() == 32

def test_append_row_inserts_next_number(tmp_learn_log):
    n = learn_log.append_row("test growth", today="2026-05-21")
    assert n == 33
    body = tmp_learn_log.read_text(encoding="utf-8")
    assert "| Growth-33 | 2026-05-21 | test growth (in_progress) |" in body

def test_append_row_preserves_following_sections(tmp_learn_log):
    learn_log.append_row("foo", today="2026-05-21")
    body = tmp_learn_log.read_text(encoding="utf-8")
    assert "## 7. Other section" in body

def test_update_label_replaces_in_progress(tmp_learn_log):
    learn_log.append_row("foo", today="2026-05-21")
    learn_log.update_label(33, "라이브 WAS 부분검증")
    body = tmp_learn_log.read_text(encoding="utf-8")
    assert "(라이브 WAS 부분검증)" in body
    assert "(in_progress)" not in body

def test_missing_section_raises(tmp_path, monkeypatch):
    bad = tmp_path / "bad.md"
    bad.write_text("no growth section\n", encoding="utf-8")
    monkeypatch.setattr(learn_log, "LEARN_LOG", bad)
    with pytest.raises(ValueError, match="§6"):
        learn_log.latest_growth_num()
