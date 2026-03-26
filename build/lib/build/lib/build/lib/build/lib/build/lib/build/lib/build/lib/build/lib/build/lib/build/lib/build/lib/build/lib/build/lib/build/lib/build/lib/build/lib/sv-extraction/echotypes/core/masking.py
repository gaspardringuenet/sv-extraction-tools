import numpy as np
from skimage.draw import polygon
from typing import Tuple, List


def get_labelme_mask(
    mask_shape: Tuple[int, int, int, int],
    shape_type: str,
    shape_points: List[List[int]]
) -> np.ndarray:
    """Mask using Labelme format annotations for shape types and points.
    Return a boolean mask of pixels contained within a shape delimited by an ordered list of points.
    """

    if shape_type == "rectangle":
        assert len(shape_points) == 2, f"2 points excpected for rectangle shape masking. {len(shape_points)} given. {len(shape_points) = }"
        mask = make_rectangle_mask(mask_shape, shape_points)
        
    elif shape_type == "polygon":
        assert len(shape_points) >= 3, f"At least 3 points excpected for rectangle shape masking. {len(shape_points)} given. {len(shape_points) = }"
        mask = make_polygon_mask(mask_shape, shape_points)

    elif shape_type == "circle":
        assert len(shape_points) == 2, f"2 points excpected for cirlce shape masking. {len(shape_points)} given. {len(shape_points) = }"
        mask = make_circle_mask(mask_shape, shape_points)
    else:
        raise NotImplementedError(f"Masking not implemented for {shape_type = }")

    return mask


def make_rectangle_mask(shape: Tuple[int, int], points: list | np.ndarray) -> np.ndarray:
    mask = np.zeros(shape)
    points = np.array(points)

    mask[points[:, 0].min():points[:, 0].max()+1, 
         points[:, 1].min():points[:, 1].max()+1] = 1
    
    return (mask == 1)


def make_polygon_mask(shape: Tuple[int, int], points: list | np.ndarray) -> np.ndarray:
    mask = np.zeros(shape)
    points = np.array(points)

    rr, cc = polygon(
        points[:, 0],  # rows
        points[:, 1],  # cols
        shape=mask.shape
    )
    mask[rr, cc] = 1

    return (mask == 1)

def make_circle_mask(shape: Tuple[int, int], points: list | np.ndarray) -> np.ndarray:
    raise NotImplementedError("Masking not implemented for 'circle' shape type.")