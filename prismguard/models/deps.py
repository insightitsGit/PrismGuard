"""Optional [guard-model] dependency helpers — keep ML imports out of the base package path."""

from __future__ import annotations

_GUARD_MODEL_EXTRA = (
    "classifier_mode / ONNX guard model requires the guard-model extra: "
    "pip install prismguard[guard-model]"
)


def require_numpy():
    """Import numpy or raise an actionable InstallError-style ImportError."""
    try:
        import numpy as np
    except ImportError as exc:
        raise ImportError(_GUARD_MODEL_EXTRA) from exc
    return np


def require_onnxruntime():
    try:
        import onnxruntime as ort
    except ImportError as exc:
        raise ImportError(_GUARD_MODEL_EXTRA) from exc
    return ort


def require_tokenizers_tokenizer():
    try:
        from tokenizers import Tokenizer
    except ImportError as exc:
        raise ImportError(_GUARD_MODEL_EXTRA) from exc
    return Tokenizer
