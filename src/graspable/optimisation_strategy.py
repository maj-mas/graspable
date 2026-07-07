import random
import re
from abc import ABC, abstractmethod

import numpy as np


class AbstractOptimisationStrategy(ABC):
    oam_symbols = {
        "s": 0,
        "p": 1,
        "d": 2,
        "f": 3,
        "g": 4,
        "h": 5,
        "j": 6,
        "k": 7,
        "l": 8,
        "m": 9,
        "n": 10,
        "o": 11,
        "q": 12,
        "r": 13,
        "t": 14,
        "u": 15,
        "v": 16,
    }
    oam_symbols_rev = dict(zip(oam_symbols.values(), oam_symbols.keys(), strict=False))
    bad_sets_since_last_success = []
    converged_sets = []

    def __init__(self, orbitals: list[str]) -> None:
        super().__init__()
        self.n_orbitals = len(orbitals)
        self.orbital_map = {orbital: i for i, orbital in enumerate(orbitals)}
        self.optimized_together_graph = np.zeros(
            (self.n_orbitals, self.n_orbitals), dtype=bool
        )  # initially, no orbitals have converged together

    def _orbital_glob(self, orbital: str) -> list[str]:
        glob_list = []
        decomp = re.findall(r"\*[a-zA-Z]|\d+\*", orbital)
        if len(decomp) != 2:
            raise RuntimeError(f"Error in glob of orbital {orbital}.")
        if decomp[0] == "*":
            raise NotImplementedError("Globs of type *oam are not supported.")
        if decomp[1] == "*":
            n = int(decomp[0])
            for l in range(n):
                glob_list.append(f"{n}{self.oam_symbols_rev[l]}")
        return glob_list

    def _update_graph(self, orbital1: str, orbital2: str, converged=bool):
        i = self.orbital_map[orbital1]
        j = self.orbital_map[orbital2]
        self.optimized_together_graph[i, j] = converged
        self.optimized_together_graph[j, i] = converged

    def update_graph_multiple(self, orbset: list[str], success: bool = True):
        # this works because it doesn't matter if we note the same combination as converged together multiple times
        if not success:
            self.bad_sets_since_last_success.append(orbset)  # if unsuccessful, store
            return
        self.bad_sets_since_last_success = []  # if successful, empty store of bad attempts (we want retries)
        self.converged_sets.append(orbset)
        for orbital1 in orbset:
            for orbital2 in orbset:
                if orbital1 == "*" or orbital2 == "*":
                    self.optimized_together_graph = np.full(
                        (self.n_orbitals, self.n_orbitals), fill_value=True, dtype=bool
                    )
                if "*" in orbital1:
                    pass
                if "*" in orbital2:
                    pass
                else:
                    self._update_graph(orbital1, orbital2)

    def converged(self) -> bool:
        return self.optimized_together_graph.all()

    @abstractmethod
    def next_set(self) -> list[str] | str:
        raise NotImplementedError(
            ""
        )  # the method with which the next pair or set of orbitals to optimize together is generated is to be implemented by the implementation


class TestStrategy(AbstractOptimisationStrategy):
    def next_set(self) -> list[str] | str:
        return "*"  # xd


class RandomStrategy(AbstractOptimisationStrategy):
    def __init__(self, orbitals: list[str], seed: int | None = None) -> None:
        super().__init__(orbitals)
        if seed is not None:
            random.seed(seed)

    def next_set(self) -> list[str] | str:
        orbitals = list(self.orbital_map.keys())
        n_selection = random.randint(1, len(orbitals))
        selection = random.sample(orbitals, k=n_selection)
        i = 0
        while (
            selection in self.bad_sets_since_last_success
            or selection in self.converged_sets
        ):
            n_selection = random.randint(1, len(orbitals))
            selection = random.sample(orbitals, k=n_selection)
            i += 1
            if i > 99:
                raise RuntimeError(
                    "No valid next try orbital set found after 100 selections."
                )

        return selection


class SuccessiveStrategy(AbstractOptimisationStrategy):
    i = 0

    def converged(self) -> bool:
        return (
            False if self.i < len(list(self.orbital_map.keys())) else True
        )  # TODO Hack

    def next_set(self) -> list[str] | str:
        orbitals = list(self.orbital_map.keys())

        if self.i < len(orbitals):
            self.i += 1
            return [orbitals[self.i - 1]]
        raise RuntimeError("SuccessiveStrategy called too many times.")
