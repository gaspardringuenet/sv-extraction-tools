from dash import Dash
from flask import Flask

from importlib.resources import files
from pathlib import Path
from typing import Literal, Optional
import xarray as xr

from ..config import _validate_root_path

from .layout.main import make_layout
from .callbacks import *

class EchotypesApp(Dash):

    def __init__(self, **kwargs):

        # inherit from the Dash class
        super().__init__(
            assets_folder = Path(__file__).parent / "assets",
            external_stylesheets=["https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css"],
            server=Flask('EchotypesApp')
        )

        # create an specific app config object
        self.app_config = EchotypesAppConfig(**kwargs)

        # create cache dictionary (avoids reloading DataArrays all the time)
        self.cache = AppCache()

        # define app layout
        self.layout = make_layout()

        # define callbacks
        self._register_callbacks()


    def _register_callbacks(self):

        # callbacks for the session control panel (top-left)
        register_callbacks_session_controls(self, self.app_config.registry, self.app_config.root)

        # callbacks for the AgGrid (top-right)
        register_callbacks_selection_table(self, self.app_config.registry, self.app_config.root)

        # callbacks for the ROI / echo-type visualization row (middle row)
        register_visualization_callbacks(self, self.app_config.registry, self.app_config.root)

        # callbacks for the clustering
        register_clustering_callbacks(self)

        # callbacks for saving the echo-types
        register_echotypes_saving_callbacks(self, self.app_config.registry, self.app_config.root)


class EchotypesAppConfig:

    def __init__(self, root: Path, registry: Path, output_dir: Path = None):

        self.root = _validate_root_path(root)
        self.registry = registry

        self.output_dir = output_dir or root / "app_data/echotypes"
        self.output_dir.mkdir(parents=True, exist_ok=True)


class AppCache:

    def __init__(self):

        # Main dataset
        self.echointegrated_dataset: Optional[xr.Dataset] = None

        # ROI mask
        self.roi_mask: Optional[xr.DataArray] = None

        # Labels DataArray
        self.labels: Optional[xr.DataArray] = None

        # Clustering models
        self.clustering_models = {
            "saved": None,
            "current": None,
        }

    # Echointegrated dataset
    def set_dataset(self, ds: xr.Dataset):
        self.echointegrated_dataset = ds

    def get_dataset(self) -> Optional[xr.Dataset]:
        return self.echointegrated_dataset

    def clear_dataset(self):
        self.echointegrated_dataset = None

    # ROI mask
    def set_roi_mask(self, da: xr.DataArray):
        self.roi_mask = da

    def get_roi_mask(self) -> Optional[xr.DataArray]:
        return self.roi_mask

    def clear_roi_mask(self):
        self.roi_mask = None

    # Labels
    def set_labels(self, da: xr.DataArray):
        self.labels = da

    def get_labels(self) -> Optional[xr.DataArray]:
        return self.labels

    def clear_labels(self):
        self.labels = None 

    # Clustering models
    def set_clustering_model(self, model, domain: Literal["saved", "current"]):
        self.clustering_models[domain] = model

    def get_clustering_model(self, domain: Literal["saved", "current"]):
        return self.clustering_models[domain]

    def clear_clustering_model(self, domain: Literal["saved", "current", "both"]):

        if domain == "both":
            self.clustering_models["saved"] = None
            self.clustering_models["current"] = None
        else:
            self.clustering_models[domain] = None

    # Clear everything
    def clear(self):
        self.clear_dataset()
        self.clear_roi_mask()
        self.clear_clustering_model("both")
    