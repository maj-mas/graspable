from abc import ABC, abstractmethod
import numpy as np


class AbstractOptimisationStrategy(ABC):
    def __init__(self, orbitals: list[str]) -> None:
        super().__init__()
        self.n_orbitals = len(orbitals)
        self.orbital_map = {orbital: i for i, orbital in enumerate(orbitals)}
        self.optimized_together_graph = np.zeros(
            (self.n, self.n), dtype=bool
        )  # initially, no orbitals have converged together

    def update_graph(self, orbital1: str, orbital2: str, converged=bool):
        i = self.optimized_together_graph[orbital1]
        j = self.optimized_together_graph[orbital2]
        self.optimized_together_graph[i, j] = converged
        self.optimized_together_graph[j, i] = converged

    def update_graph_multiple(self, results: list[tuple(str, str, bool)]):
        for orbital1, orbital2, converged in results:
            self.update_graph(orbital1, orbital2, converged)

    def converged(self) -> bool:
        return self.optimized_together_graph.all()

    @abstractmethod
    def next_set(self) -> list[tuple(str, str)] | str:
        raise NotImplementedError(
            ""
        )  # the method with which the next pair or set of orbitals to optimize together is generated is to be implemented by the implementation


class TestStrategy(AbstractOptimisationStrategy):
    def next_set(self) -> list[tuple(str, str)] | str:
        return "*"  # kek
