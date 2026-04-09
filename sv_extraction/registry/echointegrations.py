import json
import logging
from pathlib import Path
import sqlite3
from typing import List
import xarray as xr

from .sql import echointegrations as sql

logger = logging.getLogger(__name__)

# ---- Echointegrations sub-registry ----

class EIRegistry():
    """Interacts with echointegrations table.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def insert_row(self, ds: xr.Dataset, nc_files_list: list) -> int:
        return insert_ei(self.conn, ds, nc_files_list)
    
    def get(self, id: int) -> dict:
        cur = self.conn.execute("SELECT * FROM echointegrations WHERE id = ?;", (id,))
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"Id {id} not found in echointegrations table.")
        return dict(row)
        
    def count_shapes(self) -> List[dict[str, int]]:
        """Count the number of shapes per parent echointegration"""
        cur = self.conn.execute(sql.COUNT_SHAPES)
        rows = cur.fetchall()
        if rows is None:
            raise ValueError("Registry is empty.")
        return [dict(row) for row in rows]


# ---- Helper function ----

def insert_ei(conn:sqlite3.Connection, ds: xr.Dataset, nc_files_list: List[Path | str]) -> int:
    """Inserts the info related to an echointegration (i.e. an acoustic dataset for a given cruise) into the echointegration table.
    Attributes an id to that echointegration.
    If the echointegration already exists, just returns its id.

    Args:
        conn (sqlite3.Connection): connection to the registry database containing the echointegration table.
        ds (xr.Dataset): the dataset to insert.
        nc_files_list (list): the list of .nc files supporting the dataset is also added to the table (Helps differentiate datasets with equal metadata but differents files).

    Returns:
        int: row id of the echointegration in the table.
    """

    channels = list(ds.channel.values)

    values = (
        ds.attrs.get("cruise_name"),
        json.dumps(channels),
        ds.attrs.get("data_ping_axis_interval_type"),
        ds.attrs.get("data_ping_axis_interval_value"),
        ds.attrs.get("data_range_axis_interval_type"),
        ds.attrs.get("data_range_axis_interval_value"),
        json.dumps([str(Path(f).resolve()) for f in nc_files_list])
    )

    cur = conn.cursor()
    cur.execute(sql.INSERT_EI, values)

    # Fetch the ei id
    row = cur.fetchone()
    if row is not None:     # if insert was successful (i.e. new line), the id was returned
        ei_id = row[0]
        logger.info(f"Echointegration created with id {ei_id}.")    
    else:                   # if line already existed, we need to select the id
        cur.execute(sql.GET_ID_FROM_VALUES, values)
        ei_id = cur.fetchone()[0]
        logger.info(f"Echointegration already exists with id {ei_id}.")
        logger.warning(
            "Different casings for input data paths are treated as identical in registry. "
            "If you intended to add a different dataset, make sure the input files contained "
            "in the specified input folder differ from the already existing ones."
        )
    return ei_id
        