from dash import Dash, Output, Input, State, ctx
from dash.exceptions import PreventUpdate

import json
import plotly.express as px
import plotly.graph_objects as go
from typing import Sequence, Tuple, List, Literal
import xarray as xr

from ..core import figures as figtools
from ..core import processing as proc


_MODE_CONFIGS = {
    "inspect": {
        "save_disabled":        True,
        "delete_disabled":      False,
        "method_disabled":      True,
        "var_disabled":         True,
        "n_clusters_disabled":  True,
        "ref_freq_disabled":    True,
        "cluster_id_disabled":  True,
    },
    "edit": {
        "save_disabled":        False,
        "delete_disabled":      False,
        "method_disabled":      False,
        "var_disabled":         False,
        "n_clusters_disabled":  False,
        "ref_freq_disabled":    False,
        "cluster_id_disabled":  False,
    },
    "new": {
        "save_disabled":        False,
        "delete_disabled":      True,
        "method_disabled":      False,
        "var_disabled":         False,
        "n_clusters_disabled":  False,
        "ref_freq_disabled":    False,
        "cluster_id_disabled":  False,
    },
}

_MODE_DEFAULT_VALUES = {
    "method":       "KMeans",
    "var":          json.dumps({"name": "Sv"}),
    "n_clusters":   1,
    "cluster_id":   0,
}


