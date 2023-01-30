import math
from typing import Callable, List, Sequence

from pycircuit.circuit_builder.circuit import HasOutput
from pycircuit.circuit_builder.signals.minmax import min_of, max_of


def even(x):
    return 2 * int(math.floor(x / 2))


def _tree_op(
    roots: Sequence[HasOutput], op: Callable[[HasOutput, HasOutput], HasOutput]
) -> HasOutput:
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


def tree_sum(roots: Sequence[HasOutput]) -> HasOutput:
    return _tree_op(roots, lambda a, b: a + b)


def tree_min(roots: Sequence[HasOutput]) -> HasOutput:
    return _tree_op(roots, min_of)


def tree_max(roots: Sequence[HasOutput]) -> HasOutput:
    return _tree_op(roots, max_of)
