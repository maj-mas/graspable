from .environment import Environment
from .nuclear import Nuclear
from .csfmanager import CSFManager
from .scfmanager import SCFManager
from .optimisation_strategy import RandomStrategy


class Calculation:
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg

        self.mpi = self.cfg["env"]["mpi"]["use"]
        self.mpi_invoke = self.cfg["env"]["mpi"]["invoke_cmd"]
        self.mem = self.cfg["env"]["mpi"]["mem"]

    def _setup_env(self):
        print(
            "Creating working directory structure and looking for GRASP installation..."
        )
        self.env = Environment(self.cfg)
        self.execs = self.env.setup()
        print("... done.")

    def _setup_nuclear(self):
        print("Creating nuclear data...")
        self.nuclear = Nuclear(self.cfg, self.execs)
        self.nuclear.setup()
        print("...done.")

    def _generate_csfs(self):
        print("Generating lists of CSFs...")
        self.cfsman = CSFManager(self.cfg, self.execs)
        self.cfsman.setup()
        print("...done.")

    def _mr_scf(self):
        print("Performing SCF procedure for even multireference...")
        self.csfmr_even = SCFManager(
            self.cfg,
            self.execs,
            strategy=RandomStrategy,
            state="mr_even",
            orbitals=self.cfsman.orbitals_even,
            type="mr",
            id="mr_even",
            mpi=False,
        )
        self.csfmr_even.run()
        print("..done.")

        print("Performing SCF procedure for odd multireference...")
        self.csfmr_odd = SCFManager(
            self.cfg,
            self.execs,
            strategy=RandomStrategy,
            state="mr_odd",
            orbitals=self.cfsman.orbitals_odd,
            type="mr",
            id="mr_odd",
            mpi=False,
        )
        self.csfmr_odd.run()
        print("..done.")

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
