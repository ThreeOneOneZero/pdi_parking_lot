"""Crops parking spaces out of a frame and rectifies them to a fixed size.

The lot surface is roughly planar, so its projection into the image is a homography.
Four point correspondences determine one exactly, which is why the annotation gives
four corners per space.
"""

from __future__ import annotations

import cv2
import numpy as np

# (width, height). Portrait, since spaces are normalised with their long axis vertical.
DEFAULT_SIZE = (48, 64)


def _edge(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a - b))


def order_contour(points: np.ndarray) -> np.ndarray:
    """Put the four corners in a canonical order.

    The XML gives no consistent starting corner or winding direction, so identical
    spaces would otherwise come out rotated or mirrored relative to each other.

    Sorting by angle around the centroid fixes the winding. Rolling the list until
    the first edge is the short one puts the long axis vertical. Starting from the
    corner with the smallest y resolves the remaining 180 degree flip.
    """
    points = np.asarray(points, dtype=np.float32)
    if points.shape != (4, 2):
        raise ValueError(f"expected a (4, 2) contour, got {points.shape}")

    centroid = points.mean(axis=0)
    angles = np.arctan2(points[:, 1] - centroid[1], points[:, 0] - centroid[0])
    ordered = points[np.argsort(angles)]

    best, best_key = None, None
    for k in range(4):
        candidate = np.roll(ordered, -k, axis=0)
        if _edge(candidate[0], candidate[1]) > _edge(candidate[1], candidate[2]):
            continue
        key = float(candidate[0][1])
        if best_key is None or key < best_key:
            best, best_key = candidate, key

    # Degenerate space (square or zero area): no roll satisfies the short-edge rule.
    return (best if best is not None else ordered).astype(np.float32)


def crop_space(
    image: np.ndarray,
    contour: np.ndarray,
    size: tuple[int, int] = DEFAULT_SIZE,
) -> np.ndarray:
    """Warp one space into a `size` patch, removing its perspective distortion."""
    width, height = size
    if width <= 0 or height <= 0:
        raise ValueError(f"size must be positive, got {size}")

    source = order_contour(contour)
    target = np.array(
        [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
        dtype=np.float32,
    )

    matrix = cv2.getPerspectiveTransform(source, target)
    return cv2.warpPerspective(
        image, matrix, (width, height),
        flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE,
    )


def contour_area(contour: np.ndarray) -> float:
    """Area of a space in the original frame, in pixels."""
    return float(cv2.contourArea(np.asarray(contour, dtype=np.float32)))


def draw_spaces(image: np.ndarray, spaces, thickness: int = 2) -> np.ndarray:
    """Overlay space outlines on a copy of the frame: red occupied, green free."""
    output = image.copy()
    for space in spaces:
        if space.occupied is None:
            colour = (0, 255, 255)
        else:
            colour = (0, 0, 255) if space.occupied else (0, 255, 0)
        pts = np.asarray(space.contour, dtype=np.int32).reshape(-1, 1, 2)
        cv2.polylines(output, [pts], isClosed=True, color=colour, thickness=thickness)
    return output
