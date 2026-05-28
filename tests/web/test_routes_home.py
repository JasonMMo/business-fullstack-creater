"""
tests/web/test_routes_home.py — Home route coverage for M1 S1.1.
"""
from fastapi.testclient import TestClient


def test_home_route_returns_200(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200


def test_home_renders_project_name(client: TestClient) -> None:
    response = client.get("/")
    assert "고객사" in response.text or "생성기" in response.text


def test_home_has_cta_link(client: TestClient) -> None:
    response = client.get("/")
    assert "/domain/new" in response.text
