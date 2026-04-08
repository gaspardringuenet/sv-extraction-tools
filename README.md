# `echolabel` - Interactive Echogram Data Extraction Tools

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

## `echolabel` Demo

### Labelling shape using `labelme`

`echolabel` allows the user to draw shapes on echograms. It builds an images dataset corresponding to a given dataset and visualization parameters, and wraps [`labelme`](https://labelme.io/) to enable seemless annotation.

To run the app, use the `label` sub-command[^1]:

```{bash}
uv run echolabel label --input_path /path/to/your/data --libname your_library_name
```

To run with demo data:

```{bash}
uv run echolabel label --demo
```

`echolabel` then prints out echogram images and runs a `labelme` command as a subprocess, opening the UI.

Expected terminal output:

```{bash}
$ uv run echolabel label --demo
Downloading demo data: 100%|██████████████████████████████████████████████████████████████████████████████| 97.9M/97.9M [01:46<00:00, 916kB/s]
ABRACOS02_EI_01 frames: 100%|███████████████████████████████████████████████████████████████████████████████████| 2/2 [00:01<00:00,  1.65it/s]
╭──────────────────────────────────────────────────────── Echogram labelling session ────────────────────────────────────────────────────────╮
│  - Id:          2026-04-08_2100                                                                                                            │
│  - Name:        shapes_lib                                                                                                                 │
│  - Cruise:      ABRACOS02                                                                                                                  │
│  - EI:          3.0 Number of pings x 1.0 Range (meters) (EI id 1)                                                                         │
│  - Images:      /Users/gaspardringuenet/Library/Caches/echolabel/echogram_images/ABRACOS02_EI_01/RGB_38_70_120kHz_TF5000_Z0--1_Sv-90--50dB │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭───────────────────────────────────────────────────────────── Registry update ──────────────────────────────────────────────────────────────╮
│                                                                                                                                            │
│  * 7 new                                                                                                                                   │
│  * 0 modified                                                                                                                              │
│  * 0 deleted                                                                                                                               │
│  * Total number of shapes in library (shapes_lib): 7                                                                                       │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

`Labelme` UI example:

![alt text](image.png)

## Extracting subsets of data from the shapes

Since `echolabel` is focused on shapes, is necessarily captures all the pixels within a given polygon (or circle). A scientific operator may be interested in only a subset of those pixels (for instance to build a machine learning training dataset). To solve this issue, a second software allows the interactive refinement of the selected data.

To run it, use the `extract` sub-command:

```{bash}
uv run echolabel extract
```

Expected terminal output:

```{bash}
$ uv run echolabel extract
Dash is running on http://127.0.0.1:8050/
 * Serving Flask app 'EchotypesApp'
 * Debug mode: on
```

The user must then open a webrowser at the printed adress.

[^1]: Note that the `uv run` commands are only necessary for UV users. `pip` users can simply omit them. The CLI commands should work as long as the package is installed.
