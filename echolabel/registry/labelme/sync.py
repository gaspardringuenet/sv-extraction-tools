"""Syncing Labelme JSON files with database"""

import logging
from datetime import datetime
import json
from pathlib import Path
import shutil
import sqlite3
from typing import Sequence

from .geometry import geometry_hash, clean_points, get_bbox
from .parser import get_t_offset
from ..sql import shapes as sql

logger = logging.getLogger(__name__)

# ---- Direct information flow: JSONs --> DB ----

# Main functions

def update_db_from_all_jsons(
    conn: sqlite3.Connection, 
    json_dir: Path, 
    root_path: Path, 
    ei_id: int,
    library: str
) -> None:
    """Updates shapes using the output labelme JSON files present in json_dir.
    Calls update_shapes_from_json for each JSON file in json_dir then updates the status of deleted shapes.

    Args:
        conn (sqlite3.Connection): connection to the registry database.
        json_dir (Path): path to the directory containing all labelme JSON files.
        root_path (Path): path to the root of the escore repo.
        ei_id (int): registry row id of the image dataset from which the labelled image is taken.
        library_name (str): the ROI library name.
    """

    logger.debug("Changing status of new, unchanged and modified shapes in db using JSON files...")

    now = datetime.today().strftime('%Y-%m-%d %H:%M:%S')

    for json_file in json_dir.glob("*.json"):
        try:
            with conn:
                json_to_shapes(conn, json_file, root_path, now, ei_id, library)
        except sqlite3.OperationalError as e:
            logger.warning(f"Failed update of registry for JSON file - {json_file.name}\n{e}")
        
    # Handle deleted shapes
    logger.debug("Changing status of deleted shapes in db...")
    set_deleted(conn, json_dir, library)


def json_to_shapes(
    conn: sqlite3.Connection, 
    json_file: Path, 
    root_path: Path, 
    now: str,
    ei_id: int,
    library_name: str
) -> None:
    """Updates shapes table using one labelme JSON file.
    New shapes are added, modified shapes have their coordinates, geometry hash and bbox modified.
    'status' is updated for new, modified and unchanged shapes, but not for deleted shapes.

    Args:
        conn (sqlite3.Connection): connection to the registry database.
        json_file (Path): path to the labelme output JSON file.
        root_path (Path): path to the root of the escore repo.
        now (str): current datetime as string.
        ei_id (int): registry row id of the image dataset from which the labelled image is taken.
        library_name (str): the ROI library name.
    """

    with open(json_file, "r") as f:
        data = json.load(f)

    image_path = (json_file/data["imagePath"]).resolve().relative_to(root_path)
    t_offset = get_t_offset(image_name=image_path.name)
    
    for shape in data.get("shapes", []):
        shape_id = shape.get("id")

        if shape_id is None:
            continue # ignore untracked shapes

        cur = conn.cursor()
        cur.execute("SELECT geom_hash FROM shapes WHERE id = ?", (shape_id, ))
        row = cur.fetchone()

        if row is None:
            add_new_shape(conn, shape, t_offset, now, ei_id, library_name) # New shape
            continue

        row = dict(row)
        prev_geom_hash = row.get('geom_hash')
        new_geom_hash = geometry_hash(shape["shape_type"], shape["points"])

        if new_geom_hash != prev_geom_hash:
            modify_shape(conn, shape, t_offset, now) # Modified shape
        else:
            set_unchanged(conn, shape_id) # Unchanged


# Helper functions

## Shape insertion

def add_new_shape(
    conn: sqlite3.Connection, 
    shape: dict, 
    t_offset: int, 
    now: str, 
    ei_id: int,
    library_name: str
) -> None:
    """Add a new shape (row) to shapes table.

    Args:
        conn (sqlite3.Connection): connection to the registry database.
        shape (dict): labelme JSON shape object.
        t_offset (int): Ping axis offset of the image with regards to the echointegration.
        now (str): Current datetime as string.
        ei_id (int): Id of the reference echointegration.
        library_name (str): Shapes library name.
    """

    # Fetch id, label, and shape
    shape_id = shape.get("id")
    label = shape.get("label")
    shape_type = shape.get("shape_type")

    # Hash geometry (on raw points)
    geom_hash = geometry_hash(shape_type, shape.get("points"))

    # Clean points and apply ping axis offset + serialize for db storage
    points = clean_points(shape.get("points"), t_offset)
    points_json = json.dumps(points)

    # Compute bounding box
    bbox_json = json.dumps(get_bbox(points))

    # Insert shapes library (if not exists) and fetch id
    library_id = insert_shapes_library(conn, ei_id, library_name)

    # Insert shape
    insert_shape(
        conn,
        shape_id, library_id, label, 
        shape_type, points_json, bbox_json,
        geom_hash, now, now, "new"
    )


