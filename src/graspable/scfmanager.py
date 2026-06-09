import subprocess
from .scf import SelfConsistentField
from .optimisation_strategy import AbstractOptimisationStrategy


class SCFManager:
    init_type_map = {
        "tf": 2,
        "screened_h": 3,
        "screened_h_z": 3,
    }

    def __init__(
        self,
        cfg: dict,
        execs: list[str],
        strategy: AbstractOptimisationStrategy,
        state: str,
        orbitals=list[str],
        type=str,
        id=str,
        mpi: bool = True,
    ) -> None:
        self.cfg = cfg
        self.execs = execs
        self.strategy_class = strategy
        self.state = state
        self.orbitals = orbitals

        self.type = type
        if type != "mr" and type != "as":
            raise RuntimeError(f"Invalid type {type} passed to SCFManager.")
        if type == "mr":
            self.orbitals_spectroscopic = "*"  # mr states need to be good
        if type == "as":
            self.orbitals_spectroscopic = (
                ""  # correlation states can have e.g. wrong # of nodes
            )

        self.id = id
        self.mpi = mpi

        if cfg["angular"]["full"]:
            self.rangular_input = "<<EOF\ny\nEOF"
        else:
            raise NotImplementedError(
                "Only full interaction at angular integration supported thus far."
            )  # TODO

    def run(self):
        cp_proc = subprocess.run([f"cp {self.state}.c rcsf.inp"], shell=True)
        if cp_proc.returncode != 0:
            raise RuntimeError(f"Error copying {self.state}.c to rcsf.inp")

        rangular_exec = (
            self.execs["rangular"] if self.mpi else self.execs["rangular_nmpi"]
        )
        rangular_proc = subprocess.run(
            [f"{rangular_exec} &> log/rangular_log_{self.state} {self.rangular_input}"],
            shell=True,
        )
        print(f"rangular completed with exit code {rangular_proc.returncode}.")

        strategy = self.strategy_class(self.orbitals)

        i = 0
        successful_run_exists = False
        optimize_orbitals = " ".join(strategy.next_set())
        scf = SelfConsistentField(
            execs=self.execs,
            orbitals_optimise=optimize_orbitals,
            orbitals_spectroscopic=self.orbitals_spectroscopic,
            run_name=self.id + str(i),
            levels_per_j=self.cfg[f"{self.type}_csf"]["levels_per_j"],
            mpi=self.mpi,
            init_type=self.init_type_map[self.cfg["orbital_init"]["type"]],
        )
        retcode = scf.run()
        if retcode == 0:
            successful_run_exists = True
            strategy.update_graph_multiple(optimize_orbitals.split(" "))
        else:
            strategy.update_graph_multiple(optimize_orbitals.split(" "), success=False)
        i = 1

        while not strategy.converged():
            optimize_orbitals = " ".join(strategy.next_set())
            print(f"Trying set {optimize_orbitals}.")
            scf = SelfConsistentField(
                execs=self.execs,
                orbitals_optimise=optimize_orbitals,
                orbitals_spectroscopic=self.orbitals_spectroscopic,
                run_name=self.id + str(i),
                levels_per_j=self.cfg[f"{self.type}_csf"]["levels_per_j"],
                mpi=self.mpi,
                init_type=self.init_type_map[self.cfg["orbital_init"]["type"]],
                init_run=self.id + str(i - 1) if successful_run_exists else None,
            )
            retcode = scf.run()
            if retcode == 0:
                successful_run_exists = True
                strategy.update_graph_multiple(optimize_orbitals.split(" "))
            else:
                strategy.update_graph_multiple(
                    optimize_orbitals.split(" "), success=False
                )

            i += 1

        # TODO option for a final run with "*"
