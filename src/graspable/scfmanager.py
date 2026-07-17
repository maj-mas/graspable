import subprocess

from .optimisation_strategy import AbstractOptimisationStrategy
from .scf import SelfConsistentField


class SCFManager:
    """Class that performs self-consistent field calculations on a given state following an implementation of AbstractOptimisationStrategy that determines the order of orbital optimisation."""

    init_type_map = {
        "tf": 2,
        "screened_h": 3,
        "screened_h_z": 3,
    }

    def __init__(
        self,
        cfg: dict,
        execs: dict,
        exitcode_log: list,
        strategy: AbstractOptimisationStrategy,
        state: str,
        orbitals: list[str],
        type: str,
        id: str,
        mpi: bool = True,
        init_run: str | None = None,
        final_star_run: bool = False,
        run_limit: int = 100,
    ) -> None:
        """Constructs an SCFManager instance.

        Args:
            cfg (dict): Config
            execs (dict): Map of grasp commands
            exitcode_log (list): list that stores exitcodes of all CLI calls during the calculation
            strategy (AbstractOptimisationStrategy): Orbital optimisation strategy that produces consequent sets of orbitals to optimise together and checks for convergence.
            state (str): name of state on disk
            orbitals (list[str]): Orbitals to include in optimisation
            type (str): "mr" or "as" depending on whether the calculation is performed for the only multireference or for the active space.
            id (str): TODO same as state, rm
            mpi (bool, optional): Whether mpi is used (note: if graspg is enabled, mpi must always be on). Defaults to True.
            init_run (str | None, optional): Unsued? TODO rm. Defaults to None.
            final_star_run (bool, optional): Whether to perform a final SCF calculation for all orbitals in orbitals. Defaults to False.
            run_limit (int, optional): Maximum number of calls to rmcdhf. Defaults to 100.

        Raises:
            RuntimeError: Raised if type is not "as" or "mr".
        """
        self.cfg = cfg
        self.execs = execs
        self.exitcode_log = exitcode_log
        self.strategy_class = strategy
        self.state = state
        self.orbitals = orbitals

        self.active_orbitals = cfg["states"]["active"].split(" ")

        self.type = type
        if type != "mr" and type != "as":
            raise RuntimeError(f"Invalid type {type} passed to SCFManager.")
        if type == "mr":
            self.orbitals_spectroscopic = "*"  # mr states need to be good
            self.maxit = self.cfg["mr_csf"]["maxit"]
            self.restart_on_maxit_reached = False
            self.dampen_factor = self.cfg["mr_csf"]["dampen_factor"]
        if type == "as":
            self.orbitals_spectroscopic = ""
            self.maxit = self.cfg["as_csf"]["maxit"]
            self.restart_on_maxit_reached = self.cfg["as_csf"][
                "restart_on_maxit_reached"
            ]
            self.dampen_factor = self.cfg["as_csf"]["dampen_factor"]

        self.id = id
        self.mpi = mpi
        self.init_run = init_run
        self.final_star_run = final_star_run
        self.run_limit = run_limit

        if cfg["angular"]["full"]:
            self.rangular_input = "<<EOF\ny\nEOF"  # rangular only takes a single input
        else:
            raise NotImplementedError(
                "Only full interaction at angular integration supported thus far."
            )  # TODO

        self.graspg = cfg["env"]["mpi"]["graspg"]

    def run(self):
        """Runs the SCF procedure. Must be called after initialisation.

        Raises:
            RuntimeError: Raised if input files not found on disk.
            RuntimeError: Raised if no convergence is reached within the specified number of calls to rmcdhf.
            RuntimeError: Raised if the final * run does not converge.
        """
        cp_proc = subprocess.run(
            [
                f"cp {self.state}.{'g' if self.graspg else 'c'} rcsf{'g' if self.graspg else ''}.inp"
            ],
            shell=True,
            executable="/bin/bash",
        )
        self.exitcode_log.append({"cp": cp_proc.returncode})
        if cp_proc.returncode != 0:
            raise RuntimeError(
                f"Error copying {self.state}.{'g' if self.graspg else 'c'} to rcsf{'g' if self.graspg else ''}.inp"
            )
        if self.graspg:
            cp_proc = subprocess.run(
                [f"cp {self.state}.l rlabel.inp"], shell=True, executable="/bin/bash"
            )
            if cp_proc.returncode != 0:
                raise RuntimeError(f"Error copying {self.state}.l to rlabel.inp")
            self.exitcode_log.append({"cp": cp_proc.returncode})

        rangular_exec = (
            self.execs["rangular"] if self.mpi else self.execs["rangular_nmpi"]
        )
        rangular_proc = subprocess.run(
            [f"{rangular_exec} &> log/rangular_log_{self.state} {self.rangular_input}"],
            shell=True,
            executable="/bin/bash",
        )
        print(
            f"rangular completed {'successfully.' if rangular_proc.returncode == 0 else 'unsuccessfully, check logs!'}"
        )

        strategy = self.strategy_class(self.orbitals)

        i = 0
        successful_run_exists = False
        optimize_orbitals = " ".join(strategy.next_set())
        # fix for additional unoccupied labelling space orbitals present in mr calculations with graspg
        if self.type == "mr":
            orbitals_spectroscopic = optimize_orbitals
        else:
            orbitals_spectroscopic = self.orbitals_spectroscopic
        print(f"Trying set {optimize_orbitals}.")
        scf = SelfConsistentField(
            execs=self.execs,
            exitcode_log=self.exitcode_log,
            orbitals_optimise=optimize_orbitals,
            orbitals_spectroscopic=orbitals_spectroscopic,
            run_name=self.id + str(i),
            levels_per_j=self.cfg[f"{self.type}_csf"]["levels_per_j"],
            mpi=self.mpi,
            init_type=self.init_type_map[self.cfg["orbital_init"]["type"]],
            init_run=self.init_run,
            n_iterations=self.maxit,
            graspg=self.graspg,
            second_try_on_limit_reached=self.restart_on_maxit_reached,
            dampen_factor=self.dampen_factor,
        )
        retcode = scf.run()
        if retcode == 0:
            successful_run_exists = True
            strategy.update_graph_multiple(optimize_orbitals.split(" "))
        else:
            strategy.update_graph_multiple(optimize_orbitals.split(" "), success=False)
        i = 1

        last_successful_run = None
        while not strategy.converged():
            optimize_orbitals = " ".join(strategy.next_set())
            # fix for additional unoccupied labelling space orbitals present in mr calculations with graspg
            if self.type == "mr":
                orbitals_spectroscopic = optimize_orbitals
            else:
                orbitals_spectroscopic = self.orbitals_spectroscopic
            print(f"Trying set {optimize_orbitals}.")
            run_name = (
                self.id + str(i) if optimize_orbitals != "*" else self.id + "_all"
            )
            # dont keep bad orbitals !?
            init_run = None
            if successful_run_exists and self.type == "as":
                init_run = self.id + str(i - 1)
            elif successful_run_exists and self.type == "mr":
                init_run = (
                    self.id + str(i - 1)
                    if last_successful_run is None
                    else last_successful_run
                )
            scf = SelfConsistentField(
                execs=self.execs,
                exitcode_log=self.exitcode_log,
                orbitals_optimise=optimize_orbitals,
                orbitals_spectroscopic=orbitals_spectroscopic,
                run_name=run_name,
                levels_per_j=self.cfg[f"{self.type}_csf"]["levels_per_j"],
                mpi=self.mpi,
                init_type=self.init_type_map[self.cfg["orbital_init"]["type"]],
                init_run=init_run,
                n_iterations=self.maxit,
                graspg=self.graspg,
                second_try_on_limit_reached=self.restart_on_maxit_reached,
                dampen_factor=self.dampen_factor,
            )
            retcode = scf.run()
            if retcode == 0:
                successful_run_exists = True
                strategy.update_graph_multiple(optimize_orbitals.split(" "))
                last_successful_run = self.id + str(i - 1)
            else:
                strategy.update_graph_multiple(
                    optimize_orbitals.split(" "), success=False
                )

            i += 1
            if i > self.run_limit:
                raise RuntimeError(
                    "After {i} SCF runs, no convergence was reached. Try changing the optimisation strategy."
                )

        if self.final_star_run:
            optimize_orbitals = "*"
            print(f"Trying set {optimize_orbitals}.")
            scf = SelfConsistentField(
                execs=self.execs,
                exitcode_log=self.exitcode_log,
                orbitals_optimise=optimize_orbitals,
                orbitals_spectroscopic=self.orbitals_spectroscopic,
                run_name=self.id + "_all",
                levels_per_j=self.cfg[f"{self.type}_csf"]["levels_per_j"],
                mpi=self.mpi,
                init_type=self.init_type_map[self.cfg["orbital_init"]["type"]],
                init_run=self.id + str(i - 1) if successful_run_exists else None,
                n_iterations=self.maxit,
                graspg=self.graspg,
                second_try_on_limit_reached=self.restart_on_maxit_reached,
                dampen_factor=self.dampen_factor,
            )
            retcode = scf.run()
            if retcode == 0:
                successful_run_exists = True
                strategy.update_graph_multiple(optimize_orbitals.split(" "))
            else:
                raise RuntimeError("Final * run of SFC failed.")
