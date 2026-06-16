import subprocess


class SelfConsistentField:
    """Performs a single rmcdhf run with specified parameters."""

    def __init__(
        self,
        execs: dict,
        orbitals_optimise: str,
        orbitals_spectroscopic: str,
        run_name: str,
        levels_per_j: int | list[int],
        mpi: bool = True,
        init_type: int = 3,
        init_run: str | None = None,
        custom_Z: float | None = None,
        n_iterations: int = 100,
        graspg: bool = False,
    ) -> None:
        """Constructs a SelfConsistentField object.

        Args:
            execs (dict): Map of grasp commands
            orbitals_optimise (str): String containing orbitals to optimise.
            orbitals_spectroscopic (str): String containing orbitals to optimise that are also spectroscopic, i.e. node-counting is enforced.
            run_name (str): Name of run to save it to disk with.
            levels_per_j (int | list[int]): Number of levels per symmetry block, applies either to all equally if int or can be specified per block if list[int].
            mpi (bool, optional): Whether to use mpi, must be true for graspg. Defaults to True.
            init_type (int, optional): Orbital initialisation method. 1: From file (requires all orbitals present in init_run), 2: Thomas-Fermi, 3: Screened Hydrogenic, 4: Screened hydrogenig (custom Z), required custom_Z. Defaults to 3.
            init_run (str | None, optional): Run to use for orbital initialisation. If this is set, orbitals are taken from file and init_type is only used for the remaining ones. Defaults to None.
            custom_Z (float | None, optional): Z offset for custom Z orbital initialisation. Defaults to None.
            n_iterations (int, optional): Max number of SCF steps. Defaults to 100.
            graspg (bool, optional): Whether to use graspg. Defaults to False.
        """
        self.execs = execs
        self.orbitals_optimise = self._expand_orbitals_relativistic(orbitals_optimise)
        self.orbitals_spectroscopic = orbitals_spectroscopic
        self.run_name = run_name
        self.levels_per_j = levels_per_j
        self.mpi = mpi
        self.init_run = init_run
        self.init_type = init_type
        self.custom_Z = custom_Z
        self.n_iterations = n_iterations
        self.graspg = graspg

    def _expand_orbitals_relativistic(self, orbitals: str) -> str:
        """Converts non-relativistiv orbitals as e.g. 2p -> 2p* such that the + and - orbitals are included in grasp.

        Args:
            orbitals (str): String containing space-delimited orbitals.

        Returns:
            _type_: Space delimited string of orbitals with wild card appended.
        """
        if orbitals == "*":
            return orbitals
        relativistic_orbitals = ""
        orbitals_l = orbitals.split(" ")
        for orbital in orbitals_l:
            if orbital[-1] == "s":
                relativistic_orbitals += f" {orbital}"
            else:
                relativistic_orbitals += f" {orbital}*"
        return relativistic_orbitals

    # TODO support non default options?
    def _create_rwfnestimate_input(self, fname: str):
        """Creates an input file for the wave function estimation programs of grasp(g).

        Args:
            fname (str): Output filename.

        Raises:
            RuntimeError: Raised if init_type is 1 (from file) but no file was passed.
            RuntimeError: Raised if init_type is 4 (custom Z) but custom_Z was not passed.
        """
        with open(fname, "w") as file:
            file.write("y\n")
            if self.init_run is not None:
                file.write("1\n")
                file.write(self.init_run + ".w\n")
                file.write("*\n")
                file.write(f"{self.init_type}\n")
                file.write("*\n")
            else:
                if self.init_type == 1:
                    raise RuntimeError(
                        "Orbital initialisation type is 1 but no file was given."
                    )
                if self.init_type == 4:
                    if self.custom_Z is None:
                        raise RuntimeError(
                            "Custom Z orbital initialisation requested but no custom Z was given."
                        )
                    file.write(f"{self.init_type}\n")
                    file.write("*\n")
                    file.write(f"{self.custom_Z}\n")
                else:
                    file.write(f"{self.init_type}\n")
                    file.write("*\n")

    def _create_rmcdhf_input(self, fname: str):
        """Creates an input file for the SCF programs of grasp(g).

        Args:
            fname (str): Output filename.
        """
        grep_proc = subprocess.run(
            f"grep -c '*' rcsf{'g' if self.graspg else ''}.inp",
            shell=True,
            capture_output=True,
        )
        nblocks = int(grep_proc.stdout) + 1

        with open(fname, "w") as file:
            file.write("y\n")  # TODO non default options
            for i in range(nblocks):
                if isinstance(self.levels_per_j, int):
                    n = self.levels_per_j
                else:
                    n = self.levels_per_j[i]
                file.write(f"{n}\n")
            file.write("5\n")  # standard level weights TODO
            file.write(f"{self.orbitals_optimise}\n")
            file.write(f"{self.orbitals_spectroscopic}\n")
            file.write(f"{self.n_iterations}\n")

    def _save(self, state_name: str):
        """Saves the run last performed to disk.

        Args:
            state_name (str): Name to save state with.

        Raises:
            RuntimeError: Raised if rsave exits unsuccesfully.
        """
        save_proc = subprocess.run(
            [f"{self.execs['rsave']} {state_name}"], shell=True, capture_output=True
        )
        if save_proc.returncode != 0:
            raise RuntimeError("Error during rsave.")

    def run(self) -> int:
        """Performs single SCF calculation. Must be called after initialisation.

        Raises:
            RuntimeError: Raised if rwfnestimate crashes.

        Returns:
            int: rmcdhf return code.
        """
        self._create_rwfnestimate_input(f"input/rwfnestimate_input_{self.run_name}")
        rwfnestimate_proc = subprocess.run(
            [
                f"{self.execs['rwfnestimate']} < input/rwfnestimate_input_{self.run_name} &> log/rwfnestimate_log_{self.run_name}"
            ],
            shell=True,
        )
        if rwfnestimate_proc.returncode != 0:
            raise RuntimeError("Error during rwfnestimate.")

        self._create_rmcdhf_input(f"input/rmcdhf_input_{self.run_name}")
        rmcdhf_exec = self.execs["rmcdhf"] if self.mpi else self.execs["rmcdhf_nmpi"]
        rmcdhf_proc = subprocess.run(
            [
                f"{rmcdhf_exec} < input/rmcdhf_input_{self.run_name} &> log/rmcdhf_log_{self.run_name}"
            ],
            shell=True,
        )
        print(f"rmcdhf completed with exit code {rmcdhf_proc.returncode}.")

        self._save(self.run_name)

        return rmcdhf_proc.returncode
