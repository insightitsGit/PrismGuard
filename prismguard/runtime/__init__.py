from prismguard.runtime.check import CheckResult, RuntimeChecker

__all__ = [
    "CheckResult",
    "RuntimeChecker",
    "create_checker_for_app",
    "create_checker_from_env",
    "create_checker_rules_only",
]


def __getattr__(name: str):
    if name in ("create_checker_for_app", "create_checker_from_env", "create_checker_rules_only"):
        from prismguard.runtime import factory as _factory

        return getattr(_factory, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
