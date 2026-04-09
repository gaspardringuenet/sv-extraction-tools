import sqlite3

from datetime import datetime
import json
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.mixture import GaussianMixture
from sklearn.cluster import KMeans
from typing import List, Tuple

from .sql import echotypes as sql


# ---- Echo-type sub-registry ----

class EchotypeRegistry:
    """Interacts with echo-types table
    """

    def __init__(self, conn: sqlite3.Connection, root_path: Path):
        self.conn = conn
        self.root_path = root_path


    def get_children_echotypes_libs(self, shapes_libname: str) -> List[str]:
        """List the names of echotypes libraries in registry sharing a given parent
        shapes library.

        Args:
            shapes_libname (str): Name of the parent shapes library.

        Returns:
            List[str]: Children echotypes libraries names in alphabetical order.
        """
        cur = self.conn.execute(sql.GET_CHILDREN_ECHOTYPES_LIBS, (shapes_libname,))
        rows = cur.fetchall()
        if rows is None:
            return []
        else:
            echotypes_libs = [dict(row)['name'] for row in rows]
            echotypes_libs.sort()
            return echotypes_libs


    def insert_echotypes_lib(self, name: str, parent_name: str) -> int:
        """Insert an echotypes library in registry. The echotypes library references its parent
        shapes library.

        Args:
            name (str): Name of the echotypes library to insert.
            parent_name (str): Name of the parent shapes library.

        Raises:
            ValueError: If the parent shapes library does not exist in registry.
            ValueError: If the insertion failed because the echotypes library already exists.

        Returns:
            int: Id of the echotypes library in the echotypes_libraries table in registry.
        """
        cur = self.conn.execute(sql.GET_SHAPES_LIB_ID, (parent_name,))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Invalid shapes library name - {parent_name}")
        shapes_lib_id = dict(row)['id']
        cur = self.conn.execute(sql.INSERT_ECHOTYPES_LIB, (shapes_lib_id, name))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Could not insert echotypes library ({name}) in registry. Maybe it already exists?")
        return dict(row)['id']


    def delete_echotypes_lib(self, name: str) -> None:
        """Delete an echotypes library (and children echotypes) from registry.

        Args:
            name (str): The name of the echotypes library.
        """
        self.conn.execute(sql.DELETE_ECHOTYPES_LIB, (name,))


    def get_echotypes_ids_in_lib(self, echotypes_libname: str) -> List[dict]:
        """List the ids of echotypes contained in a given echotypes library.

        Args:
            echotypes_libname (str): Name of the echotopes library.

        Returns:
            List[dict]: List of echotypes and shape ids. Each element is a dictionary
                with keys "echotype_id" and "shape_id".
        """
        cur = self.conn.execute(sql.LIST_IDS_IN_LIB, (echotypes_libname,))
        rows = cur.fetchall()
        if rows is None:
            return []
        return [dict(row) for row in rows]



    def insert(self, echotypes_libname: int, shape_id: str, features: dict, method: str, fitted_model: KMeans | GaussianMixture, cluster_id: int) -> int | None:

        cur = self.conn.execute(sql.GET_ECHOTYPES_LIB_ID, (echotypes_libname,))
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"Invalid echotypes library name - {echotypes_libname}")
        echotypes_library_id = dict(row)["id"]
        
        params = extract_clustering_params(fitted_model)
        state = extract_clustering_state(fitted_model)

        values = (
            echotypes_library_id,
            shape_id,
            f"{datetime.now():%Y-%m-%d %H:%M:%S}",
            json.dumps(features),
            method,
            json.dumps(params),
            json.dumps(state),
            cluster_id
        )

        cur = self.conn.execute(sql.INSERT_ECHOTYPE, values)
        row = cur.fetchone()

        if row is None:
            return None
        
        return dict(row)["id"]
    

    def update(self, echotype_id: int, features: dict, method: str, fitted_model: KMeans | GaussianMixture, cluster_id: int) -> int | None:
        
        params = extract_clustering_params(fitted_model)
        state = extract_clustering_state(fitted_model)

        values = (
            f"{datetime.now():%Y-%m-%d %H:%M:%S}",
            json.dumps(features),
            method,
            json.dumps(params),
            json.dumps(state),
            cluster_id,
            echotype_id
        )

        self.conn.execute(sql.UPDATE_ECHOTYPE, values)
    

    def get(self, id: int, default=None) -> Tuple[dict, GaussianMixture | KMeans]:

        cur = self.conn.execute(sql.SELECT_WITH_ID, (id,))
        row = cur.fetchone()

        if row is None:
            print(f"Id {id} not found in echotypes table.")
            return default
        
        row = dict(row)
        model = reconstruct_model(row)

        row['clustering_features'] = json.loads(row['clustering_features'])
        row['clustering_params'] = json.loads(row['clustering_params'])
        row['clustering_state'] = json.loads(row['clustering_state'])

        return row, model
    

    def delete(self, id: int) -> None:
        self.conn.execute(sql.DELETE_ECHOTYPE, (id,))


    def make_aggrid(self, echotypes_libname: str) -> pd.DataFrame:
        cur = self.conn.execute(sql.MAKE_AGGRID, (echotypes_libname,))
        rows = cur.fetchall()
        
        if rows is None:
            raise ValueError(f"No data found for echotypes library {echotypes_libname}.")
        rows = [dict(row) for row in rows]
        
        df = pd.DataFrame(rows)
        if 'echotype_modified' in df.columns:
            df['echotype_modified'] = pd.to_datetime(df['echotype_modified'], format="%Y-%m-%d %H:%M:%S")
        df["id"] = range(len(df))

        return df
    

    def copy_lib(self, source_name: str, dest_name: str) -> None:

        # Get the id of the source library
        cur = self.conn.execute("SELECT id FROM echotypes_libraries WHERE name = ?;", (source_name,))
        row = cur.fetchone()
        if not row:
            raise ValueError("Source library name does not exist in registry.")
        source_id = dict(row)["id"]

        # Copy at the library level
        cur = self.conn.execute(sql.COPY_ECHOTYPES_LIB, (dest_name, source_id))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Unable to copy echotype library with source id {source_id}.")
        dest_id = dict(row)["id"]

        # Copy at the entries level
        self.conn.execute(sql.COPY_ECHOTYPES_ENTRIES, (dest_id, source_id))
    


