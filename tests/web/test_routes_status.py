"""
tests/web/test_routes_status.py — Growth-84 Exec 라이브 대시보드 라우트 커버리지.

GET /status        → 200 HTML 대시보드
GET /status.json   → 200 JSON (domain_count / growth_count / green_rate)
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# GET /status
# ---------------------------------------------------------------------------

def test_status_dashboard_200(client: TestClient) -> None:
    """GET /status → 200, HTML 에 대시보드 제목 포함."""
    response = client.get("/status")
    assert response.status_code == 200
    body = response.text
    assert "누적 자산" in body or "대시보드" in body


def test_status_dashboard_shows_metrics(client: TestClient) -> None:
    """응답 본문에 도메인 수, 풀테스트 그린율(%), Growth 카운트 타일 포함."""
    response = client.get("/status")
    assert response.status_code == 200
    body = response.text
    # 타일 레이블 확인
    assert "도메인" in body
    assert "%" in body  # 그린율 퍼센트 표시
    assert "Growth" in body


# ---------------------------------------------------------------------------
# GET /status.json
# ---------------------------------------------------------------------------

def test_status_json_shape(client: TestClient) -> None:
    """GET /status.json → 200, 필수 키 및 green_rate 구조 확인."""
    response = client.get("/status.json")
    assert response.status_code == 200
    data = response.json()
    assert "domain_count" in data
    assert "growth_count" in data
    assert "green_rate" in data
    gr = data["green_rate"]
    assert "percent" in gr
    assert "verified" in gr
    assert "total" in gr


def test_status_json_green_rate_matches(client: TestClient) -> None:
    """green_rate.percent 가 verification 데이터로부터 올바르게 파생되는지 확인."""
    from scripts.workflow import status_board

    response = client.get("/status.json")
    assert response.status_code == 200
    data = response.json()

    board = status_board.compute()
    total = len(board.verification)
    verified = sum(1 for v in board.verification if v.status == "verified")
    expected_percent = round(verified / total * 100) if total else 0

    assert data["green_rate"]["percent"] == expected_percent
    assert data["green_rate"]["total"] == total
    assert data["green_rate"]["verified"] == verified


# ---------------------------------------------------------------------------
# 오류 폴백: compute() 예외 시 500 아닌 200 + error 메시지
# ---------------------------------------------------------------------------

def test_status_dashboard_handles_compute_error(client: TestClient, monkeypatch) -> None:
    """status_board.compute 가 예외를 던져도 /status 는 200 + error 폴백을 반환한다."""
    import web.routes.status as status_module
    import scripts.workflow.status_board as sb_module

    monkeypatch.setattr(sb_module, "compute", lambda **_kw: (_ for _ in ()).throw(RuntimeError("test-error")))

    response = client.get("/status")
    assert response.status_code == 200
    assert "자산 데이터를 집계하지 못했습니다" in response.text
