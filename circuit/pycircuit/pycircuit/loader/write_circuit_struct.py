import json
import sys
from dataclasses import dataclass

from argparse_dataclass import ArgumentParser
from pycircuit.circuit_builder.circuit import CircuitData
from pycircuit.cpp_codegen.call_generation.call_metadata import CallMetaData
from pycircuit.cpp_codegen.generation_metadata import generate_global_metadata
from pycircuit.cpp_codegen.struct_generation.generate_struct import (
    generate_circuit_struct,
)
from pycircuit.cpp_codegen.struct_generation.struct_headers import (
    get_struct_headers_for,
)
from pycircuit.loader.loader_config import CoreLoaderConfig


@dataclass
class StructOptions:
    loader_config: str
    circuit_json: str

    struct_name: str


def main():
    args = ArgumentParser(StructOptions).parse_args(sys.argv[1:])

    config = CoreLoaderConfig.from_dict(json.load(open(args.loader_config)))

    circuit = CircuitData.from_dict(json.load(open(args.circuit_json)))

    all_calls = [
        CallMetaData(triggered=call.inputs, call_name=name)
        for (name, call) in circuit.call_groups.items()
    ]
    gen_metadata = generate_global_metadata(circuit, all_calls, args.struct_name)

    signal_headers = get_struct_headers_for(gen_metadata)

    signal_includes = "\n".join(
        f'#include "{config.root_signals_path}/{header}"' for header in signal_headers
    )

    struct = generate_circuit_struct(circuit, gen_metadata)

    file = f"""
        {signal_includes}

        {struct}
    """

    print(file)


if __name__ == "__main__":
    main()
