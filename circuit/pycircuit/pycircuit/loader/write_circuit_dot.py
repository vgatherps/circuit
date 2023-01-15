from dataclasses import dataclass
import json
import sys

from argparse_dataclass import ArgumentParser
from pycircuit.circuit_builder.circuit import CircuitData
from pycircuit.cpp_codegen.call_generation.generate_dot_for_circuit import (
    generate_full_circuit_dot,
)


@dataclass
class CircuitDotStructOptions:
    circuit_json: str


def generate_circuit_dot(circuit: CircuitData) -> str:
    return generate_full_circuit_dot(circuit)


def main():
    args = ArgumentParser(CircuitDotStructOptions).parse_args(sys.argv[1:])

    circuit = CircuitData.from_dict(json.load(open(args.circuit_json)))

    print(generate_circuit_dot(circuit))


if __name__ == "__main__":
    main()
