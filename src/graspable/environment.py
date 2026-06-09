from pathlib import Path
import os
import subprocess


class Environment:
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

    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg["env"]

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
                for i in range(self.cfg["mpi"]["n_p"]):
                    file.write(f'"{str(tmp_dir)}"\n')

        # go to working dir
        os.chdir(working_dir)
        if self.cfg["clean"]:
            subprocess.run(["rm *"], shell=True)  # TODO dangerous? ask user?

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
            # setup mpi programs
            if identifier in self.mpi_prgs and self.cfg["mpi"]:
                exec = identifier + (
                    "_mem_mpi"
                    if (identifier == "rmcdhf" and self.cfg["mpi"]["mem"])
                    else "_mpi"
                )
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

        # also keep no mpi versions of these two
        self.execs["rmcdhf_nmpi"] = str(grasp_bin_path / "rmcdhf")
        self.execs["rangular_nmpi"] = str(grasp_bin_path / "rangular")

        return self.execs
