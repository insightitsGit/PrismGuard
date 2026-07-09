"""Offline signed license validation — same file format as ChorusGraph."""

from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from prismguard.licensing.errors import LicenseError, LicenseExpiredError
from prismguard.licensing.keys import license_public_key_bytes

_ENTERPRISE_CONTACT = "https://github.com/insightitsGit/PrismGaurd/blob/master/docs/enterprise-product-model.md"
_CACHED: dict[str, Any] | None = None
_CACHED_PATH: str | None = None


def clear_license_cache() -> None:
    global _CACHED, _CACHED_PATH
    _CACHED = None
    _CACHED_PATH = None


def _canonical_payload_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def validate_offline_file(path: str | Path) -> dict[str, Any]:
    """Verify signed license JSON — zero network calls."""
    global _CACHED, _CACHED_PATH
    resolved = str(Path(path).resolve())
    if _CACHED is not None and _CACHED_PATH == resolved:
        return dict(_CACHED)

    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LicenseError(f"Could not read license file {path!r}: {exc}") from exc

    payload = raw.get("payload")
    signature_b64 = raw.get("signature")
    if not isinstance(payload, dict):
        raise LicenseError("License file must contain a 'payload' object.")
    if not isinstance(signature_b64, str):
        raise LicenseError("Signed license file must contain a 'signature' string.")

    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        signature = base64.b64decode(signature_b64)
        public_key = Ed25519PublicKey.from_public_bytes(license_public_key_bytes())
        public_key.verify(signature, _canonical_payload_bytes(payload))
    except ImportError as exc:
        raise LicenseError(
            "Signed license verification requires cryptography — pip install prismguard[enterprise]"
        ) from exc
    except Exception as exc:
        raise LicenseError("License signature verification failed — file may be tampered.") from exc

    expires_at = payload.get("expires_at")
    if expires_at:
        try:
            exp = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
            if datetime.now(timezone.utc) > exp:
                raise LicenseExpiredError(
                    f"License expired on {exp.date()}. Renew via enterprise contact: {_ENTERPRISE_CONTACT}"
                )
        except LicenseExpiredError:
            raise
        except Exception as exc:
            raise LicenseError(f"Invalid expires_at in license: {expires_at!r}") from exc

    _CACHED = dict(payload)
    _CACHED_PATH = resolved
    return dict(payload)


def load_license_payload() -> dict[str, Any] | None:
    path = os.environ.get("PRISMGUARD_LICENSE_FILE", "").strip()
    if not path:
        return None
    return validate_offline_file(path)
