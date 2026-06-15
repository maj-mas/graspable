import os
from pathlib import Path


class Environment:
    """Sets up working folders, mpi temporary directories and configures the grasp executables to be used based on the config."""

    execs = {
        "rnucleus": "rnucleus",
        "rcsfgenerate": "rcsfgenerate",
        "rcsfsplit": "rcsfsplit",
        "rangular": "rangular",
        "rwfnestimate": "rwfnestimate",
        "rmcdhf": "rmcdhf",
        "rsave": "rsave",
        "rci": "rci",
        "jj2lsj": "jj2lsj",
        "rbiotransform": "rbiotransform",
        "rtransition": "rtransition",
        "rcsfinteract": "rcsfinteract",
    }  # TODO add missing ones
    mpi_prgs = [
        "rangular",
        "rmcdhf",
        "rci",
        "rbiotransform",
        "rtransition",
    ]  # these programs have mpi support
    graspg_prgs = [
        "rcsfgenerate",
        "rangular",
        "rwfnestimate",
        "rmcdhf",
        "rsave",
        "rci",
        "jj2lsj",
    ]  # these programs are in graspg

    def __init__(self, cfg: dict) -> None:
        """
        Raises:
            RuntimeError: Incorrect configuration related to graspg.
        """
        self.cfg = cfg["env"]

        if self.cfg["mpi"]["graspg"] and self.cfg["mpi"]["mem"]:
            raise RuntimeError("graspg and mem options are incompatible.")
        if self.cfg["mpi"]["graspg"] and not self.cfg["mpi"]["use"]:
            raise RuntimeError("graspg needs mpi.")

    def setup(self) -> dict:  # TODO test case if dirs correctly created
        """Creates the necessary directories and files for the calculation.

        Returns:
            dict: Dictionary containing executable paths from _setup_execs().
        """
        working_dir = Path(self.cfg["working_dir"])
        working_dir.mkdir(exist_ok=True, parents=True)

        # create a directory for program input files
        input_dir = working_dir / "input"
        input_dir.mkdir(exist_ok=True)
        # create a directory for program logs
        input_dir = working_dir / "log"
        input_dir.mkdir(exist_ok=True)

        output_dir = Path(self.cfg["output_dir"])
        output_dir.mkdir(exist_ok=True, parents=True)

        if self.cfg["mpi"]["use"]:
            tmp_dir = Path(self.cfg["mpi"]["tmp_dir"])
            tmp_dir.mkdir(exist_ok=True, parents=True)

            # make tmp dirs for mpi
            for i in range(self.cfg["mpi"]["n_p"]):
                tmp_subdir = tmp_dir / f"{i:03d}"
                tmp_subdir.mkdir(exist_ok=True)

            # set up disks file
            disks_path = working_dir / "disks"
            with open(disks_path, "w") as file:
                file.write(f'"{str(working_dir)}"\n')
                file.writelines(
                    f'"{str(tmp_dir)}"\n' for _i in range(self.cfg["mpi"]["n_p"])
                )

        # go to working dir
        os.chdir(working_dir)
        if self.cfg["clean"]:
            raise NotImplementedError("Clean not supported yet.")

        return self._setup_execs()

    def _setup_execs(self) -> dict:  # TODO test case wrong install path raises error
        """Checks for existence of executables, prepends absolute path and selects mpi versions if enables.

        Raises:
            RuntimeError: If an executable is missing from the GRASP installation.

        Returns:
            dict: Maps executable identifiers to absolute paths.
        """
        grasp_bin_path = Path(self.cfg["grasp_bin_path"])

        for identifier in self.execs.keys():
            # check for existence of program
            if not (grasp_bin_path / identifier).exists():
                raise RuntimeError(
                    f"Executable {identifier} not found in specified GRASP installation."
                )

            exec = identifier
            # setup graspg programs if enabled
            if (
                identifier in self.graspg_prgs
                and identifier not in self.mpi_prgs
                and self.cfg["mpi"]["graspg"]
            ):
                if exec == "rcsfgenerate":
                    exec = "rcsfggenerate_csfg"
                else:
                    exec += "_csfg"
                # check again for graspg programs, user might not have compiled graspg but requested it in config
                if not (grasp_bin_path / exec).exists():
                    raise RuntimeError(
                        f"Executable {exec} not found in specified GRASP installation."
                    )

            # setup mpi programs (and graspg if enabled)
            if identifier in self.mpi_prgs and self.cfg["mpi"]["use"]:
                exec = identifier
                if self.cfg["mpi"]["graspg"] and identifier in self.graspg_prgs:
                    exec += "_csfg_mpi"
                elif exec == "rmcdhf" and self.cfg["mpi"]["mem"]:
                    exec += "_mem_mpi"
                else:
                    exec += "_mpi"
                # check again for mpi programs, user might not have compiled with mpi but requested it in config
                if not (grasp_bin_path / exec).exists():
                    raise RuntimeError(
                        f"Executable {exec} not found in specified GRASP installation."
                    )
                # update program name
                self.execs[identifier] = exec
            # prepend path and invoker
            self.execs[identifier] = str(grasp_bin_path / exec)
            if identifier in self.mpi_prgs and self.cfg["mpi"]:
                self.execs[identifier] = (
                    self.cfg["mpi"]["invoke_cmd"] + " " + self.execs[identifier]
                )

        # also keep no mpi versions of these two (only used if not graspg due to incompatible file formats)
        self.execs["rmcdhf_nmpi"] = str(grasp_bin_path / "rmcdhf")
        self.execs["rangular_nmpi"] = str(grasp_bin_path / "rangular")

        return self.execs
