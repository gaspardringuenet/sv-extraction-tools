import argparse

from .cli import get_CLI_parser, validate_and_parse
from .echolabel.config import _get_app_cache_dir
from .demo_data import download_demo_data


def main() -> None:

    parser = get_CLI_parser()
    args = validate_and_parse(parser)

    if args.command == "label":
        run_label(args)
    elif args.command == "extract":
        run_extract()


def run_label(args: argparse.Namespace) -> None:
    from .echolabel.app import EcholabelApp

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


def run_extract() -> None:
    from .echotypes.app import EchotypesApp

    cache_dir = _get_app_cache_dir()

    app = EchotypesApp(root=cache_dir, registry=cache_dir / "registry.db")
    app.run(debug=True)


if __name__ == "__main__":
    main()