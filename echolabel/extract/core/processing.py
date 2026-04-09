import numpy as np
import xarray as xr
from typing import Sequence, Tuple, List

from sklearn.cluster import KMeans
from sklearn.mixture import GaussianMixture

from .masking import get_labelme_mask


# Selecting Sv values from ROI shape and sv xr.DataArray

def get_offset(imin, imax, array_length):
    """Compute the offset of the [imin, imax] window in array, i.e. how much this window is out of boundaries.
    Offset is negative if imin < 0 and positive if imax > array_length.
    Assumptions are imin < imax and imax-imin < array_length.
    """
    if imin < 0:
        return imin
    else:
        return max(imax-array_length, 0)
    

def apply_padding_safe_1d(i_min: int, i_max: int, array_length: int, padding: int) -> Tuple[int, int]:
    """Apply padding on both size of a 1D window [i_min, i_max] contained in an array.
    Save behaviour: if the padding overflows array bounds, it is cropped.

    Args:
        i_min (int): start index of input window.
        i_max (int): end index of input window.
        array_length (int): length of container array.
        padding (int): desired number of indices for padding.

    Returns:
        tuple[int, int]: bounds indices of the padded window.
    """

    # apply padding naively
    i_min -= padding
    i_max += padding

    # crop to array bounds
    i_min = max(0, i_min)
    i_max = min(array_length - 1, i_max)

    return i_min, i_max


def expand_window_safe_1d(i_min: int, i_max: int, array_length: int, win_size: int) -> Tuple[int, int]:
    """Given an input window [i_min, i_max] contained in an array, expand the window in both directions to
    reach win_size.
    Safe behaviour: when the window bounds reach array bounds, try to shift the window left or right to make
    it fit in array. If the window size exceeds array length, return array bounds.

    Args:
        i_min (int): start index of input window.
        i_max (int): end index of input window.
        array_length (int): length of container array.
        win_size (int): desired size for expanded window.

    Returns:
        tuple[int, int]: bounds indices of the expanded window.
    """

    # center of bbox
    center = (i_min + i_max) // 2

    # compute window extents (correct for odd sizes)
    half_w_left = win_size // 2
    half_w_right = win_size - half_w_left

    # update bounds naively
    i_min = center - half_w_left + (1 - win_size % 2)
    i_max = center + half_w_right - win_size % 2

    # compute potential overflow (positive to the right)
    overflow_left = i_min                                 # N steps before start of array
    overflow_right = -(array_length -1 - i_max)           # N steps after end of array

    # shift window to stay inside array
    if overflow_left >= overflow_right:         # enough room to shift left or right
        if overflow_left < 0:
            shift = - overflow_left             # shift > 0 to the right when window sticks out on the left
        elif overflow_right > 0:
            shift = - overflow_right            # shift < 0 to the left when window sticks out on the right
        else:
            shift = 0                           # no shift when the window does not stick out
        return i_min + shift, i_max + shift 
    else:
        return 0, array_length -1               # return array bound when the window sticks out on both sides


def get_window_safe_1d(i_min, i_max, array_length, min_size: int, min_padding: int) -> Tuple[int, int]:
    if i_max - i_min + 1 + 2 * min_padding > min_size:                          
        return apply_padding_safe_1d(i_min, i_max, array_length, min_padding)      # padd when padding is sufficient to reach min size
    else:
        return expand_window_safe_1d(i_min, i_max, array_length, min_size)         # expand when it is not


def get_window_safe_2d(
    bbox: Tuple[int, int, int, int],
    array_shape: tuple[int, int],
    min_height: int,
    min_width: int,
    min_padding: int
) -> Tuple[int, int, int, int]:
    xmin, xmax, ymin, ymax = bbox
    len_x, len_y = array_shape

    xmin, xmax = get_window_safe_1d(xmin, xmax, len_x, min_width, min_padding)
    ymin, ymax = get_window_safe_1d(ymin, ymax, len_y, min_height, min_padding)

    return (xmin, xmax, ymin, ymax)


def offset_points(points, xmin, ymin):
    return [[p[0]-xmin, p[1]-ymin] for p in points]


def preprocess_sv(
        sv: xr.DataArray, 
        window: Tuple[int, int, int, int],
        frequencies: Sequence[float] | None = None
    ) -> xr.DataArray:
    """Pre-processing of Sv DataArray: crop to window, select frequency channels (optional), transpose to H, W, C shape.

    Args:
        sv (xr.DataArray): Sv DataArray with dimensions 'time', 'depth', 'channel'.
        window (Tuple[int, int, int, int]): Rectangle window for cropping (tmin, tmax, zmin, zmax).
        frequencies (Sequence[float] | None, optional): Frequency channels to select. If None, all channels are selected. Defaults to None.

    Returns:
        xr.DataArray: Processed Sv DataArray.
    """

    if frequencies is None:
        frequencies = sv.channel.values

    return (
        sv
        .isel(
                time=slice(window[0], window[1]+1),
                depth=slice(window[2], window[3]+1)
            )
        .sel(channel=frequencies)
        .transpose('depth', 'time', 'channel')  
    )


