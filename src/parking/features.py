"""Measurements computed from patch pixels alone.

These functions take an image and return a number;
whether that number separates occupied from free spaces is what the
experiments measure.
"""

from __future__ import annotations

import cv2
import numpy as np


def to_gray(patch: np.ndarray) -> np.ndarray:
    if patch.ndim == 3:
        return cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
    return patch


def gradient_magnitude(patch: np.ndarray) -> np.ndarray:
    """Sobel gradient magnitude, in float32."""
    gray = to_gray(patch).astype(np.float32)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    return cv2.magnitude(gx, gy)


def edge_density(patch: np.ndarray, threshold: float = 60.0) -> float:
    """Fraction of pixels whose gradient magnitude exceeds `threshold`.
    """
    return float((gradient_magnitude(patch) > threshold).mean())


def mean_intensity(patch: np.ndarray) -> float:
    """Average grey level. Included as the naive baseline the project argues against."""
    return float(to_gray(patch).mean())
