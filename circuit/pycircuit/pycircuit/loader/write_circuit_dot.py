import json
import sys

from argparse_dataclass import ArgumentParser
from pycircuit.circuit_builder.circuit import CircuitData
from pycircuit.cpp_codegen.call_generation.call_metadata import CallMetaData
from pycircuit.cpp_codegen.call_generation.generate_dot_for_trigger import (
    generate_external_dot_body_for,
)
from pycircuit.cpp_codegen.generation_metadata import generate_global_metadata
from pycircuit.loader.loader_config import CoreLoaderConfig

from .write_circuit_call import CallOptions, CallStructOptions


def generate_circuit_dot(
    struct_options: CallStructOptions, config: CoreLoaderConfig, circuit: CircuitData
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

    return generate_external_dot_body_for(metadata, gen_metadata)


def main():
    args = ArgumentParser(CallOptions).parse_args(sys.argv[1:])

    config = CoreLoaderConfig.from_dict(json.load(open(args.loader_config)))

    circuit = CircuitData.from_dict(json.load(open(args.circuit_json)))

    struct = CallStructOptions(
        call_name=args.call_name,
        struct_header=args.struct_header,
        struct_name=args.struct_name,
    )

    print(generate_circuit_dot(struct, config, circuit))


if __name__ == "__main__":
    main()
