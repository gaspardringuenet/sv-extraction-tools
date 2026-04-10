import argparse
import logging
from pathlib import Path
from typing import Literal

from .config import GlobalConfig
from .utils.cli import get_CLI_parser, validate_and_parse
from .utils.demo_data import download_demo_data


def main() -> None:

    # Parse CLI arguments
    parser = get_CLI_parser()
    args = validate_and_parse(parser)

    global_config = GlobalConfig()

    if args.cache_dir:
        print(global_config.cache)
        return
    
    # Configure logger
    #level = "DEBUG" if args.debug else "INFO" #TODO implement --debug
    setup_logging(global_config.log_level, global_config.cache)
    logger = logging.getLogger(__name__)

    # Run required sub-command
    if args.command == "label":
        run_label(global_config, logger, args)
    elif args.command == "extract":
        run_extract(global_config, logger)
    elif args.command == "copy-shapes-lib":
        raise NotImplementedError
    elif args.command == "copy-echotypes-lib":
        raise NotImplementedError
    elif args.command == "delete-shapes-lib":
        raise NotImplementedError
    elif args.command == "delete-cache":
        run_delete_cache(global_config, logger)
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


def run_label(global_config: GlobalConfig, logger: logging.Logger, args: argparse.Namespace) -> None:
    from .label.app import LabelmeWrapper

    if args.demo:
        args.input = download_demo_data(global_config.cache)

    # instanciate labelling app
    logger.info("Instanciating labelling app.")
    app = LabelmeWrapper(
        global_config=global_config,
        input=args.input,
        libname=args.libname,
        frequencies=args.freqs,
        echogram_cmap=args.cmap,
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
    if args.export_csv:
        ...


def run_extract(global_config: GlobalConfig, logger: logging.Logger) -> None:
    from .extract.app import EchotypesExtractor

    logger.info("Instanciating extraction app.")
    app = EchotypesExtractor(global_config)

    logger.info("Running extraction app.")
    app.run(debug=True)


def run_copy_lib(
    level: Literal['shapes', 'echotypes'],
    args: argparse.Namespace,
    logger: logging.Logger
) -> None:
    
    info_str = f"Copying {level} libraries {args.source} (new name: {args.destination})."
    if (level == "shapes" and args.include_downstream):
        info_str += " Copying downstream echotypes libraries as well."
    logger.info(info_str)

    if level == 'echotypes':
        ...


def run_delete_cache(global_config: GlobalConfig, logger: logging.Logger) -> None:
    import shutil
    
    cache_path = global_config.cache
    logger.info(f"About to delete cache directory: {cache_path}")
    
    response = input(f"Are you sure you want to delete all app cache at {cache_path}?\n[yes/no]: ").strip().lower()
    
    if response == "yes":
        shutil.rmtree(cache_path)
        logger.info("Cache deleted successfully.")
    else:
        logger.info("Cache deletion cancelled.")




if __name__ == "__main__":
    main()