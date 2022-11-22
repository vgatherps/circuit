import json
import os
from typing import Sequence

from pycircuit.circuit_builder.circuit import CallGroup, CircuitBuilder, HasOutput
from pycircuit.circuit_builder.definition import Definitions

dir_path = os.path.dirname(os.path.realpath(__file__))
definitions_str = open(f"{dir_path}/definitions.json").read()

definitions = Definitions.from_json(definitions_str)

circuit = CircuitBuilder(definitions=definitions.definitions)

NUM_OVERALL = 16
NUM_CALLED = 5
NAME_COUNTER = 0


# Check for power of two
assert NUM_OVERALL & (NUM_OVERALL - 1) == 0
assert NUM_OVERALL >= 2

roots: Sequence[HasOutput] = [
    circuit.get_external(f"ext_{i}", "float") for i in range(0, NUM_OVERALL)
]

while len(roots) > 1:
    new_roots = []
    for i in range(0, len(roots), 2):
        if len(roots) <= 2:
            store = True
        else:
            store = False
        new_roots.append(
            circuit.make_component(
                "add",
                f"add_{NAME_COUNTER}",
                inputs={"a": roots[i].output(), "b": roots[i + 1].output()},
                force_stored=store,
            )
        )
        NAME_COUNTER += 1
    roots = new_roots


calls = CallGroup(set([f"ext_{i}" for i in range(0, NUM_CALLED)]))
circuit.add_call_group("root_call", calls)


as_json = circuit.to_dict()

print(json.dumps(as_json, indent=4))
