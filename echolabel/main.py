import argparse
import logging
from pathlib import Path

from .cli import get_CLI_parser, validate_and_parse
from .cache.dir import get_app_cache_dir
from .demo_data import download_demo_data


def main() -> None:

    # Parse CLI arguments
    parser = get_CLI_parser()
    args = validate_and_parse(parser)

    if args.cache_dir:
        print(get_app_cache_dir())
        return
    
    # Configure logger
    level = "DEBUG" if args.debug else "INFO"
    
    setup_logging(level, get_app_cache_dir())
    logger = logging.getLogger(__name__)

    # Run required sub-command
    if args.command == "label":
        run_label(args, logger)
    elif args.command == "extract":
        run_extract(logger)
    elif args.command == "copy-shapes-lib":
        run_copy('shapes', args, logger)
    elif args.command == "copy-echotypes-lib":
        run_copy('echotypes', args, logger)
    elif args.command == "delete-shapes-lib":
        ...
    elif args.command == "delete-cache":
        ...
    else:
        raise ValueError("Incorrect command.")



def setup_logging(level: str, cache_dir: Path) -> None:
    """Configure application logger"""
    logging.basicConfig(
        format='%(levelname)s %(asctime)s: %(message)s (Line: %(lineno)d [%(filename)s])',
        datefmt='%H:%M:%S',
        level=level,
        filename=str(cache_dir / "echolabel.log"),
        filemode='w',
    )



def run_label(args: argparse.Namespace, logger: logging.Logger) -> None:
    from .label.app import EcholabelApp

    if args.demo:
        args.input = download_demo_data(get_app_cache_dir())

    # instanciate labelling app
    logger.info("Instanciating labelling app.")
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
    logger.info("Running app.")
    app.run(force_rebuild_images=False)

    # TODO output current shapes library as csv file



def run_extract(logger: logging.Logger) -> None:
    from .extract.app import EchotypesApp

    cache_dir = get_app_cache_dir()

    logger.info("Instanciating extraction app.")
    app = EchotypesApp(root=cache_dir, registry=cache_dir / "registry.db")

    logger.info("Running extraction app.")
    app.run(debug=True)



def run_copy(*args):
    ...



if __name__ == "__main__":
    main()