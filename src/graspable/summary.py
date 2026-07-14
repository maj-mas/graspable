import subprocess


class Summary:
    def __init__(
        self,
        cfg: dict,
        execs: dict,
        exitcode_log: list,
        n_min_mcdf: int,
        n_max_mcdf: int,
        n_min_ci: int,
        n_max_ci: int,
        has_even: bool,
        has_odd: bool,
    ) -> None:
        self.cfg = cfg
        self.execs = execs
        self.exitcode_log = exitcode_log
        self.n_min_mcdf = n_min_mcdf
        self.n_max_mcdf = n_max_mcdf
        self.n_min_ci = n_min_ci
        self.n_max_ci = n_max_ci
        self.has_even = has_even
        self.has_odd = has_odd

    def _call_rtablevels(self, fname_inp: str, fname_out: str, files: list[str]):
        with open(fname_inp, "w") as file:
            file.write("0\n")  # don't skip anything in config (potential future TODO)
            file.write(f"{len(files)}\n")  # number of rlevels output files
            for e_file in files:
                file.write(e_file + "\n")

        rtablevels_proc = subprocess.run([f"{self.execs['rtablevels']} < {fname_inp}"])
        self.exitcode_log.append({"rtablevels": rtablevels_proc.returncode})
        cp_proc = subprocess.run(
            [f"cp energytableascii.txt {fname_out}"]
        )  # we only need to keep the ascii output
        self.exitcode_log.append({"cp": cp_proc.returncode})
        rm_proc = subprocess.run(
            ["rm energytableascii.txt energytablelatex.tex"]
        )  # delete this
        self.exitcode_log.append({"rm": rm_proc.returncode})

    def _call_rlevels(self, files: list[str], fname_out: str):
        if len(files) == 0:
            raise RuntimeError("_call_rlevels() needs at least one file as input.")
        cmd = self.execs["rlevels"] + " "
        for file in files:
            cmd += file + " "
        cmd += f"> {fname_out}"

        rlevels_proc = subprocess.run([cmd], shell=True)
        self.exitcode_log.append({"rlevels": rlevels_proc.returncode})

    def _gen_E_table_best(self):
        cm_files = []
        if self.has_even:
            cm_files.append()

    def _gen_report(self):
        pass

    def _gen_table_convergence(self):
        pass

    def _gen_trans_table(self):
        pass

    def create(self):
        pass
