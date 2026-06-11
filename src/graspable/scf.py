import subprocess


class SelfConsistentField:
    def __init__(
        self,
        execs: list[str],
        orbitals_optimise: str,
        orbitals_spectroscopic: str,
        run_name: str,
        levels_per_j: int | list[int],
        mpi: bool = True,
        init_type: int = 3,
        init_run: str | None = None,
        custom_Z: float | None = None,
        n_iterations: int = 100,
    ) -> None:
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

    def _expand_orbitals_relativistic(self, orbitals: str):
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
        grep_proc = subprocess.run(
            'grep -c "*" rcsf.inp', shell=True, capture_output=True
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
        save_proc = subprocess.run(
            [f"{self.execs['rsave']} {state_name}"], shell=True, capture_output=True
        )
        if save_proc.returncode != 0:
            raise RuntimeError("Error during rsave.")

    def run(self) -> int:
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
