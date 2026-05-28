"""
tests/web/test_routes_target.py — Growth-79 (M5 Slice C-c) /target/upload route.

검증 항목:
  1. GET /target/upload  → 200, 폼 렌더링
  2. POST 빈 zip          → 422, 안내 메시지
  3. POST 잘못된 zip      → 422
  4. POST Maven pom.xml   → 200, 미리보기에 version: 1 + customer.slug 포함
  5. POST Gradle KTS      → 200, Gradle 입력 인식
  6. POST 누락 (pom/gradle 없음) → 422
  7. POST download=1      → application/x-yaml + Content-Disposition attachment
  8. POST slug override   → 미리보기 YAML 에 override 슬러그 적용
"""
from __future__ import annotations

import io
import zipfile

import pytest


_POM_MIN = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.acme</groupId>
  <artifactId>acme-shell</artifactId>
  <version>1.0.0</version>
  <name>ACME Shell</name>
  <dependencies>
    <dependency>
      <groupId>jakarta.servlet</groupId>
      <artifactId>jakarta.servlet-api</artifactId>
      <version>6.0.0</version>
    </dependency>
  </dependencies>
</project>
"""

_APPLICATION_YML = """spring:
  datasource:
    url: jdbc:postgresql://db.acme.internal:5432/acme_prod
    username: ${ACME_DB_USER}
    password: ${ACME_DB_PASS}
mybatis:
  type-aliases-package: com.acme.customer.domain
"""

_BUILD_GRADLE_KTS = """
plugins {
    id("org.springframework.boot") version "3.2.0"
}
group = "com.foo"
version = "1.2.3"
dependencies {
    implementation("org.springframework.boot:spring-boot-starter-web:3.2.0")
    implementation("jakarta.servlet:jakarta.servlet-api:6.0.0")
}
"""

_SETTINGS_GRADLE_KTS = 'rootProject.name = "foo-shell"\n'


def _build_zip(files: dict, *, top: str = "project") -> bytes:
    """Return zip bytes with *files* under top-level dir *top* (or no top if empty)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel, content in files.items():
            arcname = f"{top}/{rel}" if top else rel
            zf.writestr(arcname, content)
    return buf.getvalue()


# ---------------------------------------------------------------------------

def test_target_upload_get_returns_form(client):
    resp = client.get("/target/upload")
    assert resp.status_code == 200
    assert "기존 프로젝트" in resp.text
    assert 'name="project_zip"' in resp.text


def test_target_upload_post_rejects_empty_upload(client):
    resp = client.post(
        "/target/upload",
        files={"project_zip": ("empty.zip", b"", "application/zip")},
    )
    assert resp.status_code == 422
    assert "비어" in resp.text


def test_target_upload_post_rejects_malformed_zip(client):
    resp = client.post(
        "/target/upload",
        files={"project_zip": ("bad.zip", b"not a zip", "application/zip")},
    )
    assert resp.status_code == 422
    assert "zip" in resp.text


def test_target_upload_post_maven_returns_preview(client):
    payload = _build_zip({
        "pom.xml": _POM_MIN,
        "src/main/resources/application.yml": _APPLICATION_YML,
    })
    resp = client.post(
        "/target/upload",
        files={"project_zip": ("acme.zip", payload, "application/zip")},
    )
    assert resp.status_code == 200
    assert "version: 1" in resp.text
    assert "acme" in resp.text
    assert "추출 결과" in resp.text


def test_target_upload_post_gradle_kts_recognized(client):
    payload = _build_zip({
        "build.gradle.kts": _BUILD_GRADLE_KTS,
        "settings.gradle.kts": _SETTINGS_GRADLE_KTS,
    })
    resp = client.post(
        "/target/upload",
        files={"project_zip": ("foo.zip", payload, "application/zip")},
    )
    assert resp.status_code == 200
    assert "version: 1" in resp.text
    # Slug derived from rootProject.name "foo-shell" with -shell stripped → "foo"
    assert "slug: foo" in resp.text


def test_target_upload_post_missing_build_file_returns_422(client):
    payload = _build_zip({"README.md": "no build file here"})
    resp = client.post(
        "/target/upload",
        files={"project_zip": ("bare.zip", payload, "application/zip")},
    )
    assert resp.status_code == 422
    assert "pom.xml" in resp.text or "build.gradle" in resp.text


def test_target_upload_post_download_streams_yaml(client):
    payload = _build_zip({
        "pom.xml": _POM_MIN,
        "src/main/resources/application.yml": _APPLICATION_YML,
    })
    resp = client.post(
        "/target/upload",
        files={"project_zip": ("acme.zip", payload, "application/zip")},
        data={"download": "1"},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/x-yaml")
    assert 'filename="acme.yaml"' in resp.headers["content-disposition"]
    assert resp.text.startswith("#") and "version: 1" in resp.text


def test_target_upload_post_slug_override_applied(client):
    payload = _build_zip({
        "pom.xml": _POM_MIN,
        "src/main/resources/application.yml": _APPLICATION_YML,
    })
    resp = client.post(
        "/target/upload",
        files={"project_zip": ("acme.zip", payload, "application/zip")},
        data={"slug": "acme-prod"},
    )
    assert resp.status_code == 200
    assert "slug: acme-prod" in resp.text


def test_target_upload_post_rejects_invalid_slug(client):
    payload = _build_zip({"pom.xml": _POM_MIN})
    resp = client.post(
        "/target/upload",
        files={"project_zip": ("acme.zip", payload, "application/zip")},
        data={"slug": "Bad Slug!"},
    )
    assert resp.status_code == 422
    assert "슬러그" in resp.text
