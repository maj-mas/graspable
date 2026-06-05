from pathlib import Path
import os


class Environment:
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg["env"]

    def setup(self):
        """Creates the necessary directories and files for the calculation."""
        working_dir = Path(self.cfg["working_dir"])
        working_dir.mkdir(exist_ok=True, parents=True)

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
