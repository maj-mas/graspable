from .environment import Environment
from .nuclear import Nuclear
from .csfmanager import CSFManager


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

    def run(self):
        print(f"Starting calculation {self.cfg['meta']['name']}...")
        # set up the working / output directories, disks file etc. and change working directory to there
        self._setup_env()

        # set up nucleus
        self._setup_nuclear()

        # generate csfs
        self._generate_csfs()
