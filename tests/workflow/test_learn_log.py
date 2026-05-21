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


def test_append_row_preserves_crlf(tmp_learn_log_crlf):
    """CRITICAL 1: CRLF line endings must round-trip through append_row."""
    learn_log.append_row("crlf test", today="2026-05-21")
    raw = tmp_learn_log_crlf.read_bytes()
    assert b"\r\n" in raw, "CRLF endings were lost after append_row"
    # Verify no bare LF was introduced (every \n must be preceded by \r)
    lone_lf_count = raw.count(b"\n") - raw.count(b"\r\n")
    assert lone_lf_count == 0, f"{lone_lf_count} bare LF(s) introduced by append_row"


def test_update_label_raises_on_missing_growth_num(tmp_learn_log):
    """IMPORTANT 3: update_label must raise ValueError when growth_num not in §6."""
    with pytest.raises(ValueError, match="Growth-99"):
        learn_log.update_label(99, "풀테스트 그린")


def test_update_label_raises_on_already_labelled(tmp_learn_log):
    """IMPORTANT 3: update_label must raise ValueError when row already labelled."""
    learn_log.append_row("foo", today="2026-05-21")
    learn_log.update_label(33, "풀테스트 그린")
    # Second call on same row — already labelled, must raise
    with pytest.raises(ValueError, match="Growth-33"):
        learn_log.update_label(33, "다시 라벨")
