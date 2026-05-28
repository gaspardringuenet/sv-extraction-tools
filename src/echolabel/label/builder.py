from pathlib import Path
from tqdm import tqdm
from typing import Sequence
import xarray as xr

from .vizutils import sv2array, normalize_sv_array, sv_norm2image
from .config import _format_ei_name


# ---- Image saving function ---- #

def build_survey_images(
    sv: xr.DataArray,
    cruise_name: str,
    ei_id: int,
    time_frame_size: int, 
    z_min_idx: int, 
    z_max_idx: int, 
    vmin: float, 
    vmax: float, 
    frequencies: float | Sequence[float], 
    echogram_cmap: str, 
    save_dir: Path,
) -> None:
    """Slices a volume backscattering (Sv) DataArray into time frames and saves an
    echogram of each frame.

    Parameters
    ----------
    sv : xr.DataArray
        Volume backscattering DataArray with dimensions time, depth, channel.
    cruise_name : str
        Name of the cruise. Used for file names.
    ei_id : int
        Id of echointegration in registry. Used for file names.
    time_frame_size : int
        Desired echogram width, in number of ESDUs.
    z_min_idx : int
        Minimum depth index for the frames (0 at surface).
    z_max_idx : int
        Maximum depth index for the frames (-1 or len(sv.depth) at bottom).
    vmin : float
        Inferior bound of colormap.
    vmax : float
        Superior bound of colormap.
    frequencies : float | Sequence[float]
        Frequency channels to plot. Either one, or 3 channels are accepted.
    echogram_cmap : str
        Colormap name. If 3 frequencies are selected, cmap must be 'RGB'. If 1 
        frequency is selected, matplotlib cmap names are accepted.
    save_dir : Path
        Output directory.
    """

    # ensure output folder exists
    save_dir.mkdir(parents=True, exist_ok=True)

    # format EI name (used as prefix for Image files)
    ei_name = _format_ei_name(cruise_name, ei_id)

    # create slices
    n = len(sv.time)
    slicing = list(range(0, n, time_frame_size)) + [n]

    # save an image for each time slice
    for i in tqdm(range(len(slicing)-1), desc=f"{ei_name} frames"):

        t0, t1 = slicing[i], slicing[i+1]

        # slice DataArray and get values as np.ndarray
        sv_array = sv2array(sv, time_idx_slice=slice(t0, t1), depth_idx_slice=slice(z_min_idx, z_max_idx), channels=frequencies)

        # normalise values to [0, 1]
        sv_norm = normalize_sv_array(sv_array, vmin, vmax)

        # reshape and convert to PIL.Image by applying a color mapping
        img = sv_norm2image(sv_norm, echogram_cmap)

        # save image
        img.save(save_dir / f"{ei_name}_T{t0}-{t1}_Z{z_min_idx}-{z_max_idx}.png")