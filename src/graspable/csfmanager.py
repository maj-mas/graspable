import subprocess


class CSFManager:
    def __init__(self, cfg: dict, execs: dict) -> None:
        self.cfg = cfg["states"]
        self.execs = execs

    def _create_rcsfgenerate_input(self, name: str, states: list[str]):
        with open(f"input/{name}", "w") as file:
            file.write("*\n")
            file.write("0")

    def _gen_mr(self):
        pass

    def _gen_as(self):
        pass

    def _split_as(self):
        pass

    def setup(self):
        pass

    # TODO add zero/first order split
    # TODO add rcsfinteract reduction
