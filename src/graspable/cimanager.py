import subprocess
import math


class CIManager:
    """Class that performs configuration-interaction calculations on a given state."""

    def __init__(
        self,
        cfg: dict,
        execs: dict,
        levels_per_j: int | list[int],
        id: str,
        jj2lsj: bool = True,
    ) -> None:
        """Instantiates CIManager object.

        Args:
            cfg (dict): Configuration
            execs (dict): Map of grasp executables
            levels_per_j (int | list[int]):  Number of levels per symmetry block, applies either to all equally if int or can be specified per block if list[int].
            id (str): Name to save state as.
            jj2lsj (bool, optional): Whether to perform jj -> lsj label transformation. Defaults to True.
        """
        self.cfg = cfg["ci"]
        self.execs = execs
        self.qed_cfg = cfg["ci"]["qed"]
        self.levels_per_j = levels_per_j
        self.id = id
        self.jj2lsj = jj2lsj
        self.graspg = cfg["env"]["mpi"]["graspg"]
        self.n_p = cfg["env"]["mpi"]["n_p"]

    def _create_rci_input(self, fname: str, state: str, qed: bool = True):
        """Creates an input file for the configuration-interaction programs of grasp.

        Args:
            fname (str): Output file name
            state (str): Name of state
            qed (bool, optional): Whether to include QED. Defaults to True.
        """
        grep_proc = subprocess.run(
            f"grep -c '*' rcsf{'g' if self.graspg else ''}.inp",
            shell=True,
            capture_output=True,
        )
        nblocks = int(grep_proc.stdout) + 1

        with open(fname, "w") as file:
            file.write("y\n")  # TODO non-default options
            file.write(f"{state}\n")
            file.write(f"{'y' if self.qed_cfg['transverse'] and qed else 'n'}\n")
            file.write(
                f"{'y' if self.qed_cfg['transverse_all_freqs'] and qed else 'n'}\n"
            )
            file.write(
                self.qed_cfg["scale"] + "\n"
                if self.qed_cfg["transverse_all_freqs"] and qed
                else ""
            )
            file.write(f"{'y' if self.qed_cfg['vacpol'] and qed else 'n'}\n")
            file.write(f"{'y' if self.qed_cfg['normal_ms'] and qed else 'n'}\n")
            file.write(f"{'y' if self.qed_cfg['specific_ms'] and qed else 'n'}\n")
            file.write(f"{'y' if self.qed_cfg['se'] and qed else 'n'}\n")
            file.write(
                str(self.qed_cfg["n_se"]) + "\n" if self.qed_cfg["se"] and qed else ""
            )
            for i in range(nblocks):
                if isinstance(self.levels_per_j, int):
                    n = self.levels_per_j
                else:
                    n = self.levels_per_j[i]
                file.write(f"{n}\n")

    def _create_rci_input_csfg(self, fname: str, state: str, qed: bool = True):
        """Creates an input file for the configuration-interaction programs of graspg.

        Args:
            fname (str): Output file name
            state (str): Name of state
            qed (bool, optional): Whether to include QED. Defaults to True.

        Raises:
            RuntimeError: Raised if there is less than 1GB available per proc.
        """
        grep_proc = subprocess.run(
            f"grep -c '*' rcsf{'g' if self.graspg else ''}.inp",
            shell=True,
            capture_output=True,
        )
        nblocks = int(grep_proc.stdout) + 1

        # TODO graspg assumes that all nodes are equivalent here
        grep_proc = subprocess.run(
            "grep 'MemAvailable' /proc/meminfo", shell=True, capture_output=True
        )
        meminfo_split = grep_proc.stdout.split()
        mem_kb = int(meminfo_split[1])
        mem_gb = mem_kb / 1024 / 1024
        mem_per_proc = math.floor(
            mem_gb / self.n_p
        )  # must be an integer, this may lead to suboptimal memory usage if not neatly divisible
        if mem_per_proc == 0:
            raise RuntimeError(
                f"n_p={self.n_p} and free memory {mem_gb} lead to zero GB per proc when rounded down. Reduce number of threads."
            )

        with open(fname, "w") as file:
            file.write("y\n")  # TODO non-default options
            file.write(f"{state}\n")
            file.write(f"{'y' if self.qed_cfg['transverse'] and qed else 'n'}\n")
            file.write(
                f"{'y' if self.qed_cfg['transverse_all_freqs'] and qed else 'n'}\n"
            )
            file.write(
                self.qed_cfg["scale"] + "\n"
                if self.qed_cfg["transverse_all_freqs"] and qed
                else ""
            )
            # graspg specific options, TODO hardcoded for now
            file.write("n\n")  # limit breit n
            file.write("100\n")  # limit breit n
            file.write("n\n")  # limit breit l
            file.write("100\n")  # limit breit l
            file.write(f"{'y' if self.qed_cfg['vacpol'] and qed else 'n'}\n")
            file.write(f"{'y' if self.qed_cfg['normal_ms'] and qed else 'n'}\n")
            file.write(f"{'y' if self.qed_cfg['specific_ms'] and qed else 'n'}\n")
            file.write(f"{'y' if self.qed_cfg['se'] and qed else 'n'}\n")
            file.write(
                str(self.qed_cfg["n_se"])
                if self.qed_cfg["n_se"] is not None
                else str(3) + "\n"
            )
            file.write(str(mem_per_proc) + "\n")
            for i in range(nblocks):
                if isinstance(self.levels_per_j, int):
                    n = self.levels_per_j
                else:
                    n = self.levels_per_j[i]
                file.write(f"{n}\n")

    def _create_jj2lsj_input(self, fname: str, state: str):
        with open(fname, "w") as file:
            file.write(state + "\n")
            file.write("y\n")
            file.write("y\n")
            file.write("y\n")  # TODO non default

    def run(self):
        """Performs the CI calculation. Must be called after initialisation."""
        if self.qed_cfg["with_and_without"]:
            subprocess.run(
                [
                    f"cp {self.id}.{'c' if not self.graspg else 'g'} {self.id}CI_noqed.{'c' if not self.graspg else 'g'}"
                ],
                shell=True,
                capture_output=True,
            )
            subprocess.run(
                [f"cp {self.id}.w {self.id}CI_noqed.w"], shell=True, capture_output=True
            )
            if self.graspg:
                subprocess.run(
                    [f"cp {self.id}.l {self.id}CI_noqed.l"],
                    shell=True,
                    capture_output=True,
                )
            if not self.graspg:
                self._create_rci_input(
                    f"input/rci_input_{self.id}_noqed", f"{self.id}CI_noqed", qed=False
                )
            else:
                self._create_rci_input_csfg(
                    f"input/rci_input_{self.id}_noqed", f"{self.id}CI_noqed", qed=False
                )

        subprocess.run(
            [
                f"cp {self.id}.{'c' if not self.graspg else 'g'} {self.id}CI.{'c' if not self.graspg else 'g'}"
            ],
            shell=True,
            capture_output=True,
        )
        subprocess.run(
            [f"cp {self.id}.w {self.id}CI.w"], shell=True, capture_output=True
        )
        if self.graspg:
            subprocess.run(
                [f"cp {self.id}.l {self.id}CI.l"], shell=True, capture_output=True
            )
        if not self.graspg:
            self._create_rci_input(f"input/rci_input_{self.id}", f"{self.id}CI")
        else:
            self._create_rci_input_csfg(f"input/rci_input_{self.id}", f"{self.id}CI")

        if self.qed_cfg["with_and_without"]:
            print("Performing extra CI step without QED...")
            rci_noqedproc = subprocess.run(
                [
                    f"{self.execs['rci']} < input/rci_input_{self.id}_noqed &> log/rci_log_{self.id}_noqed"
                ],
                shell=True,
            )
            print(f"rci completed with exit code {rci_noqedproc.returncode}.")
            print("...done, moving to regular CI.")

        rciproc = subprocess.run(
            [
                f"{self.execs['rci']} < input/rci_input_{self.id} &> log/rci_log_{self.id}"
            ],
            shell=True,
        )
        print(f"rci completed with exit code {rciproc.returncode}.")

        if self.jj2lsj:
            if self.qed_cfg["with_and_without"]:
                self._create_jj2lsj_input(
                    f"input/jj2lsj_input_{self.id}_noqed", f"{self.id}CI_noqed"
                )
                jj2lsjproc = subprocess.run(
                    [
                        f"{self.execs['jj2lsj']} < input/jj2lsj_input_{self.id}_noqed &> log/jj2lsj_log_{self.id}_noqed"
                    ],
                    shell=True,
                )
                print(f"jj2lsj completed with exit code {jj2lsjproc.returncode}.")
            self._create_jj2lsj_input(f"input/jj2lsj_input_{self.id}", f"{self.id}CI")
            jj2lsjproc = subprocess.run(
                [
                    f"{self.execs['jj2lsj']} < input/jj2lsj_input_{self.id} &> log/jj2lsj_log_{self.id}"
                ],
                shell=True,
            )
            print(f"jj2lsj completed with exit code {jj2lsjproc.returncode}.")
