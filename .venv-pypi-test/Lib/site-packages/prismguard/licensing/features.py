"""Feature flags for paid tiers — signed offline license or dev override."""

from __future__ import annotations

from prismguard.licensing.errors import LicenseError
from prismguard.licensing.validator import load_license_payload

ENTERPRISE_PERSISTENCE = "enterprise_persistence"  # pgvector, feedback sink
ENTERPRISE_HTTP = "enterprise_http"  # prismguard serve
ENTERPRISE_TENANT = "enterprise_tenant"  # tenant lexicon in production

_ENTERPRISE_CONTACT = "https://github.com/insightitsGit/PrismGaurd/blob/master/docs/enterprise-product-model.md"
_DEV_FEATURES = frozenset({ENTERPRISE_PERSISTENCE, ENTERPRISE_HTTP, ENTERPRISE_TENANT})


def _dev_unrestricted() -> bool:
    import os

    return os.environ.get("PRISMGUARD_DEV_UNRESTRICTED", "").strip() in ("1", "true", "yes")


def entitled_features() -> frozenset[str]:
    if _dev_unrestricted():
        return _DEV_FEATURES
    try:
        payload = load_license_payload()
    except LicenseError:
        raise
    if payload is None:
        return frozenset()
    features = payload.get("features") or []
    if not isinstance(features, list):
        raise LicenseError("License payload 'features' must be a list.")
    return frozenset(str(f) for f in features)


def has_feature(feature: str) -> bool:
    return feature in entitled_features()


def require_feature(feature: str) -> None:
    if has_feature(feature):
        return
    if _dev_unrestricted():
        return
    raise LicenseError(
        f"License does not include feature {feature!r}. "
        f"Set PRISMGUARD_LICENSE_FILE to a signed Team/Business license, or contact Insight IT: "
        f"{_ENTERPRISE_CONTACT}"
    )
