import argparse
from pathlib import Path

from sv_extraction import EchotypesApp

# define root folder
HERE = Path(__file__).parent.parent

def main():

    app = EchotypesApp(root=HERE, registry=HERE/"app_data/registry.db")
    app.run(debug=True)


if __name__ == "__main__":
    main()