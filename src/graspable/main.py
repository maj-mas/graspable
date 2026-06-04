import argparse
import yaml


def main():
    """Entrypoint into the program. The config .yaml file is parsed and a computation object is created, then executed."""
    print("Hello, world!")

    # setup cli args
    argparser = argparse.ArgumentParser(
        prog="graspable",
        description="graspable aims to provide users with a YAML-based set of python tools to set up and run atomic structure calculations using the GRASP package.",
    )
    argparser.add_argument(
        "-c",
        "--config",
        type=str,
        required=True,
        help="Path to .yaml config describing the calculation.",
    )
    argparser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        default=False,
        help="If set, only print input files and parameters, but do not execute.",
    )
    args = argparser.parse_args()

    # load config
    cfg = yaml.load(args.config)


if __name__ == "__main__":
    main()
