import pytest

from prismguard.licensing.features import (
    ENTERPRISE_HTTP,
    ENTERPRISE_PERSISTENCE,
    has_feature,
    require_feature,
)
from prismguard.licensing.validator import clear_license_cache
from tests.support.license_fixture import write_test_license


def test_oss_has_no_paid_features_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PRISMGUARD_LICENSE_FILE", raising=False)
    monkeypatch.delenv("PRISMGUARD_DEV_UNRESTRICTED", raising=False)
    clear_license_cache()
    assert not has_feature(ENTERPRISE_HTTP)


def test_dev_unrestricted_enables_features(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PRISMGUARD_DEV_UNRESTRICTED", "1")
    assert has_feature(ENTERPRISE_HTTP)
    require_feature(ENTERPRISE_HTTP)  # no raise


def test_signed_license_enables_features(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
) -> None:
    pytest.importorskip("cryptography")
    lic = tmp_path / "license.json"
    write_test_license(lic, features=[ENTERPRISE_HTTP, ENTERPRISE_PERSISTENCE])
    monkeypatch.delenv("PRISMGUARD_DEV_UNRESTRICTED", raising=False)
    monkeypatch.setenv("PRISMGUARD_LICENSE_FILE", str(lic))
    clear_license_cache()
    assert has_feature(ENTERPRISE_HTTP)
    assert has_feature(ENTERPRISE_PERSISTENCE)


def test_unsigned_license_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
) -> None:
    pytest.importorskip("cryptography")
    lic = tmp_path / "bad.json"
    lic.write_text('{"payload": {"features": ["enterprise_http"]}}', encoding="utf-8")
    monkeypatch.setenv("PRISMGUARD_LICENSE_FILE", str(lic))
    clear_license_cache()
    from prismguard.licensing.errors import LicenseError
    from prismguard.licensing.validator import validate_offline_file

    with pytest.raises(LicenseError):
        validate_offline_file(lic)


def test_pgvector_requires_license(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PRISMGUARD_LICENSE_FILE", raising=False)
    monkeypatch.delenv("PRISMGUARD_DEV_UNRESTRICTED", raising=False)
    clear_license_cache()
    from prismguard.licensing.errors import LicenseError
    from prismguard.storage import create_storage

    with pytest.raises(LicenseError):
        create_storage("pgvector", dsn="postgresql://localhost/test")


def test_memory_storage_no_license(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PRISMGUARD_LICENSE_FILE", raising=False)
    monkeypatch.delenv("PRISMGUARD_DEV_UNRESTRICTED", raising=False)
    clear_license_cache()
    from prismguard.storage import create_storage

    backend = create_storage("memory")
    assert backend is not None


def test_http_service_requires_license(monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("fastapi")
    monkeypatch.delenv("PRISMGUARD_LICENSE_FILE", raising=False)
    monkeypatch.delenv("PRISMGUARD_DEV_UNRESTRICTED", raising=False)
    clear_license_cache()
    from prismguard.licensing.errors import LicenseError
    from prismguard.http.service import create_app

    with pytest.raises(LicenseError):
        create_app()


def test_metrics_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("fastapi")
    monkeypatch.setenv("PRISMGUARD_DEV_UNRESTRICTED", "1")
    from fastapi.testclient import TestClient
    from prismguard.http.service import create_app
    from prismguard.observability.metrics import get_metrics

    get_metrics().check_total = 0
    app = create_app()
    client = TestClient(app)
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "prismguard_check_total" in resp.text
