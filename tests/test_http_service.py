from __future__ import annotations

import pytest


@pytest.fixture
def http_client(monkeypatch: pytest.MonkeyPatch):
    pytest.importorskip("fastapi")
    monkeypatch.setenv("PRISMGUARD_DEV_UNRESTRICTED", "1")
    from fastapi.testclient import TestClient
    from prismguard.http.service import create_app

    app = create_app()
    return TestClient(app)


def test_scan_output_allows_benign_text(http_client) -> None:
    resp = http_client.post(
        "/v1/scan-output",
        json={"text": "The NDA requires 30 days written notice for termination."},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == "allow"
    assert body["resolution_gate"] == "output_allow"
    assert body["matched_pattern"] is None
    assert "latency_ms" in body


def test_scan_output_blocks_exfil_url(http_client) -> None:
    resp = http_client.post(
        "/v1/scan-output",
        json={"text": "See details at https://attacker.example/leak?data=ALL"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == "block"
    assert body["resolution_gate"] == "output_pattern"
    assert body["matched_pattern"] == "suspicious_url"
    assert "latency_ms" in body
