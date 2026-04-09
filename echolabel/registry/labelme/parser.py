"""Labelme JSON files handling"""

import json
from pathlib import Path
import re

from .geometry import geometry_hash


def add_shape_ids(json_dir: Path, session_id: str, start_id: int = 0) -> None:
    """Adds unique 'id' to each shape in all JSONs in json_dir.
    IDs are prefixed with session_id and are unique per session.

    Args:
        json_dir (Path): directory containing the labelme JSON files for the current image dataset and the current labelling session.
        session_id (str): current session id.
        start_id (int, optional): start of the shape counter. Defaults to 0.
    """
    counter = start_id

    for json_file in json_dir.glob("*.json"):
        with open(json_file, "r") as f:
            data = json.load(f)

        for shape in data.get("shapes", []):
            if "id" not in shape:  # newly created shape
                shape["id"] = f"{session_id}_{counter:04d}"
                counter += 1

        with open(json_file, "w") as f:
            json.dump(data, f, indent=2)


def update_geom_hash_json(json_dir: Path) -> None:
    """Update the 'geom_hash' key of the shapes in the labelme JSON files present in json_dir.

    Args:
        json_dir (Path): the directory containing labelme JSON files.
    """
    for json_file in json_dir.glob("*.json"):
        with open(json_file, "r") as f:
            data = json.load(f)

        for shape in data.get("shapes", []):
            shape["geom_hash"] = geometry_hash(shape)

        with open(json_file, "w") as f:
            json.dump(data, f, indent=2)


# ---- Cleaning function (to transfer shape data from JSONs to database) ----

def get_t_offset(image_name: str) -> int:
    """Finds the ping axis offset of an echogram image based on the image name.

    Args:
        image_name (str): the name of an image created by escore.builder.build_dataset

    Returns:
        int: the start index of the image in the xr.Dataset object it was created from.
    """
    match = re.search(r'_T(\d+)', str(image_name))
    if match is None:
        raise ValueError(f"Could not extract T index from name: {image_name}")
    offset = int(match.group(1))

    return offset