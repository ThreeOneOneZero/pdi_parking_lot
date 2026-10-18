"""Photometric normalizations applied to a grayscale patch before the measure.

Parameters are fixed beforehand rather than tuned, so no choice here was made by
looking at the test partition.
"""

from __future__ import annotations

import cv2
import numpy as np

CLAHE_CLIP = 2.0
# 4x4 tiles of a 48x64 patch are 12x16 px; OpenCV's default 8x8 would leave 6x8.
CLAHE_TILES = (4, 4)

STRETCH_LOW = 2
STRETCH_HIGH = 98


def clahe(gray: np.ndarray, clip: float = CLAHE_CLIP, tiles=CLAHE_TILES) -> np.ndarray:
    """Equalize contrast tile by tile, limiting how much flat regions get amplified."""
    return cv2.createCLAHE(clipLimit=clip, tileGridSize=tiles).apply(gray.astype(np.uint8))


def stretch(gray: np.ndarray, low: float = STRETCH_LOW, high: float = STRETCH_HIGH) -> np.ndarray:
    """Map the `low` and `high` percentiles of the patch to 0 and 255.

    A patch with no spread between the two percentiles is returned unchanged, so a
    uniform patch stays uniform instead of being divided by zero.
    """
    lo, hi = np.percentile(gray, [low, high])
    if hi <= lo:
        return gray.astype(np.uint8)
    scaled = (gray.astype(np.float32) - lo) * (255.0 / (hi - lo))
    return np.clip(scaled, 0, 255).astype(np.uint8)
