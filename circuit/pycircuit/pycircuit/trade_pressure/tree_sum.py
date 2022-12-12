import math
from typing import List, Sequence

from pycircuit.circuit_builder.circuit import CircuitBuilder, ComponentOutput, HasOutput


def even(x):
    return 2 * int(math.floor(x / 2))


def tree_sum(circuit: CircuitBuilder, roots: Sequence[HasOutput]):
    if len(roots) == 0:
        raise ValueError("Empty list passed to sum")
    while len(roots) > 1:
        new_roots = []
        for i in range(0, even(len(roots)), 2):
            new_roots.append(roots[i] + roots[i + 1])

        if (len(roots) % 2) != 0:
            new_roots[-1] = roots[-1] + new_roots[-1]

        roots = new_roots
    return roots[0]
