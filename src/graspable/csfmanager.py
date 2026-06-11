import re
import subprocess
from copy import deepcopy


class CSFManager:
    oam_symbols = {
        "s": 0,
        "p": 1,
        "d": 2,
        "f": 3,
        "g": 4,
        "h": 5,
        "i": 6,
        "j": 7,
        "k": 8,
    }
    oam_symbols_rev = dict(zip(oam_symbols.values(), oam_symbols.keys(), strict=True))

    def __init__(self, cfg: dict, execs: dict) -> None:
        self.cfg = cfg["states"]
        self.execs = execs

        self._parse_core()
        self._parse_active()
        self._assemble_states()

    def _full_occupation(self, l: int) -> int:
        return 2 * (2 * l + 1)

    def _decompose_orbital(self, orbital: str) -> tuple(int, int):
        decomp = re.findall(r"[a-zA-Z]+|\d+", orbital)
        if len(decomp) > 2:
            raise RuntimeError(f"Attempted to split an invalid orbital {orbital}.")
        return int(decomp[0]), self.oam_symbols[decomp[1]]

    def _decompose_shell(self, shell: str) -> tuple(int, int, int):
        decomp = re.findall(r"[a-zA-Z]+|\d+", shell)
        if len(decomp) > 3:
            raise RuntimeError(f"Attempted to split an invalid shell {shell}.")
        return int(decomp[0]), self.oam_symbols[decomp[1]], int(decomp[2])

    def _parse_core(self):
        if self.cfg["core"] is not None:
            self.core = self.cfg["core"].split(" ")
        else:
            self.core = []
        self.core_str = ""
        for orbital in self.core:
            n, l = self._decompose_orbital(orbital)
            if l >= n:
                raise RuntimeError(
                    f"Error in core speficication: orbital {orbital} invalid."
                )
            self.core_str += f"{orbital}({self._full_occupation(l)},c)"

    def _parse_active(self):
        if self.cfg["active"] is dict:
            raise NotImplementedError(
                "Detailed active space specification is not implemented yet."
            )
        if self.cfg["active"] is not None:
            self.active = self.cfg["active"].split(" ")
        else:
            self.active = []

        for orbital in self.active:
            if orbital in self.core:
                raise RuntimeError(
                    f"Orbital {orbital} cannot belong to core and be active."
                )  # TODO nice test case candidate

    def _check_active(self, orbital: str) -> bool:
        # check valid
        n, l = self._decompose_orbital(orbital)
        if l >= n:
            raise RuntimeError(
                f"Error in active set speficication: orbital {orbital} invalid."
            )

        if "*" in self.active:
            return True  # if all non-core orbitals are active, it's simple
        for expr in self.active:
            if expr == orbital:
                return True  # exact match
            if f"{n}*" in self.active:
                return True  # e.g. "3p" matches "3*"
            if f"*{orbital[-1]}" in self.active:
                return True  # e.g. "3p" matches "*p"
        return False

    def _assemble_state(self, state: str) -> str:
        state_grasp = self.core_str
        state_shells = state.split(" ")
        for shell in state_shells:
            if shell in self.core:
                raise RuntimeError(
                    f"Logic error: orbital {shell[:-1]} appears both in core and in state {state}."
                )
            n, l, occ = self._decompose_shell(shell)
            active = self._check_active(f"{n}{self.oam_symbols_rev[l]}")
            if occ == self._full_occupation(l) and not active:
                type = "c"
            if active:
                type = "*"
            else:
                type = "i"

            state_grasp += f"{n}{self.oam_symbols_rev[l]}({occ},{type})"

        return state_grasp

    def _orbitals_from_state(self, state: str) -> list[str]:
        orbitals = []
        state_shells = state.split(" ")
        for shell in state_shells:
            n, l, occ = self._decompose_shell(shell)
            orbitals.append(f"{n}{self.oam_symbols_rev[l]}")

        return orbitals

    def _assemble_states(self):
        self.orbitals_even = deepcopy(self.core)  # also get a list of all orbitals
        self.states_even = []
        for state in self.cfg["multireference"]["even"]:
            orbitals_state = self._orbitals_from_state(state)
            for orbital in orbitals_state:
                if orbital not in self.orbitals_even:
                    self.orbitals_even.append(orbital)

            self.states_even.append(self._assemble_state(state))

        self.orbitals_odd = deepcopy(self.core)  # also get a list of all orbitals
        self.states_odd = []
        for state in self.cfg["multireference"]["odd"]:
            orbitals_state = self._orbitals_from_state(state)
            for orbital in orbitals_state:
                if orbital not in self.orbitals_odd:
                    self.orbitals_odd.append(orbital)

            self.states_odd.append(self._assemble_state(state))

    def _create_rcsfgenerate_input(
        self, fname: str, states: list[str], exc: int, j2_min: int, j2_max: int
    ):
        with open(f"input/{fname}", "w") as file:
            file.write("*\n")  # default order
            file.write("0\n")  # no pre-def core
            file.writelines(state + "\n" for state in states)  # states
            file.write("\n")  # end states
            file.write(self.cfg["basis_set"] + "\n")  # as basis set
            file.write(str(j2_min) + "\n")  # 2j lower
            file.write(str(j2_max) + "\n")  # 2j upper
            file.write(str(exc) + "\n")  # # of excitations
            file.write("n\n")  # end

    def _select_split(self) -> tuple(int, int):
        highest_n_state = 0
        for states_parity in [
            self.cfg["multireference"]["even"],
            self.cfg["multireference"]["odd"],
        ]:
            for state in states_parity:
                for shell in state.split(" "):
                    n, l, occ = self._decompose_shell(shell)
                    if n > highest_n_state:
                        highest_n_state = n

        highest_n_basis = int(
            self.cfg["basis_set"][0]
        )  # TODO assumes s orbital always has the highest n in basis set
        if highest_n_basis <= highest_n_state:
            raise RuntimeError("Active space too small to create sensible split.")
        return highest_n_state, highest_n_basis

    def _create_rcsfsplit_input(self, fname: str, state_name: str):
        self.n_min, self.n_max = self._select_split()
        self.n_sets = self.n_max - self.n_min + 1
        with open(f"input/{fname}", "w") as file:
            file.write(state_name + "\n")
            file.write(str(self.n_sets) + "\n")
            for n in range(self.n_min, self.n_max + 1):
                for l in range(n):
                    oam = self.oam_symbols_rev[l]
                    orbital = f"{n}{oam}"
                    if l != n - 1:
                        file.write(orbital + ",")
                    else:
                        file.write(orbital)
                file.write("\n")
                file.write(f"{n}\n")

    def _gen_mr(self):
        self._create_rcsfgenerate_input(
            "rcsfgenerate_input_mr_even",
            self.states_even,
            0,
            self.cfg["2j_min"],
            self.cfg["2j_max"],
        )
        rcsfgenerate_proc_mr_even = subprocess.run(
            [
                f"{self.execs['rcsfgenerate']} < input/rcsfgenerate_input_mr_even &> log/rcsfgenerate_log_mr_even"
            ],
            shell=True,
        )
        print(
            f"rcsfgenerate completed with exit code {rcsfgenerate_proc_mr_even.returncode}."
        )
        subprocess.run(["cp rcsf.out mr_even.c"], shell=True)

        self._create_rcsfgenerate_input(
            "rcsfgenerate_input_mr_odd",
            self.states_odd,
            0,
            self.cfg["2j_min"],
            self.cfg["2j_max"],
        )
        rcsfgenerate_proc_mr_odd = subprocess.run(
            [
                f"{self.execs['rcsfgenerate']} < input/rcsfgenerate_input_mr_odd &> log/rcsfgenerate_log_mr_odd"
            ],
            shell=True,
        )
        print(
            f"rcsfgenerate completed with exit code {rcsfgenerate_proc_mr_odd.returncode}."
        )
        subprocess.run(["cp rcsf.out mr_odd.c"], shell=True)

    def _gen_as(self):
        self._create_rcsfgenerate_input(
            "rcsfgenerate_input_as_even",
            self.states_even,
            self.cfg["excitations"],
            self.cfg["2j_min"],
            self.cfg["2j_max"],
        )
        rcsfgenerate_proc_as_even = subprocess.run(
            [
                f"{self.execs['rcsfgenerate']} < input/rcsfgenerate_input_as_even &> log/rcsfgenerate_log_as_even"
            ],
            shell=True,
        )
        print(
            f"rcsfgenerate completed with exit code {rcsfgenerate_proc_as_even.returncode}."
        )
        subprocess.run(["cp rcsf.out as_even.c"], shell=True)

        self._create_rcsfgenerate_input(
            "rcsfgenerate_input_as_odd",
            self.states_odd,
            self.cfg["excitations"],
            self.cfg["2j_min"],
            self.cfg["2j_max"],
        )
        rcsfgenerate_proc_as_odd = subprocess.run(
            [
                f"{self.execs['rcsfgenerate']} < input/rcsfgenerate_input_as_odd &> log/rcsfgenerate_log_as_odd"
            ],
            shell=True,
        )
        print(
            f"rcsfgenerate completed with exit code {rcsfgenerate_proc_as_odd.returncode}."
        )
        subprocess.run(["cp rcsf.out as_odd.c"], shell=True)

    def _split_as(self):
        self._create_rcsfsplit_input("rcsfsplit_input_even", "as_even")
        rcsfsplit_proc_even = subprocess.run(
            [
                f"{self.execs['rcsfsplit']} < input/rcsfsplit_input_even &> log/rcsfsplit_log_even"
            ],
            shell=True,
        )
        print(f"rcsfsplit completed with exit code {rcsfsplit_proc_even.returncode}.")

        self._create_rcsfsplit_input("rcsfsplit_input_odd", "as_odd")
        rcsfsplit_proc_odd = subprocess.run(
            [
                f"{self.execs['rcsfsplit']} < input/rcsfsplit_input_odd &> log/rcsfsplit_log_odd"
            ],
            shell=True,
        )
        print(f"rcsfsplit completed with exit code {rcsfsplit_proc_odd.returncode}.")

    def setup(self):
        self._gen_mr()
        self._gen_as()
        if self.cfg["split"]:
            self._split_as()

    def active_orbitals_given_n(self, n: int) -> list[str]:
        active_list = []
        basis_set = self.cfg["basis_set"].split(",")
        for l in range(n):
            oam = self.oam_symbols_rev[l]
            orbital = f"{n}{oam}"
            keep = False
            for basis_orbital in basis_set:
                n_basis, l_basis = self._decompose_orbital(basis_orbital)
                if l == l_basis and n <= n_basis:
                    keep = True

            if keep:
                active_list.append(orbital)

        return active_list

    # TODO add zero/first order split
    # TODO add rcsfinteract reduction
