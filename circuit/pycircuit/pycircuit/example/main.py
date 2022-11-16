import os

from pycircuit.circuit_builder.circuit import Circuit, Component
from pycircuit.circuit_builder.definition import Definitions
from pycircuit.cpp_codegen.generate_struct import generate_circuit_struct

dir_path = os.path.dirname(os.path.realpath(__file__))
definitions_str = open(f"{dir_path}/definitions.json").read()

definitions = Definitions.from_json(definitions_str)

circuit = Circuit(definitions=definitions.definitions)

a = circuit.get_external("a", "float")
b = circuit.get_external("b", "float")

circuit.make_component("add", "test_add", inputs={"a": a.output(), "b": b.output()})

print(generate_circuit_struct(circuit, "test"))