def register_clustering_callbacks(app: Dash) -> None:

    def get_roi_sv():
        # Fetch acoustic dataset from app cache
        ds: xr.Dataset = app.cache.get_dataset()
        if ds is None:
            raise ValueError(f"No dataset available in app cache. {app.cache.summary() = }")
        
        # Fetch ROI mask from cache
        roi_mask: xr.DataArray = app.cache.get_roi_mask()
        if roi_mask is None:
            raise ValueError(f"No ROI mask available in app cache. {app.cache.summary() = }")

        # Select ROI Sv
        bbox_sv = proc.preprocess_sv(ds.Sv, window=roi_mask.attrs.get('bbox'))
        roi_sv = bbox_sv.where(roi_mask)

        return roi_sv
    
    @app.callback(
        Output('clustering-var', 'options'),
        Input('ei-metadata', 'data')
    )
    def update_clustering_var_labels(ei_meta: dict):

        sv_opt = {'label': 'Sv', 'value': json.dumps({'name': 'Sv'})}

        delta_sv_opts = [
            {
                'label': f'ΔSv {int(ref_freq)} kHz', 
                'value': json.dumps({'name': 'delta_Sv', 'ref': ref_freq})
            }
            for ref_freq in sorted(ei_meta['channels'])
            ]

        return [sv_opt] + delta_sv_opts


    @app.callback(
        Output('echotype-mode', 'value', allow_duplicate=True),

        Output('echotype-save-button', 'disabled'),
        Output('echotype-delete-button', 'disabled'),

        Output('clustering-method', 'value'),
        Output('clustering-var', 'value'),
        Output('clustering-channels-checklist', 'value', allow_duplicate=True),
        Output('clustering-n-clusters', 'value'),
        Output('cluster-id', 'value', allow_duplicate=True),

        Output('clustering-method', 'disabled'),
        Output('clustering-var', 'disabled'),
        Output('clustering-n-clusters', 'disabled'),
        Output('cluster-id', 'disabled'),

        Output('clustering-channels-checklist', 'options', allow_duplicate=True),
        Output('clustering-channels-checklist', 'style'),
        
        Input('echotype-mode', 'value'),
        Input('selected-echotype', 'data'),
        Input('clustering-channels-checklist', 'options'),
        State('clustering-channels-checklist', 'style'),

        prevent_initial_call=True
    )
    def apply_echotyping_mode(
        mode: Literal["inspect", "edit", "new"],
        selected_echotype_data: dict,
        freqs_opts: List[float],
        freqs_style: dict,
    ) -> Tuple[bool]:
        
        if not freqs_opts:
            raise PreventUpdate
        
        def set_disabled_checklist(opts: List, disabled: bool = True) -> List[dict]:
            if not isinstance(opts, list) or not opts:
                raise ValueError(f"Invalid checklist options: {opts = }")
            
            new_opts = []

            for opt in opts:
                if isinstance(opt, dict):
                    new_opt = opt.copy()
                    new_opt["disabled"] = disabled

                elif isinstance(opt, (int, float)):
                    new_opt = {
                        "label": opt,
                        "value": opt,
                        "disabled": disabled
                    }

                else:
                    raise ValueError(f"Unsupported checklist option type: {type(opt)} ({opt})")

                new_opts.append(new_opt)

            return new_opts

        def set_disabled_style_checklist(style: dict, disabled: bool = True) -> dict:
            
            new_style = {**(style or {})}
            
            if disabled:
                new_style.update({
                    "opacity": "0.6",
                    "pointerEvents": "none"
                })

            else:
                new_style["opacity"] = "1"
                new_style.pop("pointerEvents", None)

            return new_style

        triggered = ctx.triggered_id

        if triggered == "echotype-mode":
            if mode not in _MODE_CONFIGS:
                raise ValueError(f"Unsupported echotype mode: {mode}")
            if mode != "new" and selected_echotype_data is None:
                mode = "new"
        else:
            mode = "inspect" if selected_echotype_data is not None else "new"

        # Disable controls
        # Fetch disabling config for most components
        cfg = _MODE_CONFIGS[mode]

        # Use helpers for checklist
        freqs_opts = set_disabled_checklist(freqs_opts, disabled=(mode=="inspect"))
        freqs_style = set_disabled_style_checklist(freqs_style, disabled=(mode=="inspect"))

        # Resolve control values
        if mode in ("inspect", "edit"):
            method       = selected_echotype_data["clustering_method"]
            var          = json.dumps(selected_echotype_data["clustering_features"]["var"])
            frequencies  = selected_echotype_data["clustering_features"]["frequencies"]
            cluster_id   = selected_echotype_data["cluster_id"]
            n_clusters   = (selected_echotype_data["clustering_params"].get("n_clusters") 
                            or selected_echotype_data["clustering_params"].get("n_components"))
        else:
            method       = _MODE_DEFAULT_VALUES["method"]
            var          = _MODE_DEFAULT_VALUES["var"]
            frequencies  = sorted([opt.get("value") for opt in freqs_opts])[:1] if freqs_opts else []
            n_clusters   = _MODE_DEFAULT_VALUES["n_clusters"]
            cluster_id   = _MODE_DEFAULT_VALUES["cluster_id"]

        return (
            mode,
            cfg["save_disabled"],
            cfg["delete_disabled"],
            method, var, frequencies, n_clusters, cluster_id,
            cfg["method_disabled"],
            cfg["var_disabled"],
            cfg["n_clusters_disabled"],
            cfg["cluster_id_disabled"],
            freqs_opts, freqs_style
        )


    @app.callback(
        Output('current-clustering-params', 'data'),

        Input('selected-roi', 'data'),
        Input('clustering-method', 'value'),
        Input('clustering-n-clusters', 'value'),
        Input('clustering-channels-checklist', 'value'),
        Input('clustering-var', 'value'),
    )
    def cluster_selected_roi(
        selected_roi_data: dict,
        method: str, 
        n_clusters: int, 
        frequencies: Sequence[float], 
        var: str,
    ) -> dict:
        """Perform a clustering of selected ROI and cache the results in a dcc.Store.

        Args:
            selected_roi_data (dict): Cached registry data of the selected ROI.
            method (str): Clustering method to use (one of 'KMeans', 'GaussianMixture').
            n_clusters (int): Number of clusters.
            frequencies (Sequence[float]): Frequency channels to use in clustering.
            TODO EDIT var (str): Acoustic variable to use in clustering (Sv or delta_Sv).

        Returns:
            dict: payload containing the label of each ROI pixel.
        """

        # No ROI selected: clear cache and do nothing
        if not selected_roi_data:
            app.cache.clear_labels()
            return None
        
        # Load the clustering variable (and if necessary the reference frequency)
        if not var:
            app.cache.clear_labels()
            return None
        var_dict = json.loads(var)
        var = var_dict.get("name")
        ref_frequency = var_dict.get("ref")
        
        # Load ROI Sv data and select frequencies for clustering
        roi_sv = get_roi_sv().sel(channel=frequencies)

        # Initalize model
        model = proc.init_model(method=method, n_clusters=n_clusters, random_state=42)

        # Perform clustering and fetch labels as DataArray & fitted model objects
        try:
            labels_da, model = proc.cluster_sv(
                sv=roi_sv, 
                var=var, 
                ref_frequency=ref_frequency, 
                model=model
            )
        except:
            # Typically when a frequency is all NA -> clustering cannot work with 0 samples
            app.cache.clear_labels()
            return None

        # Store to server cache (avoids sending big arrays to client)
        app.cache.set_labels(labels_da)
        app.cache.set_clustering_model(model, domain="current")

        # Dash store payload: use on echotype export to db + triggers callbacks
        payload = {
            "method": method,
            "features": {
                "var": var_dict,
                "frequencies": frequencies,
            }
        }

        return payload
    

    @app.callback(
        Output('clustering-figure', 'figure'),
        Input('current-clustering-params', 'data')
    )
    def update_clustering_fig(payload: dict) -> go.Figure:
        """Load cached ROI clustering result and display it as a heatmap.

        Args:
            payload (dict): Cached ROI clustering result (serialized xr.DataArray).

        Returns:
            go.Figure: (time, depth)-shaped heatmap of clustering predictions.
        """

        labels_da = app.cache.get_labels()

        if payload is None or labels_da is None:
            return figtools.empty_figure()

        fig = px.imshow(labels_da.transpose('depth', 'time'))

        return fig
    

    @app.callback(
        Output('cluster-id', 'max'),
        Output('cluster-id', 'value', allow_duplicate=True),
        Input('clustering-n-clusters', 'value'),
        Input('clustering-figure', 'clickData'),
        Input('cluster-id', 'value'),
        State('echotype-mode', 'value'),
        prevent_initial_call=True
    )
    def set_cluster_id(n: int, clickData: dict, i_prev: int, mode: str) -> Tuple[int, int]:
        """Prevent the user from inputing a cluster id value larger than the selected number of clusters (minus 1
        since the first cluster is cluster 0). Set the 'max' property of the cluster-id input to do so.
        """
        i_max = n - 1

        triggered = ctx.triggered_id
        if triggered == "clustering-figure" and clickData and mode != "inspect":
            i_new = clickData["points"][0]["z"]
        else:
            i_new = i_prev

        return i_max, min(i_new, i_max)
    

    @app.callback(
        Output('selected-figure', 'figure'),
        Output('left-out-figure', 'figure'),
        Input('cluster-id', 'value'),
        Input('viz-params', 'data'),
        Input('current-clustering-params', 'data'),
        prevent_initial_call=True
    )
    def update_selection_figs(cluster_id:int, viz_params: dict, _) -> Tuple[go.Figure, go.Figure]:
        """Create two echograms figures: one maps the selected cluster, while the other maps the left out pixels.

        Args:
            cluster_id (int): Selected cluster id.
            viz_params (dict): Visualization params used in main viz panel.
            _ (dict): Clustering labels dcc.Store data. Used only to trigger callback.

        Returns:
            Tuple[go.Figure, go.Figure]: One echogram with selected points only, and its complementary.
        """

        # Fetch data from app cache
        labels = app.cache.get_labels()
        ds = app.cache.get_dataset()

        # Handle absence of data
        if labels is None or ds is None:
            empty = figtools.empty_figure()
            return empty, empty
        
        # Load ROI Sv data
        sv = get_roi_sv()

        # Create a mask for the selected cluster
        mask = labels == cluster_id

        # Filter using mask 
        echotype_sv = sv.where(mask, drop=False)        # pixels in echotype
        left_out_sv = sv.where(~mask, drop=False)       # left-out pixels

        # Create figures (use the same viz params as main viz panel)
        echotype_fig = figtools.make_roi_fig(echotype_sv, **viz_params)
        left_out_fig = figtools.make_roi_fig(left_out_sv, **viz_params)

        return echotype_fig, left_out_fig
    

    @app.callback(
        Output('validation-figure', 'figure'),
        Input('cluster-id', 'value'),
        Input('current-clustering-params', 'data'),
        prevent_initial_call=True
    )
    def update_valid_figs(cluster_id, params_payload):

        # Defaults
        if not params_payload:
            return figtools.empty_figure()
        
        # Get available frequencies
        frequencies = params_payload["features"]["frequencies"]
        ref_frequency = params_payload["features"]["var"].get("ref")
        if ref_frequency is None:
            ref_frequency = 38 if 38 in frequencies else (frequencies[0] if frequencies else None)

        # Get data from cache
        roi_sv = get_roi_sv()
        labels_da = app.cache.get_labels()

        if labels_da is None:
            raise ValueError(f"No clustering labels in app cache. {app.cache.summary() = }")

        # Select echotype points & compute delta Sv
        echotype_sv = roi_sv.where(labels_da == cluster_id)

        # Create figure
        fig = figtools.make_validation_plots(echotype_sv, frequencies, ref_frequency)

        return fig