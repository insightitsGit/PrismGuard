"""Production HTTP guard service (Business tier — requires enterprise_http license)."""

from __future__ import annotations

import os
import time
from typing import Any

from pydantic import BaseModel, Field

from prismguard.licensing.features import ENTERPRISE_HTTP, require_feature
from prismguard.observability.metrics import get_metrics
from prismguard.runtime.output_scan import scan_output


class CheckRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=32_000)
    session_id: str | None = None


class CheckResponse(BaseModel):
    decision: str
    resolution_gate: str
    matched_category: str | None = None
    normalized_prompt: str = ""
    details: dict[str, Any] = Field(default_factory=dict)
    latency_ms: float = 0.0


class ScanOutputRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=128_000)


class ScanOutputResponse(BaseModel):
    decision: str
    resolution_gate: str
    matched_pattern: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    latency_ms: float = 0.0


class HealthResponse(BaseModel):
    status: str
    ready: bool
    domain: str
    classifier_ready: bool


_checker = None


def _get_checker():
    global _checker
    if _checker is not None:
        return _checker
    from prismguard.runtime.factory import create_checker_from_env

    # Sidecar defaults: ONNX only with PRISMGUARD_USE_ONNX=1; domain not law-by-default.
    os.environ.setdefault("PRISMGUARD_APP_PROFILE", "sidecar")
    _checker = create_checker_from_env()
    return _checker


def create_app():
    """FastAPI app factory — lazy-imports fastapi so OSS installs stay light."""
    require_feature(ENTERPRISE_HTTP)
    try:
        from fastapi import FastAPI
        from starlette.concurrency import run_in_threadpool
    except ImportError as exc:
        raise ImportError(
            "HTTP service requires the serve extra: pip install prismguard[serve]"
        ) from exc

    app = FastAPI(
        title="PrismGuard API",
        version="0.1.9",
        description="Audited prompt-injection guard service (Business tier).",
    )

    @app.on_event("startup")
    def _warm() -> None:
        _get_checker()

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        domain = os.environ.get("PRISMGUARD_DOMAIN", "").strip() or "core"
        try:
            checker = _get_checker()
            enforce = getattr(checker, "_enforce", checker)
            gm = getattr(enforce, "_guard_model", None)
            ready = gm is None or bool(getattr(gm, "is_ready", True))
        except Exception:
            ready = False
        return HealthResponse(
            status="ok",
            ready=ready,
            domain=domain,
            classifier_ready=ready,
        )

    @app.get("/ready")
    def ready() -> dict[str, bool]:
        h = health()
        return {"ready": h.ready}

    @app.get("/metrics")
    def metrics() -> Any:
        from fastapi.responses import PlainTextResponse

        return PlainTextResponse(get_metrics().prometheus_text(), media_type="text/plain; version=0.0.4")

    @app.post("/v1/check", response_model=CheckResponse)
    async def check_input(req: CheckRequest) -> CheckResponse:
        start = time.perf_counter()
        metrics = get_metrics()
        try:
            checker = _get_checker()
            result = await run_in_threadpool(checker.check, req.text, session_id=req.session_id)
            metrics.record_check(decision=result.decision, gate=result.resolution_gate)
        except Exception:
            metrics.record_error()
            raise
        return CheckResponse(
            decision=result.decision,
            resolution_gate=result.resolution_gate,
            matched_category=result.matched_category,
            normalized_prompt=result.normalized_prompt,
            details=result.details,
            latency_ms=(time.perf_counter() - start) * 1000,
        )

    @app.post("/v1/scan-output", response_model=ScanOutputResponse)
    async def scan_output_endpoint(req: ScanOutputRequest) -> ScanOutputResponse:
        start = time.perf_counter()
        metrics = get_metrics()
        try:
            scan = await run_in_threadpool(scan_output, req.text)
            metrics.record_scan()
        except Exception:
            metrics.record_error()
            raise
        return ScanOutputResponse(
            decision=scan.decision,
            resolution_gate=scan.resolution_gate,
            matched_pattern=scan.matched_pattern,
            details=scan.details,
            latency_ms=(time.perf_counter() - start) * 1000,
        )

    return app


def main() -> None:
    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit(
            "prismguard-serve requires the serve extra: pip install prismguard[serve]"
        ) from exc

    host = os.environ.get("PRISMGUARD_HOST", "0.0.0.0")
    port = int(os.environ.get("PRISMGUARD_PORT", "8090"))
    uvicorn.run("prismguard.http.service:create_app", factory=True, host=host, port=port)


if __name__ == "__main__":
    main()
