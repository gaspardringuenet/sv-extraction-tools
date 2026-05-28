"""Callbacks to animate the session control panel: selection of ROI library, selection/management of echo-types libraries...
"""

from dash import Dash, Input, Output, State, ctx

import json
from pathlib import Path
from typing import Tuple, List
import re

from ...registry import Registry
from ..core.io import load_dataset_from_files

DEBUG = False

def register_callbacks_session_controls(app: Dash, db_path: Path, root_path: Path):

    @app.callback(
        Output('roi-library', 'value'),
        Output('roi-library', 'options'),
        Input('url', 'pathname'),
    )
    def init_app(_) -> Tuple[str, List[str]]:
        """Initialize the app by setting up the ROI library dropdown.

        Returns:
            Tuple[str, List[str]]: Selected ROI library values and options.
        """

        with Registry(db_path, root_path) as registry:
            cur = registry.conn.execute('SELECT DISTINCT name FROM shapes_libraries;')
            rows = cur.fetchall()
       
        if not rows:
            return None, []
        
        roi_libraries = [dict(row)['name'] for row in rows]
        default_roi_library = roi_libraries[0]

        return default_roi_library, roi_libraries


    @app.callback(
        Output('ei-metadata', 'data'),
        Input('roi-library', 'value')
    )
    def cache_echointegration_data(roi_libname: str) -> dict:
        """Load and cache the xarray.Dataset's metadata based on selected ROI library.
        Cache the Dataset in server cache at the same time.

        Args:
            roi_libname (str): Name of the selected ROI library.

        Returns:
            dict: Payload containing registry ID, channels, dimensions, and echointegration attributes.
        """

        # Load dataset info from registry
        with Registry(db_path, root_path) as registry:
            ei_id = registry.get_ei_from_shapes_library(roi_libname)
            ei = registry.ei.get(ei_id)

        # Load dataset
        nc_files = [f for f in json.loads(ei["netcdf_files"])]
        ds = load_dataset_from_files(nc_files)

        # Cache dataset in server cache
        app.cache.set_dataset(ds)

        # Cache metadata in dcc.Store
        payload = {
            'registry_id': ei_id,
            'channels': list(ds['channel'].values),
            'time_size': int(ds['time'].size),
            'depth_size': int(ds['depth'].size),
            'cruise_name': ds.attrs.get('cruise_name'),
            'ping_axis_interval_value': ds.attrs.get('data_ping_axis_interval_value'),
            'ping_axis_interval_type': ds.attrs.get('data_ping_axis_interval_type'),
            'range_axis_interval_value': ds.attrs.get('data_range_axis_interval_value'),
            'range_axis_interval_type': ds.attrs.get('data_range_axis_interval_type'),
            'files': nc_files
        }

        return payload


    @app.callback(
        Output('clustering-channels-checklist', 'options', allow_duplicate=True),
        Output('clustering-channels-checklist', 'value'),
        Input('ei-metadata', 'data'),
        prevent_initial_call='initial_duplicate'
    )
    def update_clustering_channels(ei_meta: dict) -> Tuple[list, list, list, int]:
        """Look up the available data channels and update session controls.

        Args:
            ei_meta (dict): echointegration metadata (extracted from the input).

        Raises:
            ValueError: If 'channels' contains no element.

        Returns:
            Tuple[list, list, list, int]: session level channels cheklist and reference channel dropdown parameters.
        """

        channels = ei_meta.get("channels")

        if channels and isinstance(channels, list) and len(channels) >= 1:
            return (
                [{'label': int(value), 'value': value} for value in channels],
                [],
            )
        else:
            raise ValueError("No 'channel' dimension in echointegrated data.")
        

    @app.callback(
        Output('session-info-text', 'children'),
        Input('roi-library', 'value'),
        Input('ei-metadata', 'data'),
    )
    def update_session_info(roi_libname: str, ei_meta: dict) -> str:
        """Provide information to the user regarding selected ROI library, and the associated dataset.

        Args:
            roi_libname (str): Name of the ROI library, selected in dropdown from the registry's shapes table (library attribute).
            ei_meta (dict):  Echointegration metadata (extracted from the data files which depend on the ROI library).

        Returns:
            str: Summary of selected data for the User.
        """        

        session_info_text = f"""
            ROI library `{roi_libname}` for selected echo-types extraction. This library was labelled on the acoustic data from the `{ei_meta.get('cruise_name')}`
            cruise, with echointegration parameters `{ei_meta.get('ping_axis_interval_value')} {ei_meta.get('ping_axis_interval_type')}` x
            `{ei_meta.get('range_axis_interval_value')} {ei_meta.get('range_axis_interval_type')}`. This dataset is stored
            in registry with id `{ei_meta.get('registry_id')}`.
        """

        return session_info_text


    @app.callback(
        Output('echotype-library-input', 'disabled'),
        Output('echotype-library-add', 'disabled'),
        Output('echotype-library-exit', 'disabled'),
        Output('library-creation-block', 'style'),
        Output('echotype-library-input', 'style'),
        Output('echotype-library-input', 'value'),
        Output('select-echotype-lib', 'options'),

        State('echotype-library-input', 'value'),
        State('echotype-library-input', 'pattern'),
        Input('roi-library', 'value'),
        State('select-echotype-lib', 'options'),
        State('select-echotype-lib', 'value'),
        Input('echotype-library-create-new', 'n_clicks'),
        Input('echotype-library-add', 'n_clicks'),
        Input('echotype-library-exit', 'n_clicks'),
        Input('echotype-library-delete', 'n_clicks')
    )
    def manage_echotype_libraries(
        echotypes_libname_input: str, 
        echotypes_libname_pattern: str, 
        roi_libname_selected: str, 
        echotypes_libname_opts: List[str],
        echotypes_libname_selected: str,
        *_
    ) -> Tuple[bool, bool, bool, dict, dict, str, List[str]]:

        triggered = ctx.triggered_id

        # Helper functions
        def get_opts() -> List[str]:
            """List echotypes library name from registry."""
            with Registry(db_path, root_path) as registry:
                return registry.echotypes.get_children_echotypes_libs(roi_libname_selected)
            return echotype_libname_opts
            
        def is_valid_input(text: str, opts: List[str]) -> bool:
            """Check user input validity."""
            if not text:
                return False
            valid_opt = text not in opts                           # input is new
            patt = re.compile(echotypes_libname_pattern)            # input matches string pattern
            valid_pattern = bool(patt.fullmatch(text))
            return valid_opt and valid_pattern
        
        def add_library(name: str, parent_name: str) -> int:
            """Add an echotypes library to registry using its name"""
            with Registry(db_path, root_path) as registry:
                lib_id = registry.echotypes.insert_echotypes_lib(name, parent_name)
                registry.conn.commit()
            return lib_id

        def delete_library(name: str) -> None:
            """Remove an echotypes library from registry and delete the associated file."""
            with Registry(db_path, root_path) as registry:
                registry.echotypes.delete_echotypes_lib(name)
                registry.conn.commit()     

        def return_state(creation_mode: bool=False, input_error: bool=False, input_val: str='', opts: List[str]=echotypes_libname_opts):
            """Return state in standard format."""

            DISABLED_STYLE = {'color': '#ccc'}
            ENABLED_STYLE = {'color': 'black'}
            ERROR_STYLE = {'border': '2px solid red', 'backgroundColor': '#ffe6e6'}
            VALID_STYLE = {}

            input_activation_style = ENABLED_STYLE if creation_mode else DISABLED_STYLE
            input_error_style = ERROR_STYLE if input_error else VALID_STYLE
            disabled = not creation_mode
            return disabled, disabled, disabled, input_activation_style, input_error_style, input_val, opts

        print(f"Correctly entered callback with {triggered = }") if DEBUG else _

        # DELETE
        if triggered == 'echotype-library-delete' and echotypes_libname_selected:
            delete_library(echotypes_libname_selected)
            return return_state(opts=get_opts())

        # CREATION MODE ('Create new library' button pressed)
        if triggered == 'echotype-library-create-new':
            return return_state(creation_mode=True)

        # CREATION MODE OFF ('Exit' button pressed)
        if triggered == "echotype-library-exit":
            return return_state()
        
        # ADD
        if triggered == 'echotype-library-add':
            valid = is_valid_input(echotypes_libname_input, echotypes_libname_opts)
            if valid:
                print(f"Adding echotypes library '{echotypes_libname_input}' to registry...") if DEBUG else _
                echotypes_lib_id = add_library(echotypes_libname_input, roi_libname_selected)
                print(f"Added with id {echotypes_lib_id}") if DEBUG else _
                return return_state(opts=get_opts())
            return return_state(True, True, echotypes_libname_input, echotypes_libname_opts)                                                     

        # NO EVENT
        if triggered is None:
            opts = get_opts()
            input_val = echotypes_libname_input or ''
            valid = is_valid_input(input_val, opts)
            return return_state(False, valid, input_val, opts)
    
        # DEFAULT
        return return_state(opts=get_opts())