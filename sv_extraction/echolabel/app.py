import glob
import os
from pathlib import Path
import subprocess
from typing import Sequence
import xarray

from .dataloader import load_dataset
from .builder import build_survey_images
from .config import *
from ..registry.labelme.parser import add_shape_ids
from ..registry import Registry

class EcholabelApp:
    """An app to label multifrequency volume backscattering echograms using Labelme.

    Attributes
    ----------
    config: EcholabelAppConfig
        configuration parameters

    Methods
    -------
    run(force_rebuild_images=False):
        runs the app

    """

    def __init__(
        self,
        input: str | Path,
        libname: str,
        frequencies: float | Sequence[float],
        echogram_cmap: str,
        root: str | Path = os.getcwd(),
        registry: str | Path = None,
        time_frame_size: int = 10_000,
        z_min_idx: int = 0,
        z_max_idx: int = -1,
        vmin: float = -90.,
        vmax: float = -50.,
        xarray_chunking: dict = None
    ) -> EcholabelAppConfig:
        """Builds app configuration.

        Parameters
        ----------
        input : str | Path
            path to a volume backscattering (Sv) netCDF file, or input folder containing several such files (for the same cruise)
        libname : str
            name of the shapes library to create / append using the EcholabelApp
        frequencies : float | Sequence[float]
            frequencies to map on echogram images
        echogram_cmap : str
            colormap for echogram images
        root : str | Path, optional
            path to project root used to compute app output paths, by default os.getcwd()
        registry : str | Path, optional
            path to the registry .db file, by default None
        time_frame_size : int, optional
            width of echogram images in number of ping axis units, by default 10_000
        z_min_idx : int, optional
            index of the upper (shallower) bound of echogram images in the depth axis, by default 0
        z_max_idx : int, optional
            index of the lower (deeper) bound of echogram images in the depth axis, by default -1
        vmin : float, optional
            minimal volume backscattering value for color mapping (in dB), by default -90.
        vmax : float, optional
            maximal volume backscattering value for color mapping (in dB), by default -50.
        xarray_chunking : dict, optional
            chunk arguments for lazy loading with xarray (e.g., {'time': 10_000, 'depth': 100}), by default None

        Returns
        -------
        EcholabelAppConfig
            the EcholabelApp configuration object, containing namely paths, image printing parameters, and labelling session info
        """

        self.config = build_app_config(
            input,
            libname,
            root,
            registry,
            time_frame_size,
            z_min_idx,
            z_max_idx,
            vmin,
            vmax,
            frequencies,
            echogram_cmap,
            xarray_chunking
        )
    
    def run(self, force_rebuild_images: bool=False) -> None:
        """Runs the app by printing out echogram images and embedding Labelme.

        Parameters
        ----------
        force_rebuild_images : bool, optional
            whether to print out the echogram images even some already exist for this configuration, by default False
        """

        # Load data, register in db and get id
        dataset = load_dataset(path=self.config.paths.input, chunks=self.config.loading.chunks)

        # Build Image Dataset
        build_images(dataset, self.config, force_rebuild_images)

        # Sync library by importing JSON files from another image folder (having the same EI; if it exists)
        sync_library(self.config, flow="down")

        # Run LABELME and fetch session id
        run_labelling_session(self.config)

        # Add tracking infos to JSON outputs (add id's and update geometry hash)
        add_shape_ids(self.config.json_dir(), self.config.session.session_id)

        # Update registry
        update_registry(self.config)

        # Sync library by exporting JSON files to all other image folders (for the same EI)
        sync_library(self.config, flow="up")



# ---- Helper functions ---- #

def build_app_config(
    input: str | Path,
    libname: str,
    root: str | Path = os.getcwd(),
    registry: str | Path = None,
    time_frame_size: int = 10_000,
    z_min_idx: int = 0,
    z_max_idx: int = -1,
    vmin: float = -90.,
    vmax: float = -50.,
    frequencies: float | Sequence[float] = None,
    echogram_cmap: str = None,
    xarray_chunking: dict = None
) -> EcholabelAppConfig:
    """
    Build Echolabel App Config object
    """
    # Build paths config object (auto formats / validates on class init)
    paths_config = EcholabelPathsConfig(input, root, registry)
    paths_config.make_app_dirs()

    # Build data loading config object (use only to store chunking)
    loading_config = DataLoadingConfig(chunks=xarray_chunking)
    
    # Load data, register in db and get id
    dataset = load_dataset(path=paths_config.input, chunks=loading_config.chunks)
    ei_id = get_or_register_ei(paths_config.registry, paths_config.root, paths_config.input, dataset)

    # Build image data config object
    image_data_config = ImageDataConfig(
        cruise_name=dataset.attrs.get('cruise_name', 'NameNotFound'),
        ei_id=ei_id,
        echogram_images_dir=paths_config.images,
        time_frame_size=time_frame_size,
        z_min_idx=z_min_idx,
        z_max_idx=z_max_idx,
        vmin=vmin,
        vmax=vmax,
        frequencies=frequencies,
        echogram_cmap=echogram_cmap
    )

    # Register image dataset in db and get it
    image_dataset_id = get_or_register_image_dataset(paths_config.registry, paths_config.root, image_data_config)

    # Build session config object
    session_config = LabellingSessionConfig(image_dataset_id, libname)

    # Build App config object
    app_config = EcholabelAppConfig(paths_config, loading_config, image_data_config, session_config)

    return app_config


