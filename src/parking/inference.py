"""Final decision for the spaces of one frame, as used by scripts.infer.

Each space is measured, placed between the free and taken levels of its own
unlabelled history and compared with the threshold calibrated on UFPR04.
"""

from __future__ import annotations

import numpy as np

from . import extraction as ext
from . import history, pipelines, split


def classify(image: np.ndarray, spaces, lot: str, date: str, past: history.SpaceHistory,
             config: dict) -> list[dict]:
    """Decision for each space; the history leaves out the frame's own date."""
    run = pipelines.PIPELINES[config["pipeline"]]
    result = []
    for space in spaces:
        measure = run(ext.crop_space(image, space.contour))
        free, taken = history.levels(past.values_for(lot, space.id, date, split.TEST),
                                     config["low"], config["high"])
        value = history.rescale(measure, free, taken, config["min_spread"])
        result.append({"space_id": space.id, "measure": round(measure, 4),
                       "free_level": round(free, 4), "taken_level": round(taken, 4),
                       "value": round(value, 4), "occupied": bool(value > config["threshold"])})
    return result
