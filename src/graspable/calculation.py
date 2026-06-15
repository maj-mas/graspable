from datetime import datetime

from .cimanager import CIManager
from .csfmanager import CSFManager
from .environment import Environment
from .nuclear import Nuclear
from .optimisation_strategy import RandomStrategy, SuccessiveStrategy
from .scfmanager import SCFManager
from .transition import Transition
from .cleanup import Clean


class Calculation:
    """Performs a GRASP calculation defined completely by a dictionary containing config entries. For documentation of the config keys and their valid values, see the default empty config shipped with the code.

    Note that all config entries must be present to ensure no crashes. If a Calculation object is created in the Main class by claling graspable from the command line, default values from the empty config are inserted so that non-required values can be omitted.
    """

    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg

        self.mpi = self.cfg["env"]["mpi"]["use"]
        self.mpi_invoke = self.cfg["env"]["mpi"]["invoke_cmd"]
        self.mem = self.cfg["env"]["mpi"]["mem"]

        self.time = datetime.now()
        self.init_time = datetime.now()

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
        parities = ["even", "odd"]
        states = ["mr_even", "mr_odd"]
        orbitals_l = [self.csfman.orbitals_even, self.csfman.orbitals_odd]
        for parity, state, orbitals in zip(parities, states, orbitals_l, strict=True):
            print(f"Performing SCF procedure for {parity} multireference...")
            self.csfmr = SCFManager(
                self.cfg,
                self.execs,
                strategy=RandomStrategy,
                state=state,
                orbitals=orbitals,
                type="mr",
                id=state,
                mpi=True
                if self.cfg["env"]["mpi"]["graspg"]
                else False,  # g only has mpi
                final_star_run=True,
            )
            self.csfmr.run()
            print(f"... done. {(datetime.now() - self.time).total_seconds()} s\n")
            self.time = datetime.now()

    def _as_scf(self):
        n_min = self.csfman.n_min
        n_max = self.csfman.n_max

        prev_prefix = "mr_"
        prev_suffix = "_all"
        for n in range(n_min, n_max + 1):
            for parity in ["even", "odd"]:
                print(
                    f"Performing active space SCF procedure up to n={n} for {parity} parity..."
                )
                prev_state = prev_prefix + parity + prev_suffix
                state = f"as_{parity}{n}"
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
        if self.cfg["ci"]["as_expansion"]:
            n_min = self.csfman.n_min
            n_max = self.csfman.n_max
        else:
            n_min = self.csfman.n_max
            n_max = n_min + 1

        for n in range(n_min, n_max + 1):
            for parity in ["even", "odd"]:
                print(f"Performing CI calculation up to n={n} for {parity} parity...")
                orbitals = self.csfman.active_orbitals_given_n(n)
                state = f"as_{parity}{n}{len(orbitals) + 1 - 1}"
                self.ci = CIManager(
                    self.cfg,
                    self.execs,
                    self.cfg["as_csf"]["levels_per_j"],
                    id=state,
                )
                self.ci.run()
                print(f"... done. {(datetime.now() - self.time).total_seconds()} s\n")
                self.time = datetime.now()

    def _trans(self):
        print("Performing transition calculation...")

        n = self.csfman.n_max
        orbitals = self.csfman.active_orbitals_given_n(n)
        state_even = f"as_even{n}{len(orbitals) + 1 - 1}CI"
        state_odd = f"as_odd{n}{len(orbitals) + 1 - 1}CI"

        self.trans = Transition(self.cfg, self.execs, state_even, state_odd)
        self.trans.run()
        print(f"... done. {(datetime.now() - self.time).total_seconds()} s\n")
        self.time = datetime.now()

    def _cleanup(self):
        print("Performing cleanup...")
        self.cleaner = Clean(self.cfg)
        self.cleaner.clean()
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

        # transition
        self._trans()

        # perform cleanup
        self._cleanup()

        print(f"All complete. {(datetime.now() - self.init_time).total_seconds()} s\n")
