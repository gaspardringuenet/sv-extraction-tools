import argparse
from pathlib import Path

from .app import EcholabelApp
from .config import _get_app_cache_dir
from ..demo_data import download_demo_data


def main() -> None:
    
    parser = get_CLI_parser()
    args = validate_and_parse(parser)

    if args.demo:
        args.input = download_demo_data(_get_app_cache_dir())

    print(f"{args.registry = }")
        
    # instanciate labelling app
    app = EcholabelApp(
        input=args.input,
        libname=args.libname,
        #root=HERE,
        frequencies=args.freqs,
        echogram_cmap=args.cmap,
        registry=args.registry,
        time_frame_size=args.time_frame_size,
        z_min_idx=args.z_min_idx,
        z_max_idx=args.z_max_idx,
        vmin=args.vmin,
        vmax=args.vmax
    )

    # run the labelling app
    app.run(force_rebuild_images=False)

    # TODO output current shapes library as csv file


def get_CLI_parser() -> argparse.ArgumentParser:

    parser = argparse.ArgumentParser(
        description="Echolabel: Interactive tool for echogram labelling.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    echolabel --demo                                                        # Run with demo data
    echolabel --input /path/to/data --libname my_shapes_library             # Run with your data and a custom library name
    echolabel --input /path/to/data --frequencies 38 70 120 --cmap RGB      # Specify the frequency channels for RGB mapping
    echolabel --input /path/to/data --frequencies --cmap viridis            # Single channel mapping
        """
    )

    parser.add_argument(
        "--input", type=Path, default=None,
        help="Path to a volume backscattering (Sv) netCDF file, or input folder containing several files of the same cruise. Required unless using --demo. Path can be relative or absolute"
    )
    parser.add_argument(
        "--libname", type=str, default="shapes_lib",
        help="Name of the shapes library. A shapes library is linked to a unique set of input files (default: shapes_lib)"
    )
    parser.add_argument(
        "--freqs", type=float, nargs='+', default=[38., 70., 120.],
        help="Frequency channels to use in echogram colormapping. Exactly three channels are accepted with --cmap RGB, else only one (default: 38 70 120)"
    )
    parser.add_argument(
        "--cmap", type=str, default="RGB",
        help="Colormap for echogram images. Either RGB or a matplotlib colormap (default: RGB)"
    )
    parser.add_argument(
        "--registry", type=Path, default=None,
        help="Path to custom registry file"
    )
    parser.add_argument(
        "--time_frame_size", type=int, default=5000,
        help="Width of echogram images in number of ping axis units (default: 5000)"
    )
    parser.add_argument(
        "--z_min_idx", type=int, default=0,
        help="Index of the upper (shallower) bound of echogram images in the depth axis (default: 0)"
    )
    parser.add_argument(
        "--z_max_idx", type=int, default=-1,
        help="Index of the lower (deeper) bound of echogram images in the depth axis (default: -1)"
    )
    parser.add_argument(
        "--vmin", type=float, default=-90.,
        help="Minimal volume backscattering value for color mapping (in dB) (default: -90)"
    )
    parser.add_argument(
        "--vmax", type=float, default=-50.,
        help="Maximal volume backscattering value for color mapping (in dB) (default: -50)"
    )
    parser.add_argument(
        "--demo", action=argparse.BooleanOptionalAction,
        help="Download and use demo data"
    )

    return parser


def validate_and_parse(parser: argparse.ArgumentParser) -> argparse.Namespace:

    args = parser.parse_args()

    if (args.input is None) and (not args.demo):
        raise ValueError()
    
    return args


if __name__ == "__main__":
    main()