import os
from pathlib import Path


def _validate_cache_dir(cache_dir: str | Path) -> Path:

    cache_dir = Path(cache_dir)

    if not cache_dir:
        raise ValueError(f"No cache directory.")

    if not cache_dir.is_dir():
        raise ValueError(f"Cache directory not a directory: {cache_dir}")
    
    return cache_dir


def _validate_root_path(root: str | Path) -> Path:

    if root is None:
        default = True
        root = os.getcwd()

    root = Path(root)

    if not root.is_dir():
        type_str = "Inferred" if default else "Provided"
        raise ValueError(f"{type_str} root path is not a directory - {root}")
    
    return root


def _validate_input_path(input: str | Path) -> Path:

    input = Path(input)

    # resolve path (rel. to root or absolute)
    if not input.is_absolute():
        input = Path(os.getcwd()) / input

    # check if path is a file or is not empty
    if input.is_file():
        return input
    if input.is_dir() and os.listdir(str(input)):
        return input
    else:
        raise ValueError(f"Invalid input path - {input}")
    

def _validate_registry_path(registry: str | Path, cache_dir: str | Path) -> Path:

    if not registry:
        return _format_registry_path(cache_dir)
    
    print(f"{registry = }")

    registry = Path(registry)
    
    if not registry.is_absolute():
        registry = Path(os.getcwd()) / registry

    if registry.parent.is_dir():
        return registry
    
    raise ValueError(f"Invalid registry parent directory path - {registry.parent}")


def _format_registry_path(cache_dir: str | Path) -> Path:

    return Path(cache_dir) / "registry.db"