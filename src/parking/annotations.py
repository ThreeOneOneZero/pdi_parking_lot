"""Reads PKLot XML annotations. See docs/dados.md section 5.1 for the format."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class Space:
    """One annotated parking space. `contour` is a (4, 2) array of image points."""

    id: str
    contour: np.ndarray
    occupied: bool | None

    @property
    def labeled(self) -> bool:
        return self.occupied is not None


@dataclass(frozen=True)
class Annotation:
    parking_id: str
    source: Path
    spaces: list[Space]
    skipped: int

    @property
    def labeled(self) -> list[Space]:
        return [s for s in self.spaces if s.labeled]

    def __len__(self) -> int:
        return len(self.spaces)


def _read_contour(space: ET.Element) -> np.ndarray | None:
    contour = space.find("contour")
    if contour is None:
        return None

    # 53 of the 2553 XML files (all in UFPR04) spell the tag <Point> instead of
    # <point>. A case-sensitive lookup silently drops every space in those frames.
    points = []
    for point in contour:
        if point.tag.lower() != "point":
            continue
        try:
            points.append((float(point.get("x")), float(point.get("y"))))
        except (TypeError, ValueError):
            return None

    if len(points) != 4:
        return None
    return np.array(points, dtype=np.float32)


def read_annotation(path: str | Path) -> Annotation:
    """Parse one PKLot XML file. Spaces with an unusable contour are skipped."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"annotation not found: {path}")

    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as err:
        raise ValueError(f"invalid XML in {path}: {err}") from err

    if root.tag != "parking":
        raise ValueError(f"unexpected root '{root.tag}' in {path}, expected 'parking'")

    spaces, skipped = [], 0
    for element in root.findall("space"):
        contour = _read_contour(element)
        if contour is None:
            skipped += 1
            continue
        occupied = element.get("occupied")
        spaces.append(
            Space(
                id=element.get("id", "?"),
                contour=contour,
                occupied=None if occupied is None else occupied.strip() == "1",
            )
        )

    return Annotation(
        parking_id=root.get("id", "?"),
        source=path,
        spaces=spaces,
        skipped=skipped,
    )


def annotation_for(frame: str | Path) -> Path:
    """Path of the XML sitting next to a .jpg frame."""
    return Path(frame).with_suffix(".xml")


def list_frames(
    root: str | Path,
    lot: str | None = None,
    weather: str | None = None,
) -> list[Path]:
    """List frames under <root>/<lot>/<weather>/<date>/. Frames without XML are omitted."""
    root = Path(root)
    if not root.is_dir():
        raise FileNotFoundError(f"data directory not found: {root}")

    pattern = f"{lot or '*'}/{weather or '*'}/*/*.jpg"
    return sorted(f for f in root.glob(pattern) if annotation_for(f).is_file())
