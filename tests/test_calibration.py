"""Tests for temperature scaling calibration."""

from __future__ import annotations

import numpy as np

from prismguard.models.calibration import apply_temperature, fit_temperature


def test_apply_temperature_scales_logits() -> None:
    logits = np.array([[0.0, 2.0]], dtype=np.float64)
    colder = apply_temperature(logits, 2.0)
    assert colder[0, 1] < logits[0, 1]


def test_fit_temperature_prefers_confident_labels() -> None:
    logits = np.array(
        [
            [2.0, -2.0],
            [-2.0, 2.0],
            [1.5, -1.5],
            [-1.5, 1.5],
        ],
        dtype=np.float64,
    )
    labels = np.array([0, 1, 0, 1], dtype=np.int64)
    temp = fit_temperature(logits, labels)
    assert 0.25 <= temp <= 4.0
