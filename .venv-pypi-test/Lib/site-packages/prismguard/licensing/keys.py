"""Embedded Ed25519 public key for offline license verification (shared CI/dev issuer with ChorusGraph)."""

from __future__ import annotations

import base64

# Development / CI issuer key — replace with production public key for customer licenses.
_LICENSE_PUBLIC_KEY_B64 = "EokYXbukexUFq7aBlXdiGMIXfAjaNnWg08uZcuaOT7Q="


def license_public_key_bytes() -> bytes:
    return base64.b64decode(_LICENSE_PUBLIC_KEY_B64)
