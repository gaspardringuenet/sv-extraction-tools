from dash import Dash, Input, Output, State, dcc

import numpy as np
from pathlib import Path
from typing import Tuple
import xarray as xr

from ...registry import Registry
from ..core import processing as proc


def register_callbacks_selection_table(app: Dash, db_path: Path, root_path: Path):
    
    @app.callback(
        Output('roi-data-grid', 'rowData'),
        Input('select-echotype-lib', 'value'),
        Input('update-aggrid-flag', 'data')
    )
    def update_aggrid(echotypes_libname: str, _) -> dict:
        """Update the AgGrid containing both candidate ROIs and created echotypes for a
        given echotypes library. Candidate ROIs are all shapes in the echotypes library's
        parent shapes library.

        Args:
            echotypes_libname (str): Selected echotypes library name.

        Returns:
            dict: Row data for the AgGrid.
        """
        with Registry(db_path, root_path) as registry:
            df = registry.echotypes.make_aggrid(echotypes_libname)
        return df.to_dict('records')
    

    @app.callback(
        Output('selected-roi', 'data'),
        Output('selected-echotype', 'data'),
        Input('roi-data-grid', 'selectedRows')
    )
    def select_roi(row: dict) -> Tuple[int, int]:
        """Cache the registry data for the selected ROI and echotype corresponding to the selected row in AgGrid.
        The echotype id set to None if the selected row corresponds to an untreated ROI.
        Both ids are set to None if no row is selected
        EDIT: Also cache a mask DataArray of ROI data points in custom app cache.

        Args:
            row (dict): Data from the AgGrid's selected row.

        Returns:
            Tuple[dict, dict]: (ROI row, Echotype row)
        """

        # Default when no row is selected
        if not row:
            return None, None
        
        # Fectch id's
        shape_id = row[0]['shape_id']
        echotype_id = row[0]['echotype_id']

        # Fetch registry data
        with Registry(db_path, root_path) as registry:
            shape_data = registry.shapes.get(shape_id) if shape_id is not None else None
            echotype_data, model = registry.echotypes.get(echotype_id) if echotype_id is not None else (None, None)

        # Load and cache ROI mask in server (custom app cache)
        app.cache.set_roi_mask(get_roi_mask(app, shape_data))
        app.cache.set_clustering_model(model, domain='saved')

        # Return registry info to Dash cache
        return shape_data, echotype_data
    

    @app.callback(
        Output('export-file-download', 'data'),
        Input('export-file-button', 'n_clicks'),
        State('select-echotype-lib', 'value'),
        State('ei-metadata', 'data'),
        prevent_initial_call=True,
    )
    def export_library(_, echotypes_libname: str, ei_meta: dict):

        ds: xr.Dataset = app.cache.get_dataset()
        if ds is None:
            raise ValueError("No dataset available in app cache")

        obs_sv_list = []
        echotype_ids = []
        shape_ids = []
        cluster_ids = []
        clustering_methods = []

        # Load registry once
        with Registry(db_path, root_path) as registry:
            ids_list = registry.echotypes.get_echotypes_ids_in_lib(echotypes_libname)

            for i, id_dict in enumerate(ids_list):

                echotype_id = id_dict["echotype_id"]
                shape_id = id_dict["shape_id"]

                try:
                    
                    # Fetch data from registry
                    shape_data = registry.shapes.get(shape_id) if shape_id else None
                    echotype_data, model = registry.echotypes.get(echotype_id)

                    var = echotype_data["clustering_features"]["var"]["name"]
                    ref_frequency = echotype_data["clustering_features"]["var"].get("ref")
                    frequencies = echotype_data["clustering_features"]["frequencies"]
                    cluster_id = echotype_data["cluster_id"]

                    # Build echotype Sv DataArray
                    roi_mask = get_roi_mask(app, shape_data)
                    bbox_sv = proc.preprocess_sv(ds.Sv, window=roi_mask.attrs.get("bbox"))
                    roi_sv = bbox_sv.where(roi_mask)
                    labels, _ = proc.cluster_sv(
                        sv=roi_sv.sel(channel=frequencies),
                        var=var,
                        ref_frequency=ref_frequency,
                        model=model,
                    )
                    echotype_sv = roi_sv.where(labels == cluster_id)

                    # Convert (time, depth) → obs
                    obs = (
                        echotype_sv
                        .stack(obs=("time", "depth"))
                        .dropna("obs", how='all')
                    )

                    # Raise error if echotype is empty
                    n_obs = obs.sizes["obs"]
                    if n_obs == 0:
                        raise ValueError("No data in echotype")

                    # Assign echotype coordinate (references obs dimension)
                    obs = obs.assign_coords(
                        echotype=("obs", np.full(n_obs, i))
                    )

                    # Add to echotypes list
                    obs_sv_list.append(obs)

                    # Append metadata lists
                    echotype_ids.append(echotype_id)
                    shape_ids.append(shape_id)
                    cluster_ids.append(cluster_id)
                    clustering_methods.append(echotype_data["clustering_method"])

                except Exception as e:
                    print(f"Failed to fetch echotype {echotype_id} (shape id: {shape_id}): {e}")

        if not obs_sv_list:
            raise ValueError("No echotypes exported")

        # Concatenate observations
        all_obs = xr.concat(obs_sv_list, dim="obs")

        # Reset MultiIndex so NetCDF can serialize it
        all_obs = all_obs.reset_index("obs")

        # Build dataset
        export_ds = xr.Dataset(
            data_vars={
                "Sv": all_obs,

                "echotype_id": ("echotype", echotype_ids),
                "shape_id": ("echotype", shape_ids),
                "cluster_id": ("echotype", cluster_ids),
                "clustering_method": ("echotype", clustering_methods),
            },
            attrs={
                "echotype_library_name": echotypes_libname,
                "ei_id": ei_meta.get("registry_id"),
                "cruise_name": ei_meta.get("cruise_name"),
                "description": "Sparse echotype Sv observations"
            },
        )

        return dcc.send_bytes(
            export_ds.to_netcdf,
            filename=f"{echotypes_libname}.nc",
        )


# Helper function
def get_roi_mask(app, shape_data: dict) -> xr.DataArray:
    """Server-side caching of ROI mask. The mask is a boolean DataArray

    Args:
        shape_data (dict): selected ROI registry info.
    """

    # No ROI selected: clear cache and do nothing
    if not shape_data:
        app.cache.clear_roi_mask()
        return 

    # Fetch acoustic dataset from app cache
    ds: xr.Dataset = app.cache.get_dataset()
    if ds is None:
        raise ValueError(f"No dataset available in app cache. {app.cache = }")
    sv: xr.DataArray = ds["Sv"]
    
    # Fetch ROI info
    xmin, _, ymin, _ = (bbox := shape_data['bbox'])
    shape_type = shape_data['shape_type']
    shape_points = shape_data['points']
    
    # Lazy-load and process Sv data
    bbox_sv = proc.preprocess_sv(sv, window=bbox)
    shape_points = proc.offset_points(shape_points, xmin, ymin)

    # Compute mask
    roi_mask = proc.get_roi_mask(bbox_sv, shape_type, shape_points)
    
    # Add a bbox attribute to indicate the position of the mask in the global DataArray
    roi_mask = roi_mask.assign_attrs(bbox=bbox)

    return roi_mask