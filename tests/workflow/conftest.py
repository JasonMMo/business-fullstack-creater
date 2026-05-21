import pytest
from pathlib import Path

SAMPLE_LOG = """\
# Learn Log

## 6. Growth 이력 (요약)

| Growth | 일자 | 살붙임 요약 |
|---|---|---|
| Growth-1 | 2026-04 | 고객관리 |
| Growth-32 | 2026-05-21 | javax lane 검증 |

## 7. Other section
"""

@pytest.fixture()
def tmp_learn_log(tmp_path, monkeypatch):
    log = tmp_path / "learn-log.md"
    log.write_text(SAMPLE_LOG, encoding="utf-8")
    monkeypatch.setattr("scripts.workflow.learn_log.LEARN_LOG", log)
    return log


@pytest.fixture()
def tmp_learn_log_crlf(tmp_path, monkeypatch):
    """Same content as SAMPLE_LOG but with CRLF line endings."""
    log = tmp_path / "learn-log-crlf.md"
    crlf_content = SAMPLE_LOG.replace("\n", "\r\n").encode("utf-8")
    log.write_bytes(crlf_content)
    monkeypatch.setattr("scripts.workflow.learn_log.LEARN_LOG", log)
    return log
