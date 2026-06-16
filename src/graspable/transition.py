import subprocess


class Transition:
    def __init__(
        self,
        cfg: dict,
        execs: dict,
        state_even: str | None = None,
        state_odd: str | None = None,
    ) -> None:
        self.cfg = cfg["trans"]
        self.execs = execs
        if state_even is None and state_odd is None:
            raise RuntimeError("Transition calculation begun but no states were given.")
        self.state_even = state_even
        self.state_odd = state_odd
        self.multipoles = self.cfg["multipoles"]

    def _create_rbiotransform_input(self, fname: str, instate: str, outstate: str):
        with open(fname, "w") as file:
            file.write("y\n")  # TODO non default options
            file.write("y\n")  # always with ci
            file.write(instate + "\n")
            file.write(outstate + "\n")
            file.write("y\n")

    def _create_rtransition_input(
        self, fname: str, instate: str, outstate: str, multipoles: list[str]
    ):
        with open(fname, "w") as file:
            file.write("y\n")  # TODO non default options
            file.write("y\n")  # always with ci
            file.write(instate + "\n")
            file.write(outstate + "\n")
            file.write(",".join(multipoles) + "\n")

    def run(self):
        if self.cfg["eveneven"]:
            self._create_rtransition_input(
                f"input/rtransition_input_{self.state_even}_{self.state_even}",
                self.state_even,
                self.state_even,
                self.multipoles,
            )
            rtransproc = subprocess.run(
                [
                    f"{self.execs['rtransition']} < input/rtransition_input_{self.state_even}_{self.state_even} &> log/rtransition_log_{self.state_even}_{self.state_even}"
                ],
                shell=True,
            )
            print(f"rtransition completed with exit code {rtransproc.returncode}.")

        if self.cfg["oddodd"]:
            self._create_rtransition_input(
                f"input/rtransition_input_{self.state_odd}_{self.state_odd}",
                self.state_odd,
                self.state_odd,
                self.multipoles,
            )
            rtransproc = subprocess.run(
                [
                    f"{self.execs['rtransition']} < input/rtransition_input_{self.state_odd}_{self.state_odd} &> log/rtransition_log_{self.state_odd}_{self.state_odd}"
                ],
                shell=True,
            )
            print(f"rtransition completed with exit code {rtransproc.returncode}.")

        if self.cfg["evenodd"]:
            self._create_rbiotransform_input(
                f"input/rbiotranform_input_{self.state_even}_{self.state_odd}",
                self.state_even,
                self.state_odd,
            )
            rbioproc = subprocess.run(
                [
                    f"{self.execs['rbiotransform']} < input/rbiotranform_input_{self.state_even}_{self.state_odd} &> log/rbiotranform_log_{self.state_even}_{self.state_odd}"
                ],
                shell=True,
            )
            print(f"rbiotransform completed with exit code {rbioproc.returncode}.")

            self._create_rtransition_input(
                f"input/rtransition_input_{self.state_even}_{self.state_odd}",
                self.state_even,
                self.state_odd,
                self.multipoles,
            )
            rtransproc = subprocess.run(
                [
                    f"{self.execs['rtransition']} < input/rtransition_input_{self.state_even}_{self.state_odd} &> log/rtransition_log_{self.state_even}_{self.state_odd}"
                ],
                shell=True,
            )
            print(f"rtransition completed with exit code {rtransproc.returncode}.")
