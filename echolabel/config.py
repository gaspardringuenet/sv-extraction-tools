import os
from pathlib import Path
import platformdirs

class GlobalConfig:
    """Global application configuration"""

    def __init__(
        self, 
        name: str = None, 
        cache_dir: Path = None, 
        registry: Path = None,
        output_dir: Path = None,
        log_level: str = "INFO"
    ):
        self.name = name or "echolabel"

        self.cache = cache_dir or get_cache_dir(self.name)
        self.registry = registry or self.cache / "registry.db"
        self.output_dir = output_dir or get_default_output_dir(self.name)

        self.cache.mkdir(parents=True, exist_ok=True)

        self.log_level = log_level


def get_cache_dir(name: str) -> Path:
    return Path(platformdirs.user_cache_dir(name))

def get_default_output_dir(name: str) -> Path:
    return Path(os.getcwd()) / f"{name}_outputs"