def get_or_register_ei(registry_file: Path, here: Path, input_dir: Path, ds: xarray.Dataset):
    """Ensures registry schema, registers the echointegration associated to input_dir
    (if it does not already exist in registry) and returns the row id in the echointegrations
    table.
    """
    files = glob.glob(str(input_dir / "*.nc"))
    with Registry(db_path=registry_file, root_path=here) as registry:
        ei_id = registry.ei.insert_row(ds, files)
        registry.conn.commit()
    return ei_id

        
def get_or_register_image_dataset(registry_file, here, cfg: ImageDataConfig):
    """Registers the image dataset associated to the configuration object (if it does not already
    exist in registry) and returns the row id in the image_datasets table.
    """
    with Registry(db_path=registry_file, root_path=here) as reg:
        id = reg.images.insert_row(cfg)
        reg.conn.commit()
    return id


def build_images(dataset: xarray.Dataset, app_config: EcholabelAppConfig, force_rebuild_images: bool):
    """Prints out the echogram as a series of .png images.
    """
    image_files = glob.glob(str(app_config.image_data.save_dir / "*.png"))
    empty_save_dir = len(image_files) == 0

    if empty_save_dir or force_rebuild_images:
        statement = "Overwriting previous images..." if force_rebuild_images else "Building new images..."
        print(statement)
        build_survey_images(**app_config.image_data.__dict__, sv=dataset["Sv"])


def sync_library(app_config: EcholabelAppConfig, flow: str):
    """Synchronizes the annotatino subfolders for a given library. Allows the user to see the library's
    shapes in labelme, even when changing the image dataset (for the same echointegration).
    """
    with Registry(app_config.paths.registry, app_config.paths.root) as registry:

        if flow == 'up':
            registry.shapes.sync_library_up(app_config.session.image_dataset_id, library=app_config.session.libname)
        elif flow == 'down':
            registry.shapes.sync_library_down(app_config.session.image_dataset_id, library=app_config.session.libname)
        else:
            raise ValueError(f"flow parameter must be one of 'up' or 'down'. {flow} given.")           


def run_labelling_session(app_config: EcholabelAppConfig):
    """Helper to run LABELME on pre-printed echogram images.
    """

    ei_info = get_ei_metadata(app_config.paths.registry, app_config.paths.root, app_config.image_data.ei_id)

    #print(f"\n==== Echogram labelling session ====\n")
    print("Echogram labelling session")
    print(f" - Id:\t\t{app_config.session.session_id}")
    print(f" - Name:\t{app_config.session.libname}")
    print(f" - Cruise:\t{app_config.image_data.cruise_name}")
    print(f" - EI:\t\t{ei_info.get('data_ping_axis_interval_value')} {ei_info.get('data_ping_axis_interval_type')} x {ei_info.get('data_range_axis_interval_value')} {ei_info.get('data_range_axis_interval_type')} (EI id {app_config.image_data.ei_id})")
    print(f" - Images:\t{app_config.image_data.save_dir}")

    log_file = app_config.paths.app_data / "labelme.log"
    
    with open(log_file, 'w') as log:
        subprocess.run(
            [                                        # launch labelme as subprocess
                "labelme",
                str(app_config.image_data.save_dir),
                '--output',
                str(app_config.json_dir()),
                #'--nodata'                                          # avoids encoding the image in the json file
            ],
            stdout=log,
            stderr=log
        )

    #print("\n====================================")


def get_ei_metadata(db_path: Path, root_path: Path, ei_id: int) -> dict:
    """Fetches echointegration metadata from the registry.
    """

    with Registry(db_path, root_path) as registry:
        ei_info = registry.ei.get(id=ei_id)
    return ei_info


def update_registry(app_config: EcholabelAppConfig):
    """Updates db using labelme outputs (.json files).
    """
    print(f"\nUpdating shapes registry file at: {app_config.paths.registry}")

    with Registry(app_config.paths.registry, app_config.paths.root) as registry:
        registry.shapes.sync_db_from_jsons(
            json_dir=app_config.json_dir(),
            ei_id=app_config.image_data.ei_id, 
            library=app_config.session.libname
        )
        registry.conn.commit()