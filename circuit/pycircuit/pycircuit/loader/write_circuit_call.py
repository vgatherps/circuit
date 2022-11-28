import json
import sys
from dataclasses import dataclass

from argparse_dataclass import ArgumentParser
from pycircuit.circuit_builder.circuit import CircuitData
from pycircuit.cpp_codegen.call_generation.call_headers import DEFAULT_HEADERS
from pycircuit.cpp_codegen.call_generation.call_metadata import CallMetaData
from pycircuit.cpp_codegen.call_generation.generate_call_for_trigger import (
    generate_external_call_body_for,
)
from pycircuit.cpp_codegen.generation_metadata import generate_global_metadata
from pycircuit.loader.loader_config import CoreLoaderConfig


@dataclass
class CallOptions:
    loader_config: str
    circuit_json: str

    struct_name: str
    struct_header: str
    call_name: str


@dataclass
class StructOptions:
    struct_name: str
    struct_header: str
    call_name: str


def generate_circuit_call(
    struct_options: StructOptions, config: CoreLoaderConfig, circuit: CircuitData
) -> str:
    if struct_options.call_name not in circuit.call_groups:
        raise ValueError(
            f"Call {struct_options.call_name} not contained in circuit config"
        )

    call = circuit.call_groups[struct_options.call_name]
    metadata = CallMetaData(triggered=call.inputs, call_name=struct_options.call_name)

    gen_metadata = generate_global_metadata(
        circuit, [metadata], struct_options.struct_name
    )

    call_str = generate_external_call_body_for(metadata, gen_metadata)

    default_includes = "\n".join(
        f'#include "{config.root_cppcuit_path}/{header}"' for header in DEFAULT_HEADERS
    )

    struct_include = f'#include "{struct_options.struct_header}.hh"'

    return f"""
        {default_includes}
        {struct_include}
    
        {call_str}
    """


def main():
    args = ArgumentParser(CallOptions).parse_args(sys.argv[1:])

    config = CoreLoaderConfig.from_dict(json.load(open(args.loader_config)))

    circuit = CircuitData.from_dict(json.load(open(args.circuit_json)))

    struct = StructOptions(
        call_name=args.call_name,
        struct_header=args.struct_header,
        struct_name=args.struct_name,
    )

    print(generate_circuit_call(struct, config, circuit))


if __name__ == "__main__":
    main()
