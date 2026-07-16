import subprocess


class SelfConsistentField:
    """Performs a single rmcdhf run with specified parameters."""

    def __init__(
        self,
        execs: dict,
        exitcode_log: list,
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
        second_try_on_limit_reached: bool = False,
        dampen_factor: float | None = None,
    ) -> None:
        """Constructs a SelfConsistentField object.

        Args:
            execs (dict): Map of grasp commands
            exitcode_log (list): list that stores exitcodes of all CLI calls during the calculation
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
            second_try_on_limit_reached (bool, optional): Can be used to restart a calculation if it reaches the maximum number of iterations. Defaults to False.
        """
        self.execs = execs
        self.exitcode_log = exitcode_log
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
        self.second_try_on_limit_reached = second_try_on_limit_reached
        self.dampen_factor = dampen_factor
        if self.dampen_factor is not None:  # TODO unflexible
            self.non_default = True
        else:
            self.non_default = False

    def _expand_orbitals_relativistic(self, orbitals: str) -> str:
        """Converts non-relativistiv orbitals as e.g. 2p -> 2p* such that the + and - orbitals are included in grasp.

        Args:
            orbitals (str): String containing space-delimited orbitals.

        Returns:
            _type_: Space delimited string of orbitals with wild card appended.
        """
        if "*" in orbitals:
            return orbitals
        relativistic_orbitals = ""
        orbitals_l = orbitals.split(" ")
        first = True
        for orbital in orbitals_l:
            if first:
                if orbital[-1] == "s":
                    relativistic_orbitals += f"{orbital}"
                else:
                    relativistic_orbitals += f"{orbital}*"
            else:
                if orbital[-1] == "s":
                    relativistic_orbitals += f" {orbital}"
                else:
                    relativistic_orbitals += f" {orbital}*"
            first = False
        return relativistic_orbitals

    # TODO support non default options?
    def _create_rwfnestimate_input(self, fname: str, alt_init_run: str | None = None):
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
            elif alt_init_run is not None:
                file.write("1\n")
                file.write(alt_init_run + ".w\n")
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
            executable="/bin/bash",
            capture_output=True,
        )
        nblocks = int(grep_proc.stdout) + 1

        with open(fname, "w") as file:
            if self.non_default:
                file.write("n\n")  # non default options
                file.write("n\n")  # no debug output for now
                file.write("n\n")  # don't change grid or c for now
                file.write("n\n")  # don't change default accuracy for now
            else:
                file.write("y\n")  # no non default options
            for i in range(nblocks):
                if isinstance(self.levels_per_j, int):
                    n = self.levels_per_j
                else:
                    n = self.levels_per_j[i]
                file.write(f"{'1-' if n != 1 else ''}{n}\n")
            file.write("5\n")  # standard level weights TODO
            file.write(f"{self.orbitals_optimise}\n")
            file.write(f"{self.orbitals_spectroscopic}\n")
            file.write(f"{self.n_iterations}\n")
            if self.non_default:
                file.write("y\n")
                file.write("n\n")  # don't change oscillation treatment for now
                file.write("n\n")  # don't integration methods for now
                file.write(
                    "n\n"
                )  # don't change sign of wavefunctions at first oscillation for now
                file.write("y\n")  # accel params!
                file.write("n\n")  # all get the same for now
                file.write(f"{self.dampen_factor}\n")
                file.write("y\n")  # also dampening for evecs for now
                file.write("n\n")  # all get the same for now
                file.write(f"{self.dampen_factor}\n")
                file.write("n\n")  # don't change improv behaviour for now
                file.write("n\n")  # don't change maximum solution attempts for now
                file.write("n\n")  # don't change orthogonalisation for now
                file.write(
                    "2\n"
                )  # orthonormalisation order must be specified (self-consistency connected)

    def _save(self, state_name: str):
        """Saves the run last performed to disk.

        Args:
            state_name (str): Name to save state with.

        Raises:
            RuntimeError: Raised if rsave exits unsuccesfully.
        """
        save_proc = subprocess.run(
            [f"{self.execs['rsave']} {state_name}"],
            shell=True,
            executable="/bin/bash",
            capture_output=True,
        )
        if save_proc.returncode != 0:
            raise RuntimeError("Error during rsave.")
        self.exitcode_log.append({"rsave": save_proc.returncode})

    def _check_maxit_reached(self) -> bool:
        """Used to check if maximum number of iterations was reached.

        Returns:
            bool: True if reached, False else.
        """
        # count occurences of "Iteration number" in rmcdhf output
        grep_proc = subprocess.run(
            f'grep -c "Iteration number" log/rmcdhf_log_{self.run_name}',
            shell=True,
            executable="/bin/bash",
            capture_output=True,
        )
        n_actual_it = int(
            grep_proc.stdout
        )  # edge case: convergence in last step. but I deem this not so important.

        if n_actual_it >= self.n_iterations:
            return True
        return False

    def _one_run(self, alt_init_run: str | None = None) -> int:
        """Performs single SCF calculation.

        Raises:
            RuntimeError: Raised if rwfnestimate crashes.

        Returns:
            int: rmcdhf return code.
        """
        if alt_init_run is None:
            self._create_rwfnestimate_input(f"input/rwfnestimate_input_{self.run_name}")
        else:
            self._create_rwfnestimate_input(
                f"input/rwfnestimate_input_{self.run_name}", alt_init_run=alt_init_run
            )
        rwfnestimate_proc = subprocess.run(
            [
                f"{self.execs['rwfnestimate']} < input/rwfnestimate_input_{self.run_name} &> log/rwfnestimate_log_{self.run_name}"
            ],
            shell=True,
            executable="/bin/bash",
        )
        if rwfnestimate_proc.returncode != 0:
            raise RuntimeError("Error during rwfnestimate.")
        self.exitcode_log.append({"rwfnestimate": rwfnestimate_proc.returncode})

        self._create_rmcdhf_input(f"input/rmcdhf_input_{self.run_name}")
        rmcdhf_exec = self.execs["rmcdhf"] if self.mpi else self.execs["rmcdhf_nmpi"]
        rmcdhf_proc = subprocess.run(
            [
                f"{rmcdhf_exec} < input/rmcdhf_input_{self.run_name} &> log/rmcdhf_log_{self.run_name}"
            ],
            shell=True,
            executable="/bin/bash",
        )
        print(
            f"rmcdhf completed {'successfully.' if rmcdhf_proc.returncode == 0 else 'unsuccessfully, check logs if this occurs during active space calculation!'}"
        )
        self.exitcode_log.append({"rmcdhf": rmcdhf_proc.returncode})

        self._save(self.run_name)

        return rmcdhf_proc.returncode

    def run(self) -> int:
        """Must be called after initialisation. Performs one or, if maxit is reached and the option is enabled, two SCF runs.

        Returns:
            int: last rmcdhf return code
        """
        retcode = self._one_run()

        if self._check_maxit_reached():
            print(
                f"WARNING: Maximum number of iterations ({self.n_iterations}) reached during SCF procedure."
            )

            if retcode == 0 and self.second_try_on_limit_reached:
                print("Performing one additional try as configured...")

                retcode = self._one_run(alt_init_run=self.run_name)

                if self._check_maxit_reached():
                    print(
                        f"WARNING: Maximum number of iterations ({self.n_iterations}) reached AGAIN during SCF procedure."
                    )

        return retcode
