import json
import sys
from dataclasses import dataclass

from argparse_dataclass import ArgumentParser
from pycircuit.circuit_builder.circuit import CircuitData
from pycircuit.cpp_codegen.call_generation.init_generation.generate_init_call import (
    generate_init_call,
)
from pycircuit.cpp_codegen.generation_metadata import generate_global_metadata
from pycircuit.loader.loader_config import CoreLoaderConfig

INCLUDES = ["nlohmann/json.hpp"]


@dataclass
class CallOptions:
    loader_config: str
    circuit_json: str

    struct_name: str
    struct_header: str


@dataclass
class InitStructOptions:
    struct_name: str
    struct_header: str


def generate_circuit_init(
    struct_options: InitStructOptions, config: CoreLoaderConfig, circuit: CircuitData
) -> str:

    gen_metadata = generate_global_metadata(circuit, [], struct_options.struct_name)

    init_str = generate_init_call(struct_options.struct_name, gen_metadata)

    struct_include = f'#include "{struct_options.struct_header}.hh"'
    default_includes = "\n".join(f"#include <{inc}>" for inc in INCLUDES)
    return f"""
{default_includes}
{struct_include}
    
{init_str}
    """


def main():
    args = ArgumentParser(CallOptions).parse_args(sys.argv[1:])

    config = CoreLoaderConfig.from_dict(json.load(open(args.loader_config)))

    circuit = CircuitData.from_dict(json.load(open(args.circuit_json)))

    struct = InitStructOptions(
        struct_header=args.struct_header,
        struct_name=args.struct_name,
    )

    print(generate_circuit_init(struct, config, circuit))


if __name__ == "__main__":
    main()
