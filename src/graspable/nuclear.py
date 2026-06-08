import subprocess


class Nuclear:
    def __init__(self, cfg: dict, execs: dict) -> None:
        self.cfg = cfg["nuclear"]
        self.execs = execs

    def _create_rnuclear_input(self):
        with open("input/rnucleus_input", "w") as file:
            file.write(f"{self.cfg['Z']}\n")  # atomic number = nuclear charge

            if self.cfg["point-like"]:
                file.write("0\n")
            else:
                file.write(
                    f"{self.cfg['A']}\n"
                )  # mass number specifying isotope for nuclear model

            if self.cfg["non_default_fermi"]["r_rms"] is None:
                file.write("n\n")
            else:
                file.write("y\n")
                file.write(f"{self.cfg['non_default_fermi']['r_rms']}\n")
                file.write(f"{self.cfg['non_default_fermi']['skin']}\n")

            if self.cfg["static"]:
                file.write("0\n")
            else:
                file.write(f"{self.cfg['m']}\n")

            file.write(f"{self.cfg['I']}\n")
            file.write(f"{self.cfg['dipole']}\n")
            file.write(f"{self.cfg['quadrupole']}\n")

    def setup(self):
        self._create_rnuclear_input()

        rnucleus_proc = subprocess.run(
            [f"{self.execs['rnucleus']} < input/rnucleus_input &> log/rnucleus_log"],
            shell=True,
        )
        print(f"rnucleus completed with exit code {rnucleus_proc.returncode}.")
