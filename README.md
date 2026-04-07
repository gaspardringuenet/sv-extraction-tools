# Sv Extraction Tools

Interactive Python tools to extract acoustic volume backscattering data from multi-frequency echograms.

## Setting up

```{bash}
uv sync
```

or with `pip`

```{bash}
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

## `Echolabel` Demo

`Echolabel` allows the user to draw shapes on echograms. It builds an images dataset corresponding to a given dataset and visualization parameters, and wraps `Labelme` to enable seemless annotation.

To run with demo data:

```{bash}
uv run scripts/echolabel_demo.py --input_path /PATH/TO/DATA
```

The `input_path` argument is optional. By default, the script will download a demonstration dataset. To reduce download time, we recommand downloading manually via this [GitHub asset link](https://github.com/gaspardringuenet/sv-extraction-tools/releases/download/demo-data-v1/sample_data.zip).

The `EcholabelApp` then prints out echogram images and runs a `labelme` command as a subprocess, opening the UI.

Expected terminal output:

```{bash}
$ uv run scripts/echolabel_demo.py
INFO 19:39:16: Downloading demo data. (Line: 50 [demo_data.py])
100%|█████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 97.9M/97.9M [02:30<00:00, 650kB/s]
INFO 19:41:47: Unzipping. (Line: 54 [demo_data.py])
INFO 19:41:53: Sample data saved to /Users/gaspardringuenet/Projects/sv-extraction/app_data/input/sample_data.nc (Line: 59 [demo_data.py])
INFO 19:41:59: Echointegration created with id 1. (Line: 72 [echointegrations.py])
INFO 19:41:59: Successfully added new image dataset with id 1 (Line: 100 [images.py])
Building new images...
ABRACOS02_EI_01 frames: 100%|███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 2/2 [00:01<00:00,  1.61it/s]
Echogram labelling session
 - Id:		2026-04-07_1941
 - Name:	ROI_lib_demo
 - Cruise:	ABRACOS02
 - EI:		3.0 Number of pings x 1.0 Range (meters) (EI id 1)
 - Images:	/Users/gaspardringuenet/Projects/sv-extraction/app_data/echogram_images/ABRACOS02_EI_01/RGB_38_70_120kHz_TF5000_Z0--1_Sv-90--50dB

Updating shapes registry file at: /Users/gaspardringuenet/Projects/sv-extraction/app_data/registry.db

Labelling session shapes registry update: 
 * 5 new 
 * 0 modified 
 * 0 deleted 
 * Total number of shapes in library (ROI_lib_demo): 5

Library synced up: available accross all 1 image datasets related to EI 01

```
