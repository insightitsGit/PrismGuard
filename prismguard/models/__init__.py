"""PrismGuard-owned Guard Model artifacts, ONNX inference, export, and training.

Importing symbols from this package requires the ``[guard-model]`` extra when
loading the ONNX classifier. Prefer ``prismguard.models.loader`` helpers.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "ONNXPromptInjectionClassifier",
    "load_onnx_classifier",
    "resolve_artifact_dir",
]


def __getattr__(name: str) -> Any:
    if name == "ONNXPromptInjectionClassifier":
        from prismguard.models.onnx_classifier import ONNXPromptInjectionClassifier

        return ONNXPromptInjectionClassifier
    if name == "load_onnx_classifier":
        from prismguard.models.loader import load_onnx_classifier

        return load_onnx_classifier
    if name == "resolve_artifact_dir":
        from prismguard.models.loader import resolve_artifact_dir

        return resolve_artifact_dir
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
