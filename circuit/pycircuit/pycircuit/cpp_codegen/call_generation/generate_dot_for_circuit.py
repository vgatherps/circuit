from pycircuit.circuit_builder.circuit import CircuitData
from pycircuit.cpp_codegen.call_generation.dotfile.generate_dot_for_circuit import (
    generate_dot_for_circuit,
)


def generate_full_circuit_dot(circuit: CircuitData) -> str:

    dot_lines = generate_dot_for_circuit(circuit)

    return f"""digraph {{
{dot_lines}
}}"""
