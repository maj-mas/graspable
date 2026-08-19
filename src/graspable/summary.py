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
        l_max: int,
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
        self.l_max = l_max
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
            cm_files.append(f"as_even{self.n_max_ci}{self.l_max + 1}CI.cm")
        if self.has_odd:
            cm_files.append(f"as_odd{self.n_max_ci}{self.l_max + 1}CI.cm")

        print(cm_files)

        self._call_rlevels(cm_files, "E_table_best")

    def _print_and_write(self, text: str, file):
        print(text)
        file.write(text)

    def _print_report(self):

        zero_exitcode_count = 0
        for call_dict in self.exitcode_log:
            key, code = list(call_dict.items())[0]
            zero_exitcode_count += 1 if code == 0 else 0
        num_calls = len(self.exitcode_log)

        with open("report", "w") as file:
            self._print_and_write(
                f"\n----- Summary for calculation: {self.cfg['meta']['name']} -----",
                file,
            )
            self._print_and_write(
                f"Out of {num_calls} program calls, {zero_exitcode_count} returned no errors.",
                file,
            )
            if zero_exitcode_count != num_calls:
                self._print_and_write("The following programs reported errors:\n", file)
                for call_dict in self.exitcode_log:
                    key, code = list(call_dict.items())[0]
                    if code != 0:
                        self._print_and_write(key, file)
                self._print_and_write("\n", file)
            self._print_and_write(
                "Printing the energy table of the largest calculation:", file
            )

            with open("E_table_best", "r") as E_file:
                table = E_file.read()
            self._print_and_write(table, file)

    def _gen_table_convergence(self):
        pass

    def _gen_trans_table(self):
        pass

    def create(self):
        self._gen_E_table_best()

        self._print_report()
