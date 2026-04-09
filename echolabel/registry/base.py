import sqlite3

from pathlib import Path
import pandas as pd
from importlib.resources import files

from .echointegrations import EIRegistry
from .images import ImagesRegistry
from .shapes import ShapesRegistry
from .echotypes import EchotypeRegistry

from .sql import base as sql


# ---- Container class for registry ----

class Registry:

    def __init__(self, db_path: Path, root_path: Path):
        self.db_path = db_path
        self.root_path = root_path
        self.conn = self._init_db()

        self.ei = EIRegistry(self.conn)                                     # The echointegrations sub-registry
        self.images = ImagesRegistry(self.conn)                             # The image datasets sub-registry
        self.shapes = ShapesRegistry(self.conn, self.root_path)             # The shapes sub-registry (handles shapes and shapes libraries)
        self.echotypes = EchotypeRegistry(self.conn, self.root_path)        # The echo-types sub-registry (handles echotypes and echotypes libraries)

    def _init_db(self):
        return init_db(self.db_path)
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.conn.close()

    def get_ei_from_shapes_library(self, library: str) -> int:
        return get_ei_from_shapes_library(self.conn, library)
    
    def get_ei_from_roi(self, roi_id: str) -> int:
        return get_ei_from_roi(self.conn, roi_id)
    
    def get_echotype_export_df(self, echotype_libname):
        sql = """
            SELECT * FROM echotypes
            JOIN roi_table AS roi
            ON roi_id = roi.id
            WHERE library_name = ?;
        """
        cur = self.conn.execute(sql, (echotype_libname,))
        rows = [dict(row) for row in cur.fetchall()]
        return pd.DataFrame(rows)




# ---- SQLite function for the methods ----

# Initialize database
def load_schema() -> str:
    sql_content = files("sv_extraction.registry").joinpath("sql/schema.sql").read_text()
    return sql_content
    

def init_db(db_path: Path | str) -> sqlite3.Connection:
    """Open the registry database and create tables.

    Args:
        db_path (Path | str): path to the .db file.

    Returns:
        sqlite3.Connection: connection to the database.
    """
    
    # Create / connect to the database
    conn = sqlite3.connect(db_path)

    # Ensure foreign keys are activate (for cascading deletions)
    conn.execute("PRAGMA foreign_keys = ON;")

    # Ensure dictionary cursor (helps when fetching data from db)
    conn.row_factory = sqlite3.Row

    # Create tables
    schema = load_schema()
    conn.executescript(schema)
    conn.commit()

    return conn


# Get the echointegration id from a labelling library name
# The link is necessarily unique (even though library can point to several image datasets, they all point to the same echointegration)

def get_ei_from_shapes_library(conn: sqlite3.Connection, library: str) -> int:

    cur = conn.execute(sql.EI_FROM_SHAPES_LIB, (library,))

    rows = cur.fetchall()
    ids = [dict(row)['id'] for row in rows]

    if len(set(ids)) > 1:
        raise ValueError(f"Library {library} is associated with multiple echointegrations.")
    else:
        return ids[0]
    

# Get the echointegration id from an roi_id

def get_ei_from_roi(conn: sqlite3.Connection, roi_id: str) -> int:
    sql = """
        SELECT DISTINCT
            ei.id
        FROM echointegrations AS ei
        JOIN images_datasets AS img
            on ei.id == img.ei_id
        JOIN roi_table AS roi
            ON roi.image_dataset == img.id
        WHERE roi.id == ?;
    """
    cur = conn.execute(sql, (roi_id,))

    rows = cur.fetchall()
    ids = [dict(row)['id'] for row in rows]

    if len(set(ids)) > 1:
        raise ValueError(f"ROI `{roi_id}` is associated with multiple echointegrations.")
    else:
        return ids[0]