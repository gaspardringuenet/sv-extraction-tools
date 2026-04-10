import glob
import logging
from pathlib import Path
import subprocess
from rich.console import Console
from rich.panel import Panel
from typing import Sequence
import xarray

from ..config import GlobalConfig
from .dataloader import load_dataset
from .builder import build_survey_images
from .config import *
from ..registry.labelme.parser import add_shape_ids
from ..registry import Registry
from ..utils.cache import cache_cleanup

logger = logging.getLogger(__name__)
class LabelmeWrapper:
    """An app to label multifrequency volume backscattering echograms using Labelme.

    Attributes
    ----------
    config: LabelConfig
        configuration parameters

    Methods
    -------
    run(force_rebuild_images=False):
        runs the app

    """

    def __init__(
        self,
        global_config: GlobalConfig,
        input: str | Path,
        libname: str,
        frequencies: float | Sequence[float],
        echogram_cmap: str,
        time_frame_size: int = 10_000,
        z_min_idx: int = 0,
        z_max_idx: int = -1,
        vmin: float = -90.,
        vmax: float = -50.,
        xarray_chunking: dict = None
    ):
        """Builds app configuration.

        Parameters
        ----------
        global_config: GlobalConfig
            global configuration object for echolabel
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
        """

        self.config = build_config(
            global_config=global_config,
            input=input,
            libname=libname,
            time_frame_size=time_frame_size,
            z_min_idx=z_min_idx,
            z_max_idx=z_max_idx,
            vmin=vmin,
            vmax=vmax,
            frequencies=frequencies,
            echogram_cmap=echogram_cmap,
            xarray_chunking=xarray_chunking
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

        # Run LABELME as subprocess
        run_labelling_session(self.config)

        # Add tracking infos to JSON outputs (add id's and update geometry hash)
        add_shape_ids(self.config.json_dir(), self.config.session.session_id)

        # Update registry
        update_registry(self.config)

        # Sync library by exporting JSON files to all other image folders (for the same EI)
        sync_library(self.config, flow="up")

        # Cleanup of the database and cache files (if EI has no shapes)
        cache_cleanup(self.config.paths.registry, self.config.paths.cache)


# ---- Helper functions ---- #

def build_config(
    global_config: GlobalConfig,
    input: str | Path,
    libname: str,
    time_frame_size: int = 10_000,
    z_min_idx: int = 0,
    z_max_idx: int = -1,
    vmin: float = -90.,
    vmax: float = -50.,
    frequencies: float | Sequence[float] = None,
    echogram_cmap: str = None,
    xarray_chunking: dict = None
) -> LabelConfig:
    """
    Build labelling app Config object
    """
    # Build paths config object (auto formats / validates on class init)
    paths_config = PathsConfig(input, global_config.cache, global_config.registry)

    # Build data loading config object (use only to store chunking)
    loading_config = DataLoadingConfig(chunks=xarray_chunking)
    
    # Load data, register in db and get id
    dataset = load_dataset(path=paths_config.input, chunks=loading_config.chunks)
    ei_id = get_or_register_ei(paths_config.registry, paths_config.cache, paths_config.input, dataset)

    # Check if libname already associated to another EI (if so error)
    if libname_conflict(paths_config.registry, paths_config.cache, libname, ei_id):
        raise ValueError("Library name already associated to another echointegration. Use another.")

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
    image_dataset_id = get_or_register_image_dataset(paths_config.registry, paths_config.cache, image_data_config)

    # Build session config object
    session_config = SessionConfig(image_dataset_id, libname)

    # Build App config object
    config = LabelConfig(paths_config, loading_config, image_data_config, session_config)

    return config


def get_or_register_ei(registry: Path, cache_dir: Path, input_path: Path, ds: xarray.Dataset):
    """Ensures registry schema, registers the echointegration associated to input (file or dir)
    (if it does not already exist in registry) and returns the row id in the echointegrations
    table.
    """

    if input_path.is_file():
        files = [str(input_path)]
    elif input_path.is_dir():
        files = glob.glob(str(input_path / "*.nc"))
    else:
        raise ValueError(f"Invalid input path - {input_path}")

    with Registry(registry, cache_dir) as registry:
        ei_id = registry.ei.insert_row(ds, files)
        registry.conn.commit()
    return ei_id


def libname_conflict(registry: Path, cache_dir: Path, libname: str, ei_id: int) -> True:
    """Check if shapes library name is associated to another echointegration
    Enforce that each libname is unique and references only one echointegration.
    """
    with Registry(registry, cache_dir) as registry:
        parent_ei_id = registry.get_ei_from_shapes_library(libname)
    
    no_conflict = ((not parent_ei_id) or (parent_ei_id == ei_id))
    conflict = not no_conflict

    if conflict:
        logger.debug(f"libname conflict: trying to use with echointegration {ei_id}"
                     f"while already associated to echointegration {parent_ei_id}")
    return conflict

        
def get_or_register_image_dataset(registry_file: Path, cache_dir: Path, img_config: ImageDataConfig):
    """Registers the image dataset associated to the configuration object (if it does not already
    exist in registry) and returns the row id in the image_datasets table.
    """
    with Registry(db_path=registry_file, root_path=cache_dir) as reg:
        id = reg.images.insert_row(img_config)
        reg.conn.commit()
    return id


def build_images(dataset: xarray.Dataset, config: LabelConfig, force_rebuild_images: bool):
    """Prints out the echogram as a series of .png images.
    """
    image_files = glob.glob(str(config.image_data.save_dir / "*.png"))
    empty_save_dir = len(image_files) == 0

    if empty_save_dir or force_rebuild_images:
        statement = "Overwriting previous images..." if force_rebuild_images else "Building new images..."
        logger.info(statement)
        build_survey_images(**config.image_data.__dict__, sv=dataset["Sv"])


def sync_library(config: LabelConfig, flow: str):
    """Synchronizes the annotatino subfolders for a given library. Allows the user to see the library's
    shapes in labelme, even when changing the image dataset (for the same echointegration).
    """
    with Registry(config.paths.registry, config.paths.cache) as registry:

        if flow == 'up':
            registry.shapes.sync_library_up(config.session.image_dataset_id, library=config.session.libname)
        elif flow == 'down':
            registry.shapes.sync_library_down(config.session.image_dataset_id, library=config.session.libname)
        else:
            raise ValueError(f"flow parameter must be one of 'up' or 'down'. {flow} given.")           


def run_labelling_session(config: LabelConfig):
    """Helper to run LABELME on pre-printed echogram images.
    """

    ei_info = get_ei_metadata(config.paths.registry, config.paths.cache, config.image_data.ei_id)

    console = Console()
    summary_str = (
        f" * Session id:\t\t{config.session.session_id}"
        f"\n * Library name:\t{config.session.libname}"
        f"\n * Cruise name:\t\t{config.image_data.cruise_name}"
        f"\n * Echointegration:\t{ei_info.get('data_ping_axis_interval_value')} {ei_info.get('data_ping_axis_interval_type')} x {ei_info.get('data_range_axis_interval_value')} {ei_info.get('data_range_axis_interval_type')} (EI id {config.image_data.ei_id})"
        f"\n * Folder in cache:\t{config.image_data.save_dir.relative_to(config.paths.cache)}"
    )

    panel = Panel(summary_str, title="Echogram labelling session")
    console.print(panel)


    log_file = config.paths.cache / "labelme.log"
    
    with open(log_file, 'w') as log:
        subprocess.run(
            [                                        # launch labelme as subprocess
                "labelme",
                str(config.image_data.save_dir),
                '--output',
                str(config.json_dir())
            ],
            stdout=log,
            stderr=log
        )


def get_ei_metadata(db_path: Path, cache_dir: Path, ei_id: int) -> dict:
    """Fetches echointegration metadata from the registry.
    """

    with Registry(db_path, cache_dir) as registry:
        ei_info = registry.ei.get(id=ei_id)
    return ei_info


def update_registry(config: LabelConfig):
    """Updates db using labelme outputs (.json files).
    """
    logger.info(f"Updating shapes registry file at: {config.paths.registry}")

    with Registry(config.paths.registry, config.paths.cache) as registry:
        registry.shapes.sync_db_from_jsons(
            json_dir=config.json_dir(),
            ei_id=config.image_data.ei_id, 
            library=config.session.libname
        )
        registry.conn.commit()