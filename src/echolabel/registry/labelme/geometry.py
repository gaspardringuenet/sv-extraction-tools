"""Geometry utilities"""

import hashlib
import json
from typing import List, Tuple


def clean_points(points:list, t_offset:int) -> list:
    """Applies ping axis offset and integer conversion to labelme shape points.

    Args:
        points (list): points (list of [x, y] indices) of a labelme shape.
        t_offset (int): ping axis offset of the image corresponding to the labelme JSON file from which points were taken. Coordinates can be floats.

    Returns:
        list: points with integer coordinates. If offset if correct, points represent the shape in the xr.Dataset used to produce the image dataset.
    """
    for p in points:
        p[0], p[1] = int(p[0]) + t_offset, int(p[1])
    return points


def get_bbox(points: List[List[int]]) -> Tuple[int, int, int, int]:
    """Computes the bounding box of a list of points.

    Args:
        points (list): list of points ([x, y] indices).

    Returns:
        tuple: bounding box in order (xmin, xmax, ymin, ymax).
    """
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), max(xs), min(ys), max(ys)


def geometry_hash(shape_type: str, points: list) -> str:
    """Encodes a shape as a string.

    Args:
        shape_type (str): string representing the type of shape (e.g., 'rectangle').
        points (list): list of points ([x, y] indices).

    Returns:
        str: hashed geometry.
    """
    payload = {
        "shape_type": shape_type,
        "points": points,
    }
    s = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(s.encode()).hexdigest()