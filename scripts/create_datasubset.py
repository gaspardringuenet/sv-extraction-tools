from pathlib import Path
import xarray as xr
from sv_extraction.echolabel.dataloader import load_dataset


def main():
    
    HERE = Path(__file__).parent.parent

    # Lazy load data (and clean removed pixels - equal to -150 dB)
    ds = load_dataset(HERE / "private/data/input/Abracos_A2/", chunks={"time": 10_000, "depth": 200})
    ds = ds.where(ds.Sv != -150.)

    # Slice to create subset
    DAY = '2017-04-25'
    time_slice = slice(f'{DAY} 06:00', f'{DAY} 18:00')
    depth_slice = slice(0, 1000)
    ds: xr.Dataset = ds.sel(time=time_slice, depth=depth_slice).compute()

    # Save
    ds.to_netcdf(path=HERE / "output/sample_data.nc", engine="netcdf4")


if __name__ == "__main__":
    main()