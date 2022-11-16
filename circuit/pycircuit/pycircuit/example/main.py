import os

from pycircuit.circuit_builder.circuit import Circuit, Component
from pycircuit.circuit_builder.definition import Definitions
from pycircuit.cpp_codegen.call_generation.call_metadata import CallMetaData
from pycircuit.cpp_codegen.generate_struct import generate_circuit_struct

dir_path = os.path.dirname(os.path.realpath(__file__))
definitions_str = open(f"{dir_path}/definitions.json").read()

definitions = Definitions.from_json(definitions_str)

circuit = Circuit(definitions=definitions.definitions)

a = circuit.get_external("a", "float")
b = circuit.get_external("b", "float")
c = circuit.get_external("c", "float")

add_a = circuit.make_component(
    "add", "test_add_1", inputs={"a": a.output(), "b": b.output()}
)
add_b = circuit.make_component(
    "add", "test_add_2", inputs={"a": b.output(), "b": c.output()}
)
circuit.make_component(
    "add", "test_add_3", inputs={"a": add_a.output(), "b": add_b.output()}
)

meta_1 = CallMetaData(triggered=set(["a"]), call_name="call_a")

print(generate_circuit_struct(circuit, [meta_1], "test"))
