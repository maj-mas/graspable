import subprocess
from .optimisation_strategy import TestStrategy


class SelfConsistentField:
    def __init__(
        self, cfg: dict, execs: list[str], cfg_key: str, mpi: bool = True
    ) -> None:
        self.cfg_orbital_init = cfg["orbital_init"]
        self.cfg = cfg[cfg_key]
        self.execs = execs
        self.mpi = mpi
        self.strategy = TestStrategy()

    def run(self):
        pass
