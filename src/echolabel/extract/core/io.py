from pathlib import Path
from typing import Sequence, Dict, List
import xarray as xr


def load_dataset_from_files(files: Sequence[Path|str], chunks: Dict[str, int] | None =  None) -> xr.Dataset:
    """Lazy-load data from one or more acoustic netCDF files having variables 'Sv', 'time', and 'depth'. If the files are related to
    the same cruise and have matching metadata, concatenate them along the 'time' axis as a single xarray.Dataset.

    Args:
        files (Sequence[Path | str]): Source acoustic netCDF files.
        chunks (Dict[str, int], optional): 'time' and 'depth' axes chunks for lazy loading with Dask. Defaults to {"time": 1000, "depth": 100}.

    Raises:
        ValueError: If no file paths are given.
        ValueError: If input files paths are not valid .nc files.
        ValueError: If not all files contain required metadata. Required: 'cruise_name', 'data_ping_axis_interval_value', 'data_ping_axis_interval_type', 'data_range_axis_interval_value', 'data_range_axis_interval_type'.
        ValueError: If not all files have the same metadata values.
        ValueError: If not all files contain required variables. Required: 'time', 'depth', 'Sv'.
        ValueError: If 'time' axes overlap between files.
        ValueError: If concatenation fails with xarray.concat().

    Returns:
        xr.Dataset: Concatenate cruise dataset.
    """

    # Required fields to check
    required_metadata_attrs = [
        'cruise_name', 
        'data_ping_axis_interval_value', 
        'data_ping_axis_interval_type', 
        'data_range_axis_interval_value', 
        'data_range_axis_interval_type'
    ]

    required_vars = ["time", "depth", "channel", "Sv"]

    # Validate files
    files = validate_files(files)

    # Defaults chunkings
    if chunks is None:
        chunks = {"time": 1000, "depth": 100}
    
    # Open xr.Dataserts from all file (use lazy loading)
    ds_dict: dict = {file: xr.open_dataset(file, chunks=chunks) for file in files}

    # Validate metadata (check existence and correspondence between datasets)

    for attr in required_metadata_attrs:
        validate_metadata(ds_dict, attr)

    # Validate variables (check existence)
    for var in required_vars:
        validate_vars(ds_dict, var)

    # Ensure time monotony & sort datasets by time
    ds_list: list = [ensure_time_monotony(ds) for ds in ds_dict.values()]
    ds_list.sort(key=lambda ds: ds.time.isel(time=0).load().item())
    check_no_time_overlap(ds_list)

    # Concatenate datasets
    return concatenate_datasets(ds_list)


# ---- Helper functions ----

def validate_files(files: Sequence[Path|str]) -> List[Path]:
    """Ensure input files are correct."""
    if not files:
        raise ValueError("No files provided.")
    for file in files:
        path = Path(file)
        if not path.is_file() or path.suffix != ".nc":
            raise ValueError(f"Input path is not a .nc file: {file}")
    return [Path(file) for file in files]

def validate_metadata(ds_dict: Dict[Path, xr.Dataset], attr: str) -> None:
    """Ensure all files share the same metadata attribute 'attr'."""
    attrs_vals = []
    # check existence
    for file, ds in ds_dict.items():
        if attr not in ds.attrs:
            raise ValueError(f"Attribute '{attr}' not found in Dataset loaded from file: {file}")
        attrs_vals.append(ds.attrs.get(attr))
    # check correspondence
    attrs_vals = set(attrs_vals)
    if len(attrs_vals) > 1: 
        raise ValueError(f"Datasets having different '{attr}' attributes are not handled. {attrs_vals = }.")

def validate_vars(ds_dict: Dict[Path, xr.Dataset], var: str) -> None:
    """Ensure all files contain the variable 'var'."""
    for file, ds in ds_dict.items():
        try:
            _ = ds[var]
        except Exception as e:
            raise ValueError(f"Variable {var} not found in Dataset loaded from file: {file}\n{e}")

def ensure_time_monotony(ds: xr.Dataset) -> xr.Dataset:
    """Sort Dataset by time."""
    return ds.sortby('time')

def check_no_time_overlap(ds_list: List[xr.Dataset]) -> None:
    """Ensure time axes do not overlap between datasets."""
    times = [
        (ds.time.isel(time=0).load().item(),
        ds.time.isel(time=-1).load().item())
        for ds in ds_list
    ]
    times = sorted(times)

    for (_, end), (start, _) in zip(times[:-1], times[1:]):
        if start <= end:
            raise ValueError("Overlapping time coordinates detected.")

def concatenate_datasets(ds_list: List[xr.Dataset]) -> xr.Dataset:
    """Concatenate datasets along the time axis."""
    try:
        ds_combined  = xr.concat(
            ds_list,
            dim='time', 
            data_vars='all',
            combine_attrs="drop_conflicts"
        )
    except Exception as e:
        files_list_str = '\n-' + '\n-'.join(str(files))
        raise ValueError(f"Unable to concatenate Datasets along the time dimensions. netCDF files:{files_list_str}") from e
    
    return ds_combined
