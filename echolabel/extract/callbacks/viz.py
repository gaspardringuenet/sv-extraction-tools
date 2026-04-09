from dash import Dash, Input, Output, State, ctx

from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
from typing import Tuple, List
import xarray as xr

from ..core import figures as figtools
from ..core import processing as proc

def register_visualization_callbacks(app: Dash, db_path: Path, root_path: Path):

    @app.callback(
        Output('roi-viz-mode', 'options'),
        Output('roi-viz-mode', 'value'),
        Output('roi-viz-frequencies', 'options'),
        Output('roi-viz-min-height', 'max'),
        Output('roi-viz-min-width', 'max'),
        Input('ei-metadata', 'data'),
    )
    def initialize_viz_controls(ei_meta: dict) -> Tuple[List[str], str, List[str], int, int]:
        """Initialize visualization controls based on the cached echointegration metadata.

        Args:
            ei_meta (dict): Echointegration metadata, extracted from the source netCDF file(s).

        Raises:
            ValueError: If no channels list is found.

        Returns:
            Tuple[List[str], str, List[str], int, int]: Values and options for the Dash components controling
            acoustic data visualization.
        """

        channels = ei_meta.get("channels")

        if channels is None or not isinstance(channels, list):
            raise ValueError(f"Acoustic dataset doesn't have any channels dimension or type is wrong: {channels = }")

        # Set the default mode (and options) depending on number of channels
        if len(channels) >= 3:
            mode = 'RGB'
            mode_opts = ['RGB', 'Single channel']
        else:
            mode = 'Single channel'
            mode_opts = ['Single channel']

        # Set the max width and height of the window to avoid overflowing dataset bounds
        max_height = ei_meta.get("depth_size")
        max_width = ei_meta.get("time_size")

        return (
            mode_opts,
            mode,
            channels,
            max_height,
            max_width
        )
    

    @app.callback(
        Output('roi-viz-frequencies', 'value'),
        Input('roi-viz-mode', 'value'),
        Input('roi-viz-frequencies', 'value'),
        Input('roi-viz-frequencies', 'options')
    )
    def enforce_viz_freqs_consistency(mode: str, freqs: List[float], opts: List[float]) -> List[float]:
        """Ensure that 1 channel (resp. 3 channels) is selected when mode is set to 'Single channel' (resp. 'RGB').
        If the last selected channel(s) correspond to the mode, they are kept.
        If not, the first channels in the echointegrated dataset are used.

        Args:
            mode (str): Selected visualization mode ('RGB' or 'Single channel').
            freqs (List[float]): Selected frequencies for color mapping.
            opts (List[float]): Available frequencies.

        Raises:
            ValueError: If the mode is none of 'RGB' or 'Single channel'.

        Returns:
            List[float]: Corrected selected frequencies for color mapping.
        """

        # When the callback is not triggered by user changing frequencies, ignore prev frequencies
        # This avoids using previously selected frequencies when changing ROI library (and thus possibly frequencies options)
        if 'roi-viz-frequencies.value' not in ctx.triggered_prop_ids:
            freqs = None

        if mode == 'RGB':
            if freqs is not None and (len(freqs) >= 3):
                new = freqs[-3:]
            else:
                new = opts[:3]
        
        elif mode == 'Single channel':
            if freqs is not None and (len(freqs) == 2): # only occurs when the previous state was 'Single channel'
                new = [freqs[-1]]   # Only allow one channel: pick the last selected
            else:
                new = [opts[0]]

        else:
            raise ValueError(f"mode should be one of 'RGB' or 'Single channel'. Got {mode} instead")
        
        return new
    
    
    @app.callback(
        Output('roi-viz-cmap', 'value'),
        Output('roi-viz-cmap', 'options'),
        Input('roi-viz-frequencies', 'value'),
        State('roi-viz-cmap', 'value')
    )
    def update_colormap_selector(frequencies: List[float], prev_cmap: str) -> Tuple[str, List[str]]:
        """Update the colormap dropdown based on selected frequencies in checklist.
        The checklist values are controlled by another callback to enforce consistency.
        When 3 frequencies are selected, a single RGB cmap is available (and selected).
        When 1 frequency is selected, all plotly express cmaps are available, and 'inferno' is selected,
        except if a cmap was already selected, in which case it is kept.
        By default, 'inferno' is selected.

        Args:
            frequencies (List[float]): Selected frequencies for color mapping.
            prev_cmap (str): Previously selected colormap. Avoids constantly switching back to default.

        Returns:
            Tuple[str, List[str]]: (value, options) for the dcc.DropDown.
        """

        defaults = {"value": "inferno", "options": px.colors.named_colorscales()}

        if (frequencies is None or not isinstance(frequencies, list)) and prev_cmap is None:
            return defaults["value"], defaults["options"]

        if len(frequencies) == 3:
            value = 'RGB'
            l = frequencies.copy()
            l.sort()
            label = f'RGB - {l[0], l[1], l[2]} [kHz]'
            options = [{'label':label, 'value':value}]

        else:
            options = defaults['options']
            value = prev_cmap if prev_cmap in options else defaults['value']

        return value, options
    

    @app.callback(
        Output('roi-figure', 'figure'),
        Output('roi-viz-min-width', 'value'),
        Output('roi-viz-min-height', 'value'),
        Output('viz-params', 'data'),

        Input('selected-roi', 'data'),
        Input('roi-viz-frequencies', 'value'),
        Input('roi-viz-cmap', 'value'),
        Input('roi-viz-db-slider', 'value'),
        Input('roi-viz-min-width', 'value'),
        Input('roi-viz-min-height', 'value'),

        State('ei-metadata', 'data'),
        State('roi-viz-min-width', 'min'),
        State('roi-viz-min-height', 'min'),
    )
    def update_roi_figure(
        selected_roi_data: dict,
        frequencies: List[float], 
        cmap: str, 
        sv_range: Tuple[int, int], 
        min_width: int, 
        min_height: int,
        ei_meta: dict, 
        min_width_default: int, 
        min_height_default: int
    ) -> Tuple[go.Figure, int, int, dict]:   
        """Create an echogram showing a window embedding the selected ROI.

        Args:
            selected_roi_data (str): Cached registry data of the selected ROI.
            frequencies (List[float]): Frequencies to map.
            cmap (str): Colormap ('RGB' or one of px.colors.named_colorscales()).
            sv_range (Tuple[int, int]): Min and max values of Sv for color mapping.
            min_width (int): User input minimum window width.
            min_height (int): User input minimum window height.
            ei_meta (dict): Cached metadata of the source acoustic data (incl. files).
            min_width_default (int): Minimal limit of the minimum window width selector.
            min_height_default (int): Maximal limit of the minimum window height selector.

        Returns:
            Tuple[go.Figure, int, int, dict]: Echogram figure with ROI drawn on top; updated window width/height values;
                Visualization params to cache.
        """

        if not selected_roi_data:
            return figtools.empty_figure(), min_width_default, min_height_default, {}
        
        triggered = ctx.triggered_id

        # On ROI change - switch back to default min height / width
        if triggered == 'selected-roi':
            min_height = min_height_default
            min_width = min_width_default

        # Create a window around ROI (safe means it cannot overflow dataset bounds)
        win = proc.get_window_safe_2d(
            bbox=selected_roi_data['bbox'], 
            array_shape=(ei_meta['time_size'], ei_meta['depth_size']),
            min_height=min_height,
            min_width=min_width,
            min_padding=50
        )

        # Update height / width values
        min_height = win[3] - win[2] + 1
        min_width = win[1] - win[0] + 1

        # Load data
        ds: xr.Dataset = app.cache.get_dataset()
        if ds is None:
            raise ValueError(f"No dataset available in app cache. {app.cache.summary() = }")
        sv: xr.DataArray = ds["Sv"]

        # Slice and ensure H, W, C shape
        sv = proc.preprocess_sv(sv, win, frequencies)

        # points to window coordinates
        points = proc.offset_points(selected_roi_data['points'], xmin=win[0], ymin=win[2])

        # plot Sv data and ROI shape #TODO: handle specific shape types
        fig = figtools.make_roi_fig(sv, cmap, frequencies, sv_range, selected_roi_data['shape_type'], points)

        # store vizualization params
        viz_params_payload = {
            "cmap": cmap,
            "frequencies": frequencies,
            "sv_range": sv_range
        }
        
        return fig, min_width, min_height, viz_params_payload
    

    @app.callback(
        Output('echotype-figure', 'figure'),
        Input('selected-echotype', 'data'),
        Input('viz-params', 'data'),
    )
    def update_echotypes_figure(
        selected_echotype_data: dict,
        viz_params: dict
    ) -> go.Figure:
        #TODO TEST & COMMENT

        if not selected_echotype_data:
            return figtools.empty_figure()
        
        # Load echotype registry info from Dash cash
        var = selected_echotype_data["clustering_features"]["var"]["name"]
        ref_frequency = selected_echotype_data["clustering_features"]["var"].get("ref")
        frequencies = selected_echotype_data["clustering_features"]["frequencies"]
        cluster_id = selected_echotype_data["cluster_id"]

        # Load data from custom app cache
        ds: xr.Dataset = app.cache.get_dataset()                        # Dataset
        roi_mask: xr.DataArray = app.cache.get_roi_mask()               # ROI mask
        saved_model = app.cache.get_clustering_model(domain="saved")    # Clustering models

        if any([ds, roi_mask, saved_model]) is None:
            raise ValueError(f"Missing cache for echotype plot. {app.cache.summary() = }")
        
        # Pre-processing: get ROI Sv
        bbox_sv = proc.preprocess_sv(ds.Sv, window=roi_mask.attrs.get('bbox'))
        roi_sv = bbox_sv.where(roi_mask)

        # Cluster ROI Sv using saved model
        labels, _ = proc.cluster_sv(
            sv=roi_sv.sel(channel=frequencies), 
            var=var,
            ref_frequency=ref_frequency,
            model=saved_model
            )
        
        # Select with registry cluster id 
        echotype_sv = roi_sv.where(labels == cluster_id)

        # Build figure with selected viz params
        fig = figtools.make_roi_fig(echotype_sv, **viz_params)

        return fig