from datetime import datetime
from pathlib import Path
from typing import Sequence

from ..paths_validation import _validate_root_path, _validate_input_path, _validate_registry_path
from ..cache.dir import get_app_cache_dir

# ---- Configuration classes ----

class EcholabelPathsConfig():
    def __init__(
        self,
        input: Path | str,
        root: Path | str = None,                    # Path to project root (default = os.getcwd())
        registry: Path | str = None,
    ):
        self.root = _validate_root_path(root)
        self.cache = get_app_cache_dir()
        self.images = self.cache / "echogram_images"

        self.input = _validate_input_path(input)  
        self.registry = _validate_registry_path(registry, self.cache)
    
    def __repr__(self):
        params = ", ".join([f'{key}={value!r}' for (key, value) in self.__dict__.items()])
        return "EcholabelPathsConfig(" + params + ")"
    
    def __str__(self):
        return str(self.__dict__)
    
    def make_cache(self):
        self.cache.mkdir(parents=True, exist_ok=True)
        self.images.mkdir(parents=True, exist_ok=True)


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


class LabellingSessionConfig():
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
        return "LabellingSessionConfig(" + params + ")"


class EcholabelAppConfig():
    def __init__(
        self,
        paths: EcholabelPathsConfig,
        loading: DataLoadingConfig,
        image_data: ImageDataConfig,
        session: LabellingSessionConfig,
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
        return "EcholabelAppConfig(" + params + "\n)"



# ---- Helper functions ----

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