def insert_shapes_library(conn: sqlite3.Connection, ei_id: int, library_name: str) -> int:
    """Try to insert shapes library in registry. Return library id in all cases.

    Args:
        conn (sqlite3.Connection): Connection to the registry database
        ei_id (int): Id of the reference echointegration.
        library_name (str): Name of the shapes library.

    Returns:
        int: Id of library in shapes_libraries.
    """
    cur = conn.cursor()

    # Insert shapes library if it does not exist, fetch library id in any case
    cur.execute(sql.INSERT_SHAPES_LIB, (ei_id, library_name))
    row = cur.fetchone()
    if row is not None:
        library_id = row['id']
    else:
        cur.execute(sql.GET_SHAPES_LIB_ID_FROM_VALUES, (ei_id, library_name))
        row = cur.fetchone()
        library_id = row['id']

    return library_id


def insert_shape(conn: sqlite3.Connection, *shape_args):
    """Insert shape in shapes table"""
    cur = conn.cursor()
    cur.execute(sql.INSERT_SHAPE, (shape_args))



## Shape modification

def modify_shape(
    conn: sqlite3.Connection, 
    shape: dict, 
    t_offset: int, 
    now: str
) -> None:
    """Modify a row of shapes when the corresponding shape has been modified (points were moved) in labelme.

    Args:
        conn (sqlite3.Connection): connection to the registry database.
        shape (dict): labelme JSON shape object.
        t_offset (int): ping axis offset of the image with regards to the echointegration.
        now (str): current datetime as string.
    """

    cur = conn.cursor()

    # Fetch id, label, and shape
    shape_id = shape.get("id")
    label = shape.get("label")
    shape_type = shape.get("shape_type")

    # Hash geometry (on raw points)
    geom_hash = geometry_hash(shape_type, shape.get("points"))

    # Clean points and apply ping axis offset + serialize for db storage
    points = clean_points(shape.get("points"), t_offset)
    points_json = json.dumps(points)

    # Compute bounding box
    bbox_json = json.dumps(get_bbox(points))
    
    # New shape
    cur.execute(sql.UPDATE_SHAPE, (label, shape_type, points_json, bbox_json, geom_hash, now, "modified", shape_id))
    

## Assert the status of unchanged and deleted shapes

def set_unchanged(conn: sqlite3.Connection, shape_id: str) -> None:
    """Changes 'status' to 'unchanged' in shapes for the row corresponding to shape_id.

    Args:
        conn (sqlite3.Connection): connection to the registry database.
        shape_id (str): row id of the shape in shapes.
    """
    cur = conn.cursor()
    cur.execute(sql.SET_STATUS, ("unchanged", shape_id))


def set_deleted(conn: sqlite3.Connection, json_dir: Path | str, library: str) -> None:
    """Scans json_dir for labelme JSON files.
    All shapes in shapes whose id cannot be found in any JSON file have their 'status' attribute changed to 'deleted'.

    Args:
        conn (sqlite3.Connection): connection to the registry database.
        json_dir (Path | str): directory containing labelme JSON files.
        library (str): the ROI library name.
    """
    cur = conn.cursor()
    shape_ids = [shape["id"] for json_file in json_dir.glob("*.json") for shape in json.load(open(json_file))["shapes"]]
    sql_statement = sql.set_deleted(shape_ids)
    cur.execute(sql_statement, [library, *shape_ids])


# ---- Reverse information flow: DB --> JSONs ----