# ---- Helper functions ----

def extract_clustering_params(fitted_model: GaussianMixture | KMeans) -> dict:
    """Extract only init parameters from fitted model."""
    
    if isinstance(fitted_model, GaussianMixture):
        return {
            'covariance_type': fitted_model.covariance_type,
            'n_components': fitted_model.n_components,
            'random_state': 42,  # Always use fixed seed for reproducibility
            'n_init': fitted_model.n_init,
            'max_iter': fitted_model.max_iter,
            'tol': fitted_model.tol
        }
    
    elif isinstance(fitted_model, KMeans):
        return {
            'n_clusters': fitted_model.n_clusters,
            'random_state': 42,
            'n_init': fitted_model.n_init,
            'max_iter': fitted_model.max_iter,
            'tol': fitted_model.tol
        }
    
    else:
        raise ValueError(f"Unsupported model type: {type(fitted_model)}")


def extract_clustering_state(fitted_model: GaussianMixture | KMeans) -> dict:
    """Extract fitted parameters needed to reconstruct cluster assignments."""
    
    if isinstance(fitted_model, GaussianMixture):
        return {
            'means': fitted_model.means_.tolist(),  # Convert numpy to list
            'covariances': fitted_model.covariances_.tolist(),
            'weights': fitted_model.weights_.tolist(),
            'precisions_cholesky': fitted_model.precisions_cholesky_.tolist(),
        }
    
    elif isinstance(fitted_model, KMeans):
        return {
            'cluster_centers': fitted_model.cluster_centers_.tolist(),
            'inertia': float(fitted_model.inertia_),
            'n_iter': int(fitted_model.n_iter_)
        }
    
    else:
        raise ValueError(f"Unsupported model type: {type(fitted_model)}")
    

def reconstruct_model(row) -> GaussianMixture | KMeans:
    """Reconstruct fitted model from stored params."""
    
    method = row['clustering_method']
    params = json.loads(row['clustering_params'])
    state = json.loads(row['clustering_state'])
    
    if method == 'GaussianMixture':
        model = GaussianMixture(**params)
        model.means_ = np.array(state['means'])
        model.covariances_ = np.array(state['covariances'])
        model.weights_ = np.array(state['weights'])
        model.precisions_cholesky_ = np.array(state['precisions_cholesky'])
        return model
    
    elif method == 'KMeans':
        model = KMeans(**params)
        model.cluster_centers_ = np.array(state['cluster_centers'])
        model.inertia_ = state['inertia']
        model.n_iter_ = state['n_iter']
        return model
    
    else:
        raise ValueError(f"Unknown clustering method: {method}")