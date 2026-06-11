from datetime import datetime

from .environment import Environment
from .nuclear import Nuclear
from .csfmanager import CSFManager
from .scfmanager import SCFManager
from .optimisation_strategy import RandomStrategy, SuccessiveStrategy
from .cimanager import CIManager


class Calculation:
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg

        self.mpi = self.cfg["env"]["mpi"]["use"]
        self.mpi_invoke = self.cfg["env"]["mpi"]["invoke_cmd"]
        self.mem = self.cfg["env"]["mpi"]["mem"]

        self.time = datetime.now()

    def _setup_env(self):
        print(
            "Creating working directory structure and looking for GRASP installation..."
        )
        self.env = Environment(self.cfg)
        self.execs = self.env.setup()
        print(f"... done. {(datetime.now() - self.time).total_seconds()} s\n")
        self.time = datetime.now()

    def _setup_nuclear(self):
        print("Creating nuclear data...")
        self.nuclear = Nuclear(self.cfg, self.execs)
        self.nuclear.setup()
        print(f"... done. {(datetime.now() - self.time).total_seconds()} s\n")
        self.time = datetime.now()

    def _generate_csfs(self):
        print("Generating lists of CSFs...")
        self.csfman = CSFManager(self.cfg, self.execs)
        self.csfman.setup()
        print(f"... done. {(datetime.now() - self.time).total_seconds()} s\n")
        self.time = datetime.now()

    def _mr_scf(self):  # TODO more graceful behaviour if no even or odd state
        print("Performing SCF procedure for even multireference...")
        self.csfmr_even = SCFManager(
            self.cfg,
            self.execs,
            strategy=RandomStrategy,
            state="mr_even",
            orbitals=self.csfman.orbitals_even,
            type="mr",
            id="mr_even",
            mpi=False,
            final_star_run=True,
        )
        self.csfmr_even.run()
        print(f"... done. {(datetime.now() - self.time).total_seconds()} s\n")
        self.time = datetime.now()

        print("Performing SCF procedure for odd multireference...")
        self.csfmr_odd = SCFManager(
            self.cfg,
            self.execs,
            strategy=RandomStrategy,
            state="mr_odd",
            orbitals=self.csfman.orbitals_odd,
            type="mr",
            id="mr_odd",
            mpi=False,
            final_star_run=True,
        )
        self.csfmr_odd.run()
        print(f"... done. {(datetime.now() - self.time).total_seconds()} s\n")
        self.time = datetime.now()

    def _as_scf(self):
        if self.cfg["states"]["split"]:
            n_sets = self.csfman.n_sets
            n_min = self.csfman.n_min
            n_max = self.csfman.n_max
        else:
            n_sets = 1
            n_min = (0,)
            n_max = 1

        prev_prefix = "mr_"
        prev_suffix = "_all"
        for n in range(n_min, n_max + 1):
            for parity in ["even", "odd"]:
                print(
                    f"Performing active space SCF procedure up to n={n} for {parity} parity..."
                )
                prev_state = prev_prefix + parity + prev_suffix
                state = f"as_{parity}{n}"
                # orbitals = " ".join(self.csfman.active_orbitals_given_n(n))
                orbitals = self.csfman.active_orbitals_given_n(n)
                orbitals.append(f"{n}*")
                print(orbitals)
                self.csfas = SCFManager(
                    self.cfg,
                    self.execs,
                    strategy=SuccessiveStrategy,
                    state=state,
                    orbitals=orbitals,
                    type="as",
                    id=state,
                    mpi=True,
                    init_run=prev_state,
                    final_star_run=False,
                )
                self.csfas.run()
                print(f"... done. {(datetime.now() - self.time).total_seconds()} s\n")
                self.time = datetime.now()
            prev_prefix = "as_"
            prev_suffix = str(n)

    def _as_ci(self):
        if self.cfg["states"]["split"] and self.cfg["ci"]["as_expansion"]:
            n_min = self.csfman.n_min
            n_max = self.csfman.n_max
        else:
            n_min = self.csfman.n_max
            n_max = n_min + 1

        for n in range(n_min, n_max + 1):
            for parity in ["even", "odd"]:
                print(f"Performing CI calculation up to n={n} for {parity} parity...")
                orbitals = self.csfman.active_orbitals_given_n(n)
                state = f"as_{parity}{n}{len(orbitals)+1-1}"
                self.ci = CIManager(
                    self.cfg,
                    self.execs,
                    self.cfg["as_csf"]["levels_per_j"],
                    id=state,
                )
                self.ci.run()
                print(f"... done. {(datetime.now() - self.time).total_seconds()} s\n")
                self.time = datetime.now()

    def run(self):
        print(f"Starting calculation {self.cfg['meta']['name']}...")
        # set up the working / output directories, disks file etc. and change working directory to there
        self._setup_env()

        # set up nucleus
        self._setup_nuclear()

        # generate csfs
        self._generate_csfs()

        # do scf for mr
        self._mr_scf()

        # do scf for as
        self._as_scf()

        # do ci
        self._as_ci()
