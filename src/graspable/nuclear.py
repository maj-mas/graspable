import subprocess


class Nuclear:
    """Generates nuclear data for GRASP calculation based on config."""

    def __init__(self, cfg: dict, execs: dict, exitcode_log: list) -> None:
        self.cfg = cfg["nuclear"]
        self.execs = execs
        self.exitcode_log = exitcode_log

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
            executable="/bin/bash",
        )
        print(
            f"rnucleus completed {'successfully.' if rnucleus_proc.returncode == 0 else 'unsuccessfully, check logs!'}"
        )
        self.exitcode_log.append({"rnucleus": rnucleus_proc.returncode})