def get_roi_mask(sv: xr.DataArray, shape_type: str, shape_points: List[List[int]]) -> xr.DataArray:
    """Create mask to select points in sv that are contained in the ROI described by its shape type and the shape's
    points.

    Args:
        sv (xr.DataArray): Sv DataArray on which the mask will be applied.
        shape_type (str): Labelme shape type of the ROI.
        shape_points (List[List[int]]): Labelme shape points of the ROI. List of [time, depth] coordinates as
            indices with in sv dimensions.

    Returns:
        xr.DataArray: ROI mask DataArray.
    """

    # Compute mask shape
    mask_shape = sv['time'].size, sv['depth'].size,

    # Compute mask
    mask = get_labelme_mask(mask_shape, shape_type, shape_points)

    # return mask DataArray
    return xr.DataArray(
        mask,
        dims=('time', 'depth'),
        coords={'time':sv.time, 'depth':sv.depth}
    )


def init_model(method: str, n_clusters: int, random_state: int) -> GaussianMixture | KMeans:
    """Initialize clustering models.
    """
    
    if method == 'GaussianMixture':
        model = GaussianMixture(n_components=n_clusters, random_state=random_state)
        return model
    
    elif method == 'KMeans':
        model = KMeans(n_clusters=n_clusters, random_state=random_state)
        return model
    
    else:
        raise ValueError(f"Unknown clustering method: {method}")


def cluster_sv(
    sv: xr.DataArray,
    var: str,
    ref_frequency: float,
    model: GaussianMixture | KMeans
) -> Tuple[xr.DataArray, GaussianMixture | KMeans]:

    # Get the right variables (Sv or Delta Sv)
    data = get_var(sv, var_name=var, ref_frequency=ref_frequency)

    # Stack pixels of data into clustering compatible format
    X = stack_pixels(data)

    # Run clustering and create a 1D DataArray
    labels_da = xr.DataArray(
        model.fit_predict(X.values),
        dims="pixel",
        coords={"pixel": X["pixel"]}
    )

    # Reshape to match sv shape
    labels_da = unstack_pixels(source=labels_da, format_like=sv)
    
    return labels_da, model


def compute_delta_sv(
    sv: xr.DataArray,
    ref_frequency: float
) -> xr.DataArray:
    """Subtract a reference channel to volume backscattering (Sv) values contained in the other channels of sv.
    Computes ΔSv_ref = Sv(channel) - Sv(ref) for all channels except ref.

    Args:
        sv (xr.DataArray): multi-frequency Sv data with a 'channel' dimension.
        ref_frequency (float): reference channel coordinate.

    Returns:
        xr.DataArray: DataArray of same shape as sv, except for one less on the channel dimension. channel coords are renamed.
    """
    
    if "channel" not in sv.dims:
        raise ValueError("Input DataArray must have a 'channel' dimension.")
    
    if sv.sizes["channel"] < 2:
        raise ValueError(
            f"At least 2 frequency channels are required for r(f) clustering: {sv.sizes['channel']} available."
        )

    try:
        sv_ref = sv.sel(channel=ref_frequency)
    except KeyError:
        raise ValueError(
            f"Reference frequency {ref_frequency} kHz does not match available frequencies:"
            f"{sv.channel.values}"
        )
    
    sv_other = sv.drop_sel(channel=ref_frequency)

    delta_sv = sv_other - sv_ref

    # Rename variable
    delta_sv = delta_sv.rename("Delta Sv")

    # Add a dimension for reference frequency (channels are kept identical)
    delta_sv = delta_sv.expand_dims(
        reference_frequency= np.array([ref_frequency], dtype=np.float64)
    )

    # Add metadata
    delta_sv.reference_frequency.attrs.update({
        "units": "kHz",
        "long_name": "Reference frequency"
    })

    return delta_sv



def stack_pixels(da: xr.DataArray):

    # Stack spatial dimensions
    stacked = da.stack(pixel=("time", "depth"))

    # Drop pixels with NaNs
    stacked = stacked.dropna(dim="pixel", how="any")

    # shape to (n_pixels, n_channels) as expected by most clustering algorithms
    stacked = stacked.transpose("pixel", "channel")

    return stacked # Contains the necessary information for unstacking
    

def get_var(sv: xr.DataArray, var_name: str, ref_frequency: float | None = None) -> xr.DataArray:
    """Compute Delta Sv (w/ regards to ref frequency) if var_name is 'delta_Sv'. Else return unchanged sv.
    """

    if var_name == "Sv":
        return sv
    
    elif var_name == "delta_Sv":
        delta_sv = compute_delta_sv(sv, ref_frequency)
        return delta_sv.squeeze("reference_frequency", drop=True) # remove reference frequency dim for use in stack_pixels
    
    else:
        raise ValueError(f"Clustering variable name must be one of ['Sv', 'delta_Sv']. Current input: '{var_name}'")
    

def unstack_pixels(source: np.ndarray, format_like: xr.DataArray, stacked_dim="pixel") -> xr.DataArray:
    """Format a 1D labels array indexed by pixels, to match another array's shape (here (time, depth))"""

    # Unstack to (time, depth)
    labels_da = source.unstack(stacked_dim)

    # Reindex like roi_sv
    labels_da = labels_da.reindex_like(
        format_like.squeeze(drop=True),
        fill_value=np.nan
    )

    return labels_da