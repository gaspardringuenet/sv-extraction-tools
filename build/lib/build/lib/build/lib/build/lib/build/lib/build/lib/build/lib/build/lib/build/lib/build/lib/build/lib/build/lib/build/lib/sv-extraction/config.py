import os
from pathlib import Path

def _validate_root_path(root: str | Path):

    if root is None:
        default = True
        root = os.getcwd()

    root = Path(root)

    if not root.is_dir():
        type_str = "Inferred" if default else "Provided"
        raise ValueError(f"{type_str} root path is not a directory - {root}")
    
    return root


def _validate_input_path(input, root):

    input = Path(input)

    # resolve path (rel. to root or absolute)
    if not input.is_absolute():
        input = root / input

    # check if path is a file or is not empty
    if input.is_file():
        return input
    if input.is_dir() and os.listdir(str(input)):
        return input
    else:
        raise ValueError(f"Invalid input path - {input}")
    

def _validate_registry_path(registry, root, appdatadir):

    if not registry:
        return _format_registry_path(appdatadir)
    
    registry = Path(registry)
    
    if not registry.is_absolute():
        registry = root / registry

    if registry.parent.is_dir():
        return registry
    else:
        raise ValueError(f"Invalid registry parent directory path - {registry.parent}")

def _format_registry_path(appdatadir):

    return Path(appdatadir) / "registry.db"