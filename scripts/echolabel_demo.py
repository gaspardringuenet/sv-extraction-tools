import argparse
from pathlib import Path

from sv_extraction import EcholabelApp
from sv_extraction.demo_data import download_demo_data

# define root folder
HERE = Path(__file__).parent.parent


def main(
    libname: str,
    frequencies: float | list[float],
    cmap: str,
    time_frame_size: int,
    z_min_idx: int,
    z_max_idx: int,
    vmin: float,
    vmax: float,
    input_path: Path = None,
    registry_path: Path = None
) -> None:
    
    if not input_path:
        input_path = download_demo_data()
        
    # instanciate labelling app
    app = EcholabelApp(
        input=input_path,
        libname=libname,
        root=HERE,
        frequencies=frequencies,
        echogram_cmap=cmap,
        registry=registry_path,
        time_frame_size=time_frame_size,
        z_min_idx=z_min_idx,
        z_max_idx=z_max_idx,
        vmin=vmin,
        vmax=vmax
    )

    # run the labelling app
    app.run(force_rebuild_images=False)



if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument("--input_path", type=Path, default=None)
    parser.add_argument("--libname", type=str, default="ROI_lib_demo")
    parser.add_argument("--frequencies", type=float, nargs='+', default=[38., 70., 120.])
    parser.add_argument("--cmap", type=str, default="RGB")
    parser.add_argument("--registry_path", type=Path, default=None)
    parser.add_argument("--time_frame_size", type=int, default=5000)
    parser.add_argument("--z_min_idx", type=int, default=0)
    parser.add_argument("--z_max_idx", type=int, default=-1)
    parser.add_argument("--vmin", type=float, default=-90.)
    parser.add_argument("--vmax", type=float, default=-50.)

    args = parser.parse_args()

    main(**vars(args))