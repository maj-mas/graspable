from .environment import Environment


class Calculation:
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg

        self.mpi = self.cfg["env"]["mpi"]["use"]
        self.mpi_invoke = self.cfg["env"]["mpi"]["invoke_cmd"]
        self.mem = self.cfg["env"]["mpi"]["mem"]

    def _setup_env(self):
        self.env = Environment(self.cfg)
        self.env.setup()

    def run(self):
        # set up the working / output directories, disks file etc. and change working directory to there
        self._setup_env()
