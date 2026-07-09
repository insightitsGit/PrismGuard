"""Sign test license files for CI — dev issuer key only (not for customer distribution)."""

from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

# Matches prismguard.licensing.keys embedded public key (CI/dev issuer only).
_TEST_PRIVATE_KEY_B64 = "p8tXdxA1tvhQ5G9sln948R8l7QMYv0GAoRpCYopk6Rs="


def _canonical_payload_bytes(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign_license_payload(payload: dict) -> dict:
    private_key = Ed25519PrivateKey.from_private_bytes(base64.b64decode(_TEST_PRIVATE_KEY_B64))
    signature = private_key.sign(_canonical_payload_bytes(payload))
    return {"payload": payload, "signature": base64.b64encode(signature).decode("ascii")}


def write_test_license(
    path: Path,
    *,
    features: list[str],
    tenant: str = "test-tenant",
    days_valid: int = 365,
) -> Path:
    expires = datetime.now(timezone.utc) + timedelta(days=days_valid)
    payload = {
        "tenant": tenant,
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": expires.isoformat(),
        "features": list(features),
    }
    path.write_text(json.dumps(sign_license_payload(payload), indent=2), encoding="utf-8")
    return path
