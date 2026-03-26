from dash import Dash, Output, Input, State

from pathlib import Path
from typing import Tuple, Literal

from ...registry import Registry

def register_echotypes_saving_callbacks(app: Dash, db_path: Path, root_path: Path) -> None:

    @app.callback(
        Output('update-aggrid-flag', 'data', allow_duplicate=True),
        Output('echotype-mode', 'value', allow_duplicate=True),
        Input('echotype-save-button', 'n_clicks'),
        State('echotype-mode', 'value'),
        State('selected-roi', 'data'),
        State('selected-echotype', 'data'),
        State('select-echotype-lib', 'value'),
        State('current-clustering-params', 'data'),
        State('cluster-id', 'value'),
        prevent_initial_call=True
    )
    def add_echotype_to_db(
        _, 
        mode: Literal["edit", "new"], 
        selected_roi_data: dict, 
        selected_echotype_data: dict,
        echotype_libname: str, 
        clustering_params: dict, 
        cluster_id: int
    ) -> Tuple[int, str]:
        
        # Fetch echotype library name from selector
        if not echotype_libname:
            raise ValueError("No echotype library provided.")
        if not clustering_params:
            raise ValueError("No clustering params found in Dash store component.")
        
        # Fetch info from Dash cache
        if not selected_roi_data:
            raise ValueError(f"No ROI data in store for export. {selected_roi_data = }")
        
        shape_id = selected_roi_data.get("id")
        method = clustering_params.get("method")
        features = clustering_params.get("features")
        
        # Fetch clustering model from custom app cache
        model = app.cache.get_clustering_model(domain="current")

        # Insert new echotype in registry
        if mode == "new":
            with Registry(db_path, root_path) as registry:
                echotype_id = registry.echotypes.insert(
                    echotypes_libname=echotype_libname,
                    shape_id=shape_id,
                    features=features,
                    method=method,
                    fitted_model=model,
                    cluster_id=cluster_id
                )
                registry.conn.commit()

            return echotype_id, "inspect"

        # Edit echotype fields in registry    
        elif mode == "edit":
            
            if not isinstance(selected_echotype_data, dict):
                raise ValueError(f"Invalid echotype data in store for editing. {selected_roi_data = }")
            
            echotype_id = selected_echotype_data.get("id")
            if echotype_id is None:
                raise ValueError(f"No echotype id in store for editing. {selected_roi_data = }")

            with Registry(db_path, root_path) as registry:
                registry.echotypes.update(
                    echotype_id=echotype_id,
                    features=features,
                    method=method,
                    fitted_model=model,
                    cluster_id=cluster_id
                )
                registry.conn.commit()

        else:
            raise ValueError(f"Unsupported echotype mode: {mode}")

        return echotype_id, 'inspect'
    

    @app.callback(
        Output('update-aggrid-flag', 'data', allow_duplicate=True),
        Input('echotype-delete-button', 'n_clicks'),
        State('selected-echotype', 'data'),
        prevent_initial_call=True
    )
    def delete_echotype_from_db(_, selected_echotype_data: dict) -> int:

        echotype_id = selected_echotype_data.get("id")

        if echotype_id is None:
            return

        with Registry(db_path, root_path) as registry:
            registry.echotypes.delete(id=echotype_id)
            registry.conn.commit()
        
        return echotype_id