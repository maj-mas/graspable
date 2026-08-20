import argparse
import sys
from importlib.resources import files

from omegaconf import OmegaConf

from .calculation import Calculation

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
args = None
if "unittest" not in sys.modules:
    args = argparser.parse_args()


class GraspableMain:
    def main(self, cfg: str = None):
        """Entrypoint into the program. The config .yaml file is parsed and a computation object is created, then executed.

        Args:
            cfg (str, optional): Path to config, useful if graspable is imported as a module, e.g. for unit testing. Defaults to None.

        Raises:
            RuntimeError: If the passed config is empty.
        """

        if args is not None:
            if args.dry_run:
                raise NotImplementedError("dry run not implemented.")

        # load config
        cfg_path = cfg if cfg is not None else args.config

        config = OmegaConf.load(cfg_path)
        if config is None or len(config) == 0:
            raise RuntimeError("The input config is empty")

        # also load default config for unspecified options
        def_config_path = files("graspable.cfg") / "default_config.yaml"
        default_config = OmegaConf.load(def_config_path)

        # merge the two s.t. defaults are inserted where the base has no entries
        merged_conf = OmegaConf.merge(default_config, config)

        # perform some logic on the config
        self._preproc_cfg(merged_conf)

        # proceed to calculation
        calc = Calculation(merged_conf)
        calc.run()

    def _preproc_cfg(self, cfg: dict):
        # non parity specific option can be used if parity spefici one is not given
        # mr
        if (
            cfg["mr_scf"]["levels_per_j"] is not None
            and cfg["mr_scf"]["levels_per_j_even"] is None
        ):
            cfg["mr_scf"]["levels_per_j_even"] = cfg["mr_scf"]["levels_per_j"]
        if (
            cfg["mr_scf"]["levels_per_j"] is not None
            and cfg["mr_scf"]["levels_per_j_odd"] is None
        ):
            cfg["mr_scf"]["levels_per_j_odd"] = cfg["mr_scf"]["levels_per_j"]
        # as
        if (
            cfg["as_scf"]["levels_per_j"] is not None
            and cfg["as_scf"]["levels_per_j_even"] is None
        ):
            cfg["as_scf"]["levels_per_j_even"] = cfg["as_scf"]["levels_per_j"]
        if (
            cfg["as_scf"]["levels_per_j"] is not None
            and cfg["as_scf"]["levels_per_j_odd"] is None
        ):
            cfg["as_scf"]["levels_per_j_odd"] = cfg["as_scf"]["levels_per_j"]


def main():
    graspable_instance = GraspableMain()
    graspable_instance.main()


if __name__ == "__main__":
    main()
