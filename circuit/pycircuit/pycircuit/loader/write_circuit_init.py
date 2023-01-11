import json
import sys
from dataclasses import dataclass

from argparse_dataclass import ArgumentParser
from pycircuit.circuit_builder.circuit import CircuitData
from pycircuit.cpp_codegen.call_generation.init_generation.generate_init_call import (
    generate_init_call,
)
from pycircuit.cpp_codegen.generation_metadata import generate_global_metadata
from pycircuit.cpp_codegen.struct_generation.generate_val_load import (
    generate_checks_for_all_components,
)
from pycircuit.loader.loader_config import CoreLoaderConfig
from pycircuit.cpp_codegen.call_generation.call_lookup.generate_call_lookup import (
    generate_true_loader_body,
    top_level_real_loader,
)

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
    loader_prefix = f"{struct_options.struct_name}::"
    lookup_str = generate_true_loader_body(circuit.call_groups, prefix=loader_prefix)
    lookup_signature = top_level_real_loader(prefix=loader_prefix)
    val_lookup_str = generate_checks_for_all_components(
        list(gen_metadata.annotated_components.values()), struct_options.struct_name
    )

    struct_include = f'#include "{struct_options.struct_header}.hh"'
    default_includes = "\n".join(f"#include <{inc}>" for inc in INCLUDES)
    return f"""
{default_includes}
{struct_include}
    
{init_str}

{lookup_signature} {{
// Compatibility shim
{lookup_str}
}}

{val_lookup_str}"""


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
