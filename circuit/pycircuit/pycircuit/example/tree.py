import os

from pycircuit.circuit_builder.circuit import Circuit
from pycircuit.circuit_builder.definition import Definitions
from pycircuit.cpp_codegen.call_generation.call_metadata import CallMetaData
from pycircuit.cpp_codegen.generate_struct import generate_circuit_struct

dir_path = os.path.dirname(os.path.realpath(__file__))
definitions_str = open(f"{dir_path}/definitions.json").read()

definitions = Definitions.from_json(definitions_str)

circuit = Circuit(definitions=definitions.definitions)

NUM_OVERALL = 1024
NUM_CALLED = 10

# Check for power of two
assert NUM_OVERALL & (NUM_OVERALL - 1) == 0
assert NUM_OVERALL >= 2

roots = []
for i in range(0, NUM_OVERALL):
    roots.append(circuit.get_external(f"ext_{i}", "float"))

NAME_COUNTER = 0

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


meta_1 = CallMetaData(
    triggered=set([f"ext_{i}" for i in range(0, NUM_CALLED)]), call_name="root_call"
)

print(generate_circuit_struct(circuit, [meta_1], "test"))
