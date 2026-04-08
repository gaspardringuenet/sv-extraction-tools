import sqlite3
import logging
from pathlib import Path
import json
import pandas as pd
from rich.console import Console
from rich.panel import Panel

from .sql import shapes as sql
from .labelme.sync import update_db_from_all_jsons, sync_library_down, sync_library_up

logger = logging.getLogger(__name__)

# ---- Annotated shapes sub-registry ----
class ShapesRegistry:
    """Interacts with shapes table.
    """

    def __init__(self, conn: sqlite3.Connection, root_path: Path):
        self.conn = conn
        self.root_path = root_path


    def sync_db_from_jsons(self, json_dir: Path, ei_id: int, library: str, verbose: bool=True):
        # update db from JSON files
        update_db_from_all_jsons(
            conn=self.conn,
            json_dir=json_dir,
            root_path=self.root_path,
            ei_id=ei_id,
            library=library
        )
        # print an update to user (optional)
        if verbose:
            _print_update(self.conn, library)
        # remove shapes labeled as deleted (and consequently empty shapes libraries)
        self.conn.execute(sql.REMOVE_DELETED)
        self.conn.execute(sql.REMOVE_EMPTY_SHAPES_LIB)

    
    def sync_library_down(self, image_dataset_id, library):
        sync_library_down(self.conn, image_dataset_id, library)


    def sync_library_up(self, image_dataset_id, library):
        sync_library_up(self.conn, image_dataset_id, library)

    
    def list_ids(self, library: str):
        return list_valid_ROI_ids(self.conn, library)
    

    def get(self, id):
        cur = self.conn.execute(sql.SELECT_WITH_ID, (id,))
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"Id {id} not found in shapes table.")
        else:
            shape = dict(row)
            shape['points'] = json.loads(shape['points'])
            shape['bbox'] = json.loads(shape['bbox'])
            return shape
        

    def delete(self, id=None):
        if id is None:
            cur = self.conn.execute("DELETE FROM shapes")
            logger.info("Deleted all entries in shapes.")
        else:
            placeholders = ",".join("?" for _ in [*id])
            cur = self.conn.execute(f"DELETE FROM shapes WHERE id IN ({placeholders})", [*id])
            logger.info(f"Deleted {len([*id])} entry from shapes.")


    def to_df(self, library:str):
        return shapes_to_df(self.conn, library)

    


# ---- SQLite functions for the methods ----

def _print_update(conn: sqlite3.Connection, library: str) -> None:
    """Prints an update of the new, modified and deleted shapes in shapes registry.
    Also prints the total number of shapes in the current shapes library.

    Args:
        conn (sqlite3.Connection): connection to the registry database.
        library (str): the shapes library name.
    """

    flags = ['new', 'modified', 'deleted', 'unchanged']
    counts = {}

    try:
        with conn:
            cur = conn.cursor()
            for flag in flags:
                cur.execute(sql.COUNT_LIB_SHAPES_BY_STATUS, (flag, library))
                counts[flag] = dict(cur.fetchone()).get('COUNT(*)', 0)
    except sqlite3.OperationalError as e:
        print(e)

    n_tot = counts["new"] + counts["modified"] + counts["unchanged"]

    console = Console()
    update_str = (
        f"\n * {counts['new']} new"
        f"\n * {counts['modified']} modified"
        f"\n * {counts['deleted']} deleted"
        f"\n * Total number of shapes in library ({library}): {n_tot}"
    )
    panel = Panel(update_str, title="Registry update")
    console.print(panel)



def list_valid_ROI_ids(conn: sqlite3.Connection, library: str) -> list:
    #TODO FIX
    """For a given labelling library, returns a list of all valid ROI's in shapes. 

    Args:
        conn (sqlite3.Connection): connection to the registry database.
        library (str): the ROI library name.

    Returns:
        list: list ROI row ids.
    """
    cur = conn.cursor()
    cur.execute("SELECT id FROM shapes WHERE status != 'deleted' AND library == ?", (library, ))

    return [dict(row)["id"] for row in cur.fetchall()]


def shapes_to_df(conn: sqlite3.Connection, library: str) -> pd.DataFrame:

    cur = conn.execute("SELECT * FROM shapes WHERE library == ?", (library, ))
    data = [dict(row) for row in cur.fetchall()]
    df = pd.DataFrame(data)
    return df