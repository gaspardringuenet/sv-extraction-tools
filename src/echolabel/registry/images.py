import sqlite3
import json
import logging

from ..label.config import ImageDataConfig
from .sql import images as sql

# ---- Image datasets sub-registry ----

class ImagesRegistry():
    """Interacts with image_datasets table.
    """
    
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_id(self, config: ImageDataConfig):
        return get_id_from_config(self.conn, config)

    def exists(self, config: ImageDataConfig):
        return self.get_id(config) is not None

    def insert_row(self, config: ImageDataConfig):   
        #TODO implement row existence check and force
        #TODO use relative echogram_images_dir path when inserting
        return insert_image_ds(self.conn, config)
    
    def get(self, id):
        cur = self.conn.execute("SELECT * FROM image_datasets WHERE id = ?;", (id,))
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"Id {id} not found in image_datasets table.")
        else:
            return dict(row)


# ---- Helper functions ----

# Get id or None

def get_id_from_config(conn: sqlite3.Connection, config: ImageDataConfig):
    
    values = (
        config.ei_id,
        str(config.save_dir),
        config.time_frame_size,
        config.vmin,
        config.vmax,
        config.z_min_idx,
        config.z_max_idx,
        json.dumps(config.frequencies),
        config.echogram_cmap
    )

    cur = conn.cursor()
    cur.execute(sql.GET_ID_FROM_VALUES, values)
    row = cur.fetchone()

    row_id = None if row is None else row[0]

    return row_id


# Insertion function

def insert_image_ds(
    conn: sqlite3.Connection, 
    config: ImageDataConfig, 
) -> int:
    """Inserts a new row in the image_datasets table and returns its row id. If the row already exists, just returns the row id.

    Args:
        conn (sqlite3.Connection): connection to the database containing the table.
        config (DatasetConfig): image dataset configuration object.
        verbose (bool, optional): whether to print insertion success information. Defaults to False.

    Returns:
        int: row id of the image dataset in the table.
    """

    values = (
        config.ei_id,
        str(config.save_dir),
        config.time_frame_size,
        config.vmin,
        config.vmax,
        config.z_min_idx,
        config.z_max_idx,
        json.dumps(config.frequencies),
        config.echogram_cmap
    )

    cur = conn.cursor()
    cur.execute(sql.INSERT, values)

    # Fetch the image dataset id
    row = cur.fetchone()
    if row is not None:     # if insert was successful (i.e. new line), the id was returned
        img_ds_id = row[0]  
        logging.info(f"Successfully added new image dataset with id {img_ds_id}")
    else:                   # if line already existed, we need to select the id
        img_ds_id =  get_id_from_config(conn, config)
        logging.info(f"Image dataset already exists in registry with id {img_ds_id}")
    
    return img_ds_id
