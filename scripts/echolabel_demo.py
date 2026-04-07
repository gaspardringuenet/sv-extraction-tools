from pathlib import Path
from sv_extraction import EcholabelApp


def main():

    # define root folder
    HERE = Path(__file__).parent.parent

    # instanciate labelling app
    app = EcholabelApp(
        input="private/data/input/ABRACOS_A2",
        libname="ROI_lib_A2_3F_test",
        root=HERE,
        frequencies=[38., 70., 120.],
        echogram_cmap='RGB',
    )

    # run the labelling app
    app.run(force_rebuild_images=False)


if __name__ == "__main__":
    main()