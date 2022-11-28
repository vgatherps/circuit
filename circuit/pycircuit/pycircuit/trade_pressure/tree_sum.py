import json
import os
from typing import List, Sequence

from pycircuit.circuit_builder.circuit import (
    CallGroup,
    CircuitBuilder,
    ComponentOutput,
    HasOutput,
    OutputOptions,
)
from pycircuit.circuit_builder.definition import Definitions

DUMMY_COUNTER = 0


def do_add(circuit, a, b):
    global DUMMY_COUNTER
    DUMMY_COUNTER += 1
    return circuit.make_component(
        "add",
        f"add_{DUMMY_COUNTER}",
        inputs={"a": a, "b": b},
    )


def tree_sum(circuit: CircuitBuilder, roots: List[ComponentOutput]):
    if len(roots) == 0:
        raise ValueError("Empty list passed to sum")
    while len(roots) > 1:
        new_roots = []
        for i in range(0, len(roots), 2):
            new_roots.append(do_add(circuit, roots[i], roots[i + 1]))

        if len(roots) % 1 != 0:
            new_roots[-1] = do_add(circuit, roots[-1], new_roots[-1])

        roots = new_roots
    return roots[0]
