import argparse
import yaml
from importlib.resources import files

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
if __name__ == "__main__":
    args = argparser.parse_args()


class GraspableMain:
    def main(self, cfg: str = None):
        """Entrypoint into the program. The config .yaml file is parsed and a computation object is created, then executed.

        Args:
            cfg (str, optional): Path to config, useful if graspable is imported as a module, e.g. for unit testing. Defaults to None.

        Raises:
            RuntimeError: If the passed config is empty.
        """

        # load config
        cfg_path = args.config if cfg is None else cfg
        with open(cfg_path, "r") as cfg_file:
            config = yaml.safe_load(cfg_file)
        if config is None:
            raise RuntimeError("The input config is empty")

        # also load default config for unspecified options
        config_path = files("graspable.cfg") / "default_config.yaml"
        with config_path.open("r") as default_cfg_file:
            default_config = yaml.safe_load(default_cfg_file)

        print(config)
        print(default_config)


def main():
    graspable_instance = GraspableMain()
    graspable_instance.main()


if __name__ == "__main__":
    main()
