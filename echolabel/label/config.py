import os
from datetime import datetime
from pathlib import Path
from typing import Sequence

# ---- Configuration classes ----

class PathsConfig():
    def __init__(
        self,
        input: Path | str,
        cache: Path,
        registry: Path,
    ):
        #self.root = _validate_root_path(root)
        self.input = _validate_input_path(input)  
        self.cache = cache
        self.registry = registry
        self.images = self.cache / "echogram_images"

        self.images.mkdir(parents=True, exist_ok=True)
    
    def __repr__(self):
        params = ", ".join([f'{key}={value!r}' for (key, value) in self.__dict__.items()])
        return "PathsConfig(" + params + ")"
    
    def __str__(self):
        return str(self.__dict__)

class DataLoadingConfig():
    def __init__(self, chunks: dict):
        self.chunks = chunks

class ImageDataConfig():
    """Configuration object. Attributes specify echointegrated data and parameters to build
    an image dataset from it.
    """
    
    def __init__(self,
        cruise_name: str,
        ei_id: int,
        time_frame_size: int,
        z_min_idx: int,
        z_max_idx: int,
        frequencies: float | Sequence[float],
        vmin: float,
        vmax: float,
        echogram_cmap: str,
        echogram_images_dir: Path,
    ):
        
        self.cruise_name = cruise_name
        self.ei_id = ei_id
        self.time_frame_size = time_frame_size
        self.z_min_idx = z_min_idx
        self.z_max_idx = z_max_idx
        self.frequencies = frequencies
        self.vmin = vmin
        self.vmax = vmax
        self.echogram_cmap = echogram_cmap

        self.save_dir = _format_images_dir_path(
            echogram_images_dir=echogram_images_dir,
            cruise_name=self.cruise_name,
            ei_id=self.ei_id,
            time_frame_size=self.time_frame_size,
            vmin=self.vmin,
            vmax=self.vmax,
            z_min_idx=self.z_min_idx,
            z_max_idx=self.z_max_idx,
            frequencies=self.frequencies,
            echogram_cmap=self.echogram_cmap,
        )

    def __repr__(self):
        params = ", ".join([f'{key}={value!r}' for (key, value) in self.__dict__.items()])
        return "ImageDataConfig(" + params + ")"


class SessionConfig():
    """Configuration object for an echogram labelling session.
    """
    def __init__(
        self,
        image_dataset_id: int,
        libname: str = "Default"
        ):

        self.session_id = datetime.today().strftime('%Y-%m-%d_%H%M') # intelligible prefix for ROI ids
        self.image_dataset_id = image_dataset_id
        self.libname = libname

    def __repr__(self):
        params = ", ".join([f'{key}={value!r}' for (key, value) in self.__dict__.items()])
        return "SessionConfig(" + params + ")"


class LabelConfig():
    def __init__(
        self,
        paths: PathsConfig,
        loading: DataLoadingConfig,
        image_data: ImageDataConfig,
        session: SessionConfig,
    ):
        self.paths = paths
        self.loading = loading
        self.image_data = image_data
        self.session = session

    def json_dir(self):
        dir = self.image_data.save_dir / self.session.libname
        dir.mkdir(parents=True, exist_ok=True)
        return dir

    def __repr__(self):
        params = "\n".join([f'{key}={value.__repr__()!r}' for (key, value) in self.__dict__.items()])
        return "LabelConfig(" + params + "\n)"



# ---- Helper functions ----

def _validate_input_path(input: str | Path) -> Path:

    input = Path(input)

    # resolve path (rel. to CWD or absolute)
    if not input.is_absolute():
        input = Path(os.getcwd()) / input

    # check if path is a file or is not empty
    if input.is_file():
        return input
    if input.is_dir() and os.listdir(str(input)):
        return input
    else:
        raise ValueError(f"Invalid input path - {input}")
    

# ---- Builder path formatting functions ----

def _format_ei_name(cruise_name, ei_id):
    """Name describing echointegration data (Cruise name + echointegration id in registry)
    """
    return cruise_name + f'_EI_{ei_id:02d}'


def _format_images_dir_path(
    echogram_images_dir: Path,
    cruise_name: str,
    ei_id: int,
    time_frame_size: int,
    vmin: float,
    vmax: float,
    z_min_idx: int,
    z_max_idx : int,
    frequencies: float | Sequence[float],
    echogram_cmap: str
) -> Path:
    """Helper to format the folder structure before creating an echogram image dataset.
    """

    supfolder = _format_ei_name(cruise_name, ei_id)

    def subfolder() -> str:
        """Subfolder name containing parameters.
        """
        
        if isinstance(frequencies, (list, tuple)):      # normalize frequencies to a list
            freqs = frequencies
        else:
            freqs = [frequencies]
            
        freqs = [int(f) for f in freqs]                 # convert to int for cleaner name

        return (echogram_cmap + '_' + 
                '_'.join(map(str, freqs)) +'kHz_' +
                f'TF{time_frame_size}_Z{z_min_idx}-{z_max_idx}_Sv{int(vmin)}-{int(vmax)}dB')

    return echogram_images_dir / supfolder / subfolder()