"""JSON files are the source of truth and inform db BUT in one case, we need db info to flow back to JSON.
To allow the user to easily switch between visualizations (image datasets) and still see all the shapes in current
library, we need to ensure all JSON shapes are visible by LABELME, regardless of the image dataset folder.

LABELME creates a .json file for each annotated image.
To distinguish between shapes library we store the JSONs in a subfolder of the image dataset.

We use the following structure:

└── appData
    └── echogram_images
        ├── cruise_name_EI_001
        │   └── image_dataset_001 (names using its params)
        │   │   ├── shapes_library_A             <--┒
        │   │   │       ├── image_000.json          │
        │   │   │       ...                         │
        │   │   ├── shapes_library_B/               │
        │   │   ├── image_000.png                   ├─ We need to ensure those are synced
        │   │   ├── ...                             │
        │   │   └── image_N.png                     │
        │   └── image_dataset_002                   │
        │       ├── shapes_library_A             <--┚
        │       ...
        ├── ...
        └── cruise_name_EI_X

Syncing can be achieved using folders/files names, but that not great in terms of robustness. We use the database instead.

After a labelling session (bound to a image dataset and shapes library):

*   Fetch the echointegration id
*   List all image dataset folders for this echointegration
*   Paste the library's JSON folder into each

UPDATE: a two step algorithm keeps all folder for a library synced:
1.  Importing from any other folder for the same EI + library before labelling session
2.  Exporting to all other folders after labelling session
"""

def sync_library_down(conn: sqlite3.Connection, image_dataset_id: int, library: str) -> None:
    logger.debug("Syncing library JSON down...")

    # Fetch the EI and destination folder from db
    cur = conn.execute("SELECT ei_id, image_folder_path FROM images_datasets WHERE id = ?", (image_dataset_id, ))
    row = cur.fetchone()

    if row is None:
        raise ValueError(f"Image dataset {image_dataset_id} not found.")

    row = dict(row)
    dest_image_folder = Path(row["image_folder_path"])
    ei_id = row["ei_id"]

    # Fetch a source folder
    cur = conn.execute("SELECT DISTINCT image_folder_path FROM images_datasets WHERE ei_id = ? and id != ?", (ei_id, image_dataset_id))
    row = cur.fetchone()

    if row is None:
        return
    
    source_image_folder = dict(row)["image_folder_path"]
    
    # Import
    _copy_paste_library(source_image_folder, [dest_image_folder], library)

    logger.info(f"Library synced down: imported from image folder {dest_image_folder} sharing EI {ei_id:02d}")


def sync_library_up(conn: sqlite3.Connection, image_dataset_id: int, library: str) -> None:
    """Copies LABELME's shapes library folder (within the image dataset folder) and pastes it to all
    related image datasets (i.e. datasets built from the same echointegration).
    As a results, running the labelling app from any image datasets shows the same shapes (for this library). 

    Args:
        conn (sqlite3.Connection): connection to the registry database.
        image_dataset_id (int): row id of the source image dataset in the registry.
        library (str): name of the shapes library to propagate.
    """
    logger.debug("Syncing library JSON up...")

    # Fetch the EI and source folder from db
    cur = conn.execute("SELECT ei_id, image_folder_path FROM images_datasets WHERE id = ?", (image_dataset_id, ))
    row = cur.fetchone()

    if row is None:
        raise ValueError(f"Image dataset {image_dataset_id} not found.")

    row = dict(row)
    source_image_folder = Path(row["image_folder_path"])
    ei_id = row["ei_id"]

    # Collect all destination folders
    cur = conn.execute("SELECT DISTINCT image_folder_path FROM images_datasets WHERE ei_id = ? and id != ?", (ei_id, image_dataset_id))
    rows = cur.fetchall()
    dest_image_folders = [dict(row)["image_folder_path"] for row in rows]

    # Propagate
    _copy_paste_library(source_image_folder, dest_image_folders, library)

    logger.info(f"Library synced up: available accross {len(dest_image_folders) + 1} image datasets" \
                " related to EI {ei_id:02d}")


def _copy_paste_library(source_image_folder: Path | str, dest_image_folders: Sequence[Path|str], library: str):
    source_path = Path(source_image_folder) / library

    if not source_path.exists():
        logger.warning(f"Source path {source_path} does not exist. Skipping propagations.")
        return

    for image_folder in dest_image_folders:
        dest_path = Path(image_folder) / library
        dest_path.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
