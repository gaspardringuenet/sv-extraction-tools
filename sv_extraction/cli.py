import os
import argparse
from pathlib import Path


def get_CLI_parser() -> argparse.ArgumentParser:

    parser = argparse.ArgumentParser(
        description="Echolabel: Interactive tool for echogram labelling.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    echolabel label --demo                                                      # Run with demo data
    echolabel label --input /path/to/data --libname my_shapes_library           # Run with your data and a custom library name
    echolabel label --input /path/to/data --frequencies 38 70 120 --cmap RGB    # Specify the frequency channels for RGB mapping
    echolabel label --input /path/to/data --frequencies --cmap viridis          # Single channel mapping
    echolabel extract                                                           # Extract echotypes from labelled shapes
        """
    )


    # Top-level argument
    parser.add_argument(
        "--cache_dir", action=argparse.BooleanOptionalAction,
        help="Print cache directory path"
    )

    # Sub-commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Label command triggering labelme wrapper (default)
    label_parser = subparsers.add_parser(
        "label",
        help="Launch interactive echogram shapes labelling tools (default)",

    )


    label_parser.add_argument(
        "--input", type=Path, default=None,
        help="Path to a volume backscattering (Sv) netCDF file, or input folder containing several files of the same cruise. Required unless using --demo. Path can be relative or absolute"
    )
    label_parser.add_argument(
        "--libname", type=str, default="shapes_lib",
        help="Name of the shapes library. A shapes library is linked to a unique set of input files (default: shapes_lib)"
    )
    label_parser.add_argument(
        "--freqs", type=float, nargs='+', default=[38., 70., 120.],
        help="Frequency channels to use in echogram colormapping. Exactly three channels are accepted with --cmap RGB, else only one (default: 38 70 120)"
    )
    label_parser.add_argument(
        "--cmap", type=str, default="RGB",
        help="Colormap for echogram images. Either RGB or a matplotlib colormap (default: RGB)"
    )
    label_parser.add_argument(
        "--registry", type=Path, default=None,
        help="Path to custom registry file"
    )
    label_parser.add_argument(
        "--time_frame_size", type=int, default=5000,
        help="Width of echogram images in number of ping axis units (default: 5000)"
    )
    label_parser.add_argument(
        "--z_min_idx", type=int, default=0,
        help="Index of the upper (shallower) bound of echogram images in the depth axis (default: 0)"
    )
    label_parser.add_argument(
        "--z_max_idx", type=int, default=-1,
        help="Index of the lower (deeper) bound of echogram images in the depth axis (default: -1)"
    )
    label_parser.add_argument(
        "--vmin", type=float, default=-90.,
        help="Minimal volume backscattering value for color mapping (in dB) (default: -90)"
    )
    label_parser.add_argument(
        "--vmax", type=float, default=-50.,
        help="Maximal volume backscattering value for color mapping (in dB) (default: -50)"
    )
    label_parser.add_argument(
        "--demo", action=argparse.BooleanOptionalAction,
        help="Download and use demo data"
    )
    label_parser.add_argument(
        "--export_csv", action=argparse.BooleanOptionalAction,
        help="//TODO NOT IMPLEMENTED. Export shapes library data as a .csv file"
    )
    label_parser.add_argument(
        "--output", type=Path, default=Path(os.getcwd()),
        help=f"//TODO NOT IMPLEMENTED. Output folder for export (default: {Path(os.getcwd())})"
    )
    label_parser.add_argument(
        "--debug", action=argparse.BooleanOptionalAction,
        help="Print debug level logs"
    )


    # Extract command (launch Dash echotype extraction app)
    extract_parser = subparsers.add_parser(
        name="extract",
        help="Open echotypes extraction app in web browser."
    )

    extract_parser.add_argument(
        "--registry", type=Path, default=None,
        help="Path to custom registry file (defaut: echolabel cache)"
    )

    return parser


def validate_and_parse(parser: argparse.ArgumentParser) -> argparse.Namespace:
    args = parser.parse_args()

    if (args.command == "label") and (args.input is None) and (not args.demo):
        raise ValueError("--input or --demo required for the 'label' command")
    
    return args