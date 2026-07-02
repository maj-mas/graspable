import re
import subprocess
from copy import deepcopy


class CSFManager:
    """Class that creates lists of CSFs for the calculation based on the configuration."""

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
        self.graspg = cfg["env"]["mpi"]["graspg"]

        self.has_even = self.cfg["multireference"]["even"] is not None
        self.has_odd = self.cfg["multireference"]["odd"] is not None
        if not self.has_even and not self.has_odd:
            raise RuntimeError(
                "At least an even or an odd state needs to be added to the multireference!"
            )

        self._parse_core()
        self._parse_active()
        self._assemble_states()

    def _full_occupation(self, l: int) -> int:
        """Number of electrons that fit into a nonrelativistic l-subshell.

        Args:
            l (int): OAM

        Returns:
            int: Max occupation.
        """
        return 2 * (2 * l + 1)

    def _decompose_orbital(self, orbital: str) -> tuple[int, int]:
        """Parses an orbital string such as '10h' into n=10 and l=5 using regexes.

        Args:
            orbital (str): Orbital string

        Raises:
            RuntimeError: Raised if orbital cannot be split according to rule.

        Returns:
            tuple(int, int): (n, l)
        """
        decomp = re.findall(r"[a-zA-Z]+|\d+", orbital)
        if len(decomp) > 2:
            raise RuntimeError(f"Attempted to split an invalid orbital {orbital}.")
        return int(decomp[0]), self.oam_symbols[decomp[1]]

    def _decompose_shell(self, shell: str) -> tuple[int, int, int]:
        """Parses a non-relativistic subshell string including occupation such as '10h4' into n=10, l=5 and n_electrons=4 using regexes.

        Args:
            shell (str): Subshell string

        Raises:
            RuntimeError: Raised if subshell cannot be split according to rule.

        Returns:
            tuple(int, int, int): (n, l, n_electrons)
        """
        decomp = re.findall(r"[a-zA-Z]+|\d+", shell)
        if len(decomp) > 3:
            raise RuntimeError(f"Attempted to split an invalid shell {shell}.")
        return int(decomp[0]), self.oam_symbols[decomp[1]], int(decomp[2])

    def _parse_core(self):
        """Converts the core string from the config into a list of orbitals in grasp notation, e.g. 1s 2s -> 1s(2,c) 2s(2,c) that is then stored in self.core_str. It is assumed that core orbitals are always full.

        Raises:
            RuntimeError: Raised if an invalid orbital such as 1p is encountered.
        """
        if self.cfg["core"] is not None:
            self.core = self.cfg["core"].split(" ")
        else:
            self.core = []  # if core is None, the loop below will be over an empty list an core_str will be empty, which is fine!
        self.core_str = ""
        for orbital in self.core:
            n, l = self._decompose_orbital(orbital)
            if l >= n:
                raise RuntimeError(
                    f"Error in core speficication: orbital {orbital} invalid."
                )
            self.core_str += f"{orbital}({self._full_occupation(l)},c)"

    def _parse_active(self):
        """Parses the string defining the active orbitals, which are allowed to contain the wildcard symbol *. In the future, support for more detailed occupation specification will be added (e.g. 'd2p orbital can have 3 to 5 electrons').

        Raises:
            RuntimeError: Raised if an orbital is found both in the core and the active list.
        """
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
        """Determines wether an orbital is active. This requires some care because the list of active orbitals can contain wildcards (or even just be '*').

        Args:
            orbital (str): Orbital string, e.g. '3p'

        Raises:
            RuntimeError: Raised if an invalid orbital such as 1p is encountered.

        Returns:
            bool: True if active, False otherwise.
        """
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
        """Converts a simple non-relativistic config string such as 2s2 2p1 to GRASP notation, e.g. 2s(2,*) 2p(1,*) depending on which orbitals are configured active or closed.

        Args:
            state (str): State string.

        Raises:
            RuntimeError: Raised if an orbital is found both in the core and the active list.

        Returns:
            str: GRASP formatted configuration string.
        """
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
        """Splits a simple non-relativistic config string into orbital strings, e.g. '2s2 2p1' -> ["2s", "2p"]

        Args:
            state (str): State string

        Returns:
            list[str]: Split orbitals, occupation discarded.
        """
        orbitals = []
        state_shells = state.split(" ")
        for shell in state_shells:
            n, l, occ = self._decompose_shell(shell)
            orbitals.append(f"{n}{self.oam_symbols_rev[l]}")

        return orbitals

    def _assemble_states(self):
        """Parses states from the config to grasp format and creates a list of all orbitals that appear in the configuration for both parities."""
        if self.has_even:
            self.orbitals_even = deepcopy(self.core)  # also get a list of all orbitals
            self.states_even = []
            for state in self.cfg["multireference"]["even"]:
                orbitals_state = self._orbitals_from_state(state)
                for orbital in orbitals_state:
                    if orbital not in self.orbitals_even:
                        self.orbitals_even.append(orbital)

                self.states_even.append(self._assemble_state(state))

        if self.has_odd:
            self.orbitals_odd = deepcopy(self.core)  # also get a list of all orbitals
            self.states_odd = []
            for state in self.cfg["multireference"]["odd"]:
                orbitals_state = self._orbitals_from_state(state)
                for orbital in orbitals_state:
                    if orbital not in self.orbitals_odd:
                        self.orbitals_odd.append(orbital)

                self.states_odd.append(self._assemble_state(state))

    def _create_rcsfgenerate_input(
        self,
        fname: str,
        states: list[str],
        exc: int,
        j2_min: int,
        j2_max: int,
        manual_basis: str | None = None,
    ):
        """Creates an input file for the CSF list generating programs of graspg.

        Args:
            fname (str): File name.
            states (list[str]): List of configurations in grasp format.
            exc (int): Number of excitations using grasp sign convention.
            j2_min (int): Minimum value of 2J for states to be generated.
            j2_max (int): Maximum value of 2J for states to be generated.
            manual_basis (str | None, optional): List of basis set listing maximum l for each n, e.g. '5s,4p,3d'. If None, basis_set from config is used. Defaults to None.
        """
        with open(f"input/{fname}", "w") as file:
            if not self.graspg:
                file.write("*\n")  # default order
            file.write("0\n")  # no pre-def core
            file.writelines(state + "\n" for state in states)  # states
            file.write("\n")  # end states
            if manual_basis is None:
                file.write(self.cfg["basis_set"] + "\n")  # as basis set
            else:
                file.write(manual_basis + "\n")  # as basis set
            file.write(str(j2_min) + "," + str(j2_max) + "\n")  # 2j lower,upper
            file.write(str(exc) + "\n")  # # of excitations
            file.write("n\n")  # end

    def _create_rcsfgenerate_input_graspg(
        self,
        fname: str,
        states: list[str],
        exc: int,
        j2_min: int,
        j2_max: int,
        manual_basis: str | None = None,
    ):
        """Creates an input file for the CSF list generating programs of graspg.

        Args:
            fname (str): File name.
            states (list[str]): List of configurations in grasp format.
            exc (int): Number of excitations using grasp sign convention.
            j2_min (int): Minimum value of 2J for states to be generated.
            j2_max (int): Maximum value of 2J for states to be generated.
            manual_basis (str | None, optional): List of basis set listing maximum l for each n, e.g. '5s,4p,3d'. If None, basis_set from config is used. Defaults to None.
        """
        with open(f"input/{fname}", "w") as file:
            # for graspg: mr only first
            file.write("0\n")  # no pre-def core
            file.writelines(state + "\n" for state in states)  # states
            file.write("\n")  # end states
            file.write(self.cfg["labelling_space"] + "\n")  # labelling space
            file.write(str(j2_min) + "," + str(j2_max) + "\n")  # 2j lower,upper
            file.write("0\n")  # # of excitations
            file.write("y\n")  # end
            file.writelines(state + "\n" for state in states)  # states
            file.write("\n")  # end states
            # then add as
            if manual_basis is None:
                file.write(self.cfg["basis_set"] + "\n")  # as basis set
            else:
                file.write(manual_basis + "\n")  # as basis set
            file.write(str(j2_min) + "," + str(j2_max) + "\n")  # 2j lower,upper
            file.write(str(exc) + "\n")  # # of excitations
            file.write("n\n")  # end

    def _select_split(self) -> tuple[int, int]:
        """Finds highest n in even and odd configs and highest n in basis set.

        Raises:
            RuntimeError: Active space should not be too small.

        Returns:
            tuple(int, int): (n_max_configs, n_max_basis)
        """
        highest_n_state = 0
        states_lookup = []
        if self.has_even:
            states_lookup.append(self.cfg["multireference"]["even"])
        if self.has_odd:
            states_lookup.append(self.cfg["multireference"]["odd"])
        for states_parity in states_lookup:
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
        """Creates an input file for the CSF list splitting programs of grasp.

        Args:
            fname (str): File name.
            state_name (str): Name of state on disk.
        """
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

    def _mr_basis(self) -> str:
        """Selects a basis set for the initial calculation on the multireference only (no excitations). This is required due to an oddity with graspg.

        Returns:
            str: Basis set string, e.g. '5s,4p,3d'.
        """
        basis = ""
        for oam_symbol in list(self.oam_symbols.keys()):
            highest_n = 0
            if self.has_even:
                for orbital in self.orbitals_even:
                    if oam_symbol in orbital:
                        n, l = self._decompose_orbital(orbital)
                        if n > highest_n:
                            highest_n = n
            if self.has_odd:
                for orbital in self.orbitals_odd:
                    if oam_symbol in orbital:
                        n, l = self._decompose_orbital(orbital)
                        if n > highest_n:
                            highest_n = n
            if highest_n != 0:
                basis += f"{highest_n}{oam_symbol},"

        if basis.endswith(","):
            basis = basis[:-1]

        return basis

    def _gen_mr(self):
        """Generates CSFs for the multireference without excitations for both parities."""
        mr_basis = self._mr_basis()

        if self.has_even:
            self._create_rcsfgenerate_input(
                "rcsfgenerate_input_mr_even",
                self.states_even,
                0,
                self.cfg["2j_min"],
                self.cfg["2j_max"],
                manual_basis=mr_basis,
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

        if self.has_odd:
            self._create_rcsfgenerate_input(
                "rcsfgenerate_input_mr_odd",
                self.states_odd,
                0,
                self.cfg["2j_min"],
                self.cfg["2j_max"],
                manual_basis=mr_basis,
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

    def _gen_mr_csfg(self):
        """Generates CSFs for the multireference without excitations for both parities, using graspg."""
        mr_basis = self._mr_basis()

        if self.has_even:
            self._create_rcsfgenerate_input(
                "rcsfgenerate_input_mr_even",
                self.states_even,
                0,
                self.cfg["2j_min"],
                self.cfg["2j_max"],
                manual_basis=mr_basis,
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
            subprocess.run(["cp rcsfg.out mr_even.g"], shell=True)
            subprocess.run(["cp rlabel.out mr_even.l"], shell=True)

        if self.has_odd:
            self._create_rcsfgenerate_input(
                "rcsfgenerate_input_mr_odd",
                self.states_odd,
                0,
                self.cfg["2j_min"],
                self.cfg["2j_max"],
                manual_basis=mr_basis,
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
            subprocess.run(["cp rcsfg.out mr_odd.g"], shell=True)
            subprocess.run(["cp rlabel.out mr_odd.l"], shell=True)

    def _gen_as(self):
        """Generates lists of CSFs for the active space for both parities."""
        if self.has_even:
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

        if self.has_odd:
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

    def _gen_as_csfg(self):
        """Generates lists of CSFs for the active space for both parities, using graspg."""
        if self.has_even:
            self._create_rcsfgenerate_input_graspg(
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
            subprocess.run(["cp rcsfg.out as_even.g"], shell=True)
            subprocess.run(["cp rlabel.out as_even.l"], shell=True)

        if self.has_odd:
            self._create_rcsfgenerate_input_graspg(
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
            subprocess.run(["cp rcsfg.out as_odd.g"], shell=True)
            subprocess.run(["cp rlabel.out as_odd.l"], shell=True)

    def _split_as(self):
        """Splits the list of active space CSFs by principal quantum number for both parities."""
        if self.has_even:
            if self.graspg:
                subprocess.run(["cp as_even.l rlabel.inp"], shell=True)
            self._create_rcsfsplit_input("rcsfsplit_input_even", "as_even")
            rcsfsplit_proc_even = subprocess.run(
                [
                    f"{self.execs['rcsfsplit']} < input/rcsfsplit_input_even &> log/rcsfsplit_log_even"
                ],
                shell=True,
            )
            print(
                f"rcsfsplit completed with exit code {rcsfsplit_proc_even.returncode}."
            )

        if self.has_odd:
            if self.graspg:
                subprocess.run(["cp as_odd.l rlabel.inp"], shell=True)
            self._create_rcsfsplit_input("rcsfsplit_input_odd", "as_odd")
            rcsfsplit_proc_odd = subprocess.run(
                [
                    f"{self.execs['rcsfsplit']} < input/rcsfsplit_input_odd &> log/rcsfsplit_log_odd"
                ],
                shell=True,
            )
            print(
                f"rcsfsplit completed with exit code {rcsfsplit_proc_odd.returncode}."
            )

    def _split_as_csfg(self):
        """Splits the list of active space CSFs by principal quantum number for both parities. Since rcsfsplit is not implemented for the graspg format, we achieve the same result using repeated calls to rcsfggenerate_csfg, resulting in somewhat of a longer runtime."""
        print(
            "Performing AS split manually since graspg is enabled, this step might take a little longer."
        )
        self.n_min, self.n_max = self._select_split()
        self.n_sets = self.n_max - self.n_min + 1

        for n in range(self.n_min, self.n_max + 1):
            basis = ""
            for l in range(n):
                oam = self.oam_symbols_rev[l]
                orbital = f"{n}{oam}"
                if l != n - 1:
                    basis += orbital + ","
                else:
                    basis += orbital

            if self.has_even:
                self._create_rcsfgenerate_input_graspg(
                    f"rcsfgenerate_input_as_even_split{n}",
                    self.states_even,
                    self.cfg["excitations"],
                    self.cfg["2j_min"],
                    self.cfg["2j_max"],
                    manual_basis=basis,
                )
                rcsfgenerate_proc_split_even = subprocess.run(
                    [
                        f"{self.execs['rcsfgenerate']} < input/rcsfgenerate_input_as_even_split{n} &> log/rcsfgenerate_log_as_even_split{n}"
                    ],
                    shell=True,
                )
                print(
                    f"rcsfgenerate completed with exit code {rcsfgenerate_proc_split_even.returncode}."
                )
                subprocess.run([f"cp rcsfg.out as_even{n}.g"], shell=True)
                subprocess.run([f"cp rlabel.out as_even{n}.l"], shell=True)

            if self.has_odd:
                self._create_rcsfgenerate_input_graspg(
                    f"rcsfgenerate_input_as_odd_split{n}",
                    self.states_odd,
                    self.cfg["excitations"],
                    self.cfg["2j_min"],
                    self.cfg["2j_max"],
                    manual_basis=basis,
                )
                rcsfgenerate_proc_split_odd = subprocess.run(
                    [
                        f"{self.execs['rcsfgenerate']} < input/rcsfgenerate_input_as_odd_split{n} &> log/rcsfgenerate_log_as_odd_split{n}"
                    ],
                    shell=True,
                )
                print(
                    f"rcsfgenerate completed with exit code {rcsfgenerate_proc_split_odd.returncode}."
                )
                subprocess.run([f"cp rcsfg.out as_odd{n}.g"], shell=True)
                subprocess.run([f"cp rlabel.out as_odd{n}.l"], shell=True)

    def _check_csfg_labelling_space(self):
        """Checks if the labelling space passed is okay. Otherwise, raises exception."""
        orbitals = self.cfg["labelling_space"].split(",")
        n, l = self._decompose_orbital(orbitals[0])
        ls = [l]
        # the labelling space should go up to some n and include all l subshells
        for orbital in orbitals[1:]:
            new_n, new_l = self._decompose_orbital(orbital)
            if new_l in ls or new_n != n:
                raise RuntimeError(
                    f"Labelling space definition {self.cfg['labelling_space']} invalid. Needs to be a full set of n-shells, e.g. 3s,3p,3d or 4s,4p,4d,4f."
                )
            ls.append(new_l)
            n = new_n
        # the principal quantum number of the labelling space needs to be at least as large as the largest principal quantum number in the multireference
        max_n_states = 0
        orbitals_lookup = []
        if self.has_even:
            orbitals_lookup.append(self.orbitals_even)
        if self.has_odd:
            orbitals_lookup.append(self.orbitals_odd)
        for orbitals_parity in orbitals_lookup:
            for orbital in orbitals_parity:
                n_state, l = self._decompose_orbital(orbital)
                if n_state > max_n_states:
                    max_n_states = n_state

        if max_n_states > n:
            raise RuntimeError(
                f"Labelling space principal quantum number needs to be at least as large as the largest in the MR. Labelling space n={n}, largest n in MR = {max_n_states}."
            )

    def setup(self):
        """Generates lists of CSFs according to the config. Must be called after initialisation."""
        if not self.graspg:
            self._gen_mr()
            self._gen_as()
            self._split_as()
        else:
            self._check_csfg_labelling_space()
            self._gen_mr_csfg()
            self._gen_as_csfg()
            self._split_as()
            # self._split_as_csfg()

    def active_orbitals_given_n(self, n: int) -> list[str]:
        """Returns a list of non-relativistic orbitals in the active set that match the given principal quantum number.

        Args:
            n (int): Principal quantum number.

        Returns:
            list[str]: List of active orbitals at n.
        """
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
