"""Helpers to download demo data"""

import logging
from pathlib import Path
import requests
from tqdm import tqdm
import zipfile

# define root folder
HERE = Path(__file__).parent.parent

# Init logger
logger = logging.getLogger(__name__)


def download_file(url: str) -> str:
    """Download a file from a url using requests"""

    local_filename = url.split('/')[-1]

    headers = {
        "User-Agent": "curl/8.0",
        "Accept-Encoding": "identity"
    }

    with requests.get(url, stream=True, headers=headers) as r:
        r.raise_for_status()
        total_size = int(r.headers.get('content-length', 0))

        with open(local_filename, "wb") as f, tqdm(total=total_size, unit="B", unit_scale=True) as pbar:
            for chunk in r.raw.stream(1024 * 1024, decode_content=False):
                f.write(chunk)
                pbar.update(len(chunk))
        
    return local_filename


def download_demo_data() -> Path:
    """Download sample data from GitHub release"""
    output_file = HERE / "app_data/input/sample_data.nc"

    if output_file.exists():
        logger.warning(f"Demo data file already exists at {output_file}.")
        return output_file
    
    output_file.parent.mkdir(exist_ok=True, parents=True)

    url = "https://github.com/gaspardringuenet/sv-extraction-tools/releases/download/demo-data-v1/sample_data.zip"

    logger.info("Downloading demo data.")

    zipped_file = HERE / download_file(url)

    logger.info("Unzipping.")
    with zipfile.ZipFile(zipped_file, 'r') as zip_ref:
        zip_ref.extractall(output_file.parent)

    zipped_file.unlink()
    logger.info(f"Sample data saved to {output_file}")

    return output_file