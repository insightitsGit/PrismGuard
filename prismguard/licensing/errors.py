class LicenseError(RuntimeError):
    """Base license validation error."""


class LicenseExpiredError(LicenseError):
    """License past expires_at."""
