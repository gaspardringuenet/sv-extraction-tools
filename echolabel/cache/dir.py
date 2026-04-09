from pathlib import Path
import platformdirs

def get_app_cache_dir() -> Path:
    path = Path(platformdirs.user_cache_dir("echolabel"))
    path.mkdir(exist_ok=True, parents=True)
    return path