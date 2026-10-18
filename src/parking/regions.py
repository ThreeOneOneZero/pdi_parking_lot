"""Region measure: segment the edges, clean them with morphology, keep the largest blob.

Edge density counts every edge pixel, so scattered asphalt texture and a car's
outline can score alike. Here the edges become a mask, closing merges the fragments
of a car into one blob, opening removes what stays thin, such as painted lines and
isolated specks, and the measure is how much of the patch the largest blob covers.
"""

from __future__ import annotations

import cv2
import numpy as np

from . import features

EDGE_THRESHOLD = 60.0

# Best sizes without normalization, chosen on the calibration partition by
# scripts/e4_sweep.py and never on test frames; pipelines.py binds each choice.
CLOSE_SIZE = 5
OPEN_SIZE = 3


def edge_mask(gray: np.ndarray, threshold: float = EDGE_THRESHOLD) -> np.ndarray:
    """Binary mask, 255 where the gradient magnitude exceeds `threshold`.

    The same edges edge density counts, so the comparison changes only the measure.
    """
    return np.where(features.gradient_magnitude(gray) > threshold, 255, 0).astype(np.uint8)


def ellipse(size: int) -> np.ndarray:
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))


def clean(mask: np.ndarray, close_size: int = CLOSE_SIZE, open_size: int = OPEN_SIZE) -> np.ndarray:
    """Closing then opening.

    Closing comes first because a car outline is only a few pixels wide, and an
    opening applied to it would erase the car together with the noise.
    """
    closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, ellipse(close_size))
    return cv2.morphologyEx(closed, cv2.MORPH_OPEN, ellipse(open_size))


def largest_component(mask: np.ndarray) -> np.ndarray:
    """Mask of the largest 8-connected region, or an empty mask if there is none."""
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    if count <= 1:
        return np.zeros_like(mask)
    biggest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return np.where(labels == biggest, 255, 0).astype(np.uint8)


def describe(region: np.ndarray) -> dict:
    """Descriptors of one region, all dimensionless.

    area_fraction: region pixels / patch pixels.
    extent: region pixels / pixels of its bounding box.
    solidity: region pixels / pixels of its convex hull.
    """
    area = int(np.count_nonzero(region))
    if area == 0:
        return {"area_fraction": 0.0, "extent": 0.0, "solidity": 0.0}

    points = cv2.findNonZero(region)
    _, _, width, height = cv2.boundingRect(points)

    # The hull is filled and counted in pixels, like the region; its polygon area
    # runs through pixel centres and would come out smaller than the region itself.
    hull = np.zeros_like(region)
    cv2.fillConvexPoly(hull, cv2.convexHull(points), 255)
    return {
        "area_fraction": area / region.size,
        "extent": area / (width * height),
        "solidity": area / int(np.count_nonzero(hull)),
    }


def stages(gray: np.ndarray, close_size: int = CLOSE_SIZE, open_size: int = OPEN_SIZE) -> dict:
    """Every intermediate mask of the measure, for figures and inspection."""
    edges = edge_mask(gray)
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, ellipse(close_size))
    opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, ellipse(open_size))
    return {"edges": edges, "closed": closed, "opened": opened,
            "region": largest_component(opened)}


def region_fraction(gray: np.ndarray, close_size: int = CLOSE_SIZE,
                    open_size: int = OPEN_SIZE) -> float:
    """The E4 measure: fraction of the patch covered by the largest cleaned region."""
    region = largest_component(clean(edge_mask(gray), close_size, open_size))
    return float(np.count_nonzero(region)) / region.size
