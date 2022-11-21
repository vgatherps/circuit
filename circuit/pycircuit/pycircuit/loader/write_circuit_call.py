import json
import sys
from dataclasses import dataclass

from argparse_dataclass import ArgumentParser
from pycircuit.circuit_builder.circuit import CircuitData
from pycircuit.cpp_codegen.call_generation.call_headers import (
    DEFAULT_HEADERS,
    get_headers_for,
)
from pycircuit.cpp_codegen.call_generation.call_metadata import CallMetaData
from pycircuit.cpp_codegen.call_generation.generate_call_for_trigger import (
    generate_external_call_body_for,
)
from pycircuit.cpp_codegen.generation_metadata import generate_struct_metadata
from pycircuit.loader.loader_config import CoreLoaderConfig


@dataclass
class CallOptions:
    loader_config: str
    circuit_json: str

    call_name: str
    struct_name: str


def main():
    args = ArgumentParser(CallOptions).parse_args(sys.argv[1:])

    config = CoreLoaderConfig.from_dict(json.load(open(args.loader_config)))

    circuit = CircuitData.from_dict(json.load(open(args.circuit_json)))

    if args.call_name not in circuit.call_groups:
        raise ValueError(f"Call {args.call_name} not contained in circuit config")

    call = circuit.call_groups[args.call_name]
    metadata = CallMetaData(triggered=call.inputs, call_name=args.call_name)

    gen_metadata = generate_struct_metadata(circuit, [metadata], args.struct_name)

    call = generate_external_call_body_for(metadata, gen_metadata)

    headers = get_headers_for(metadata, gen_metadata)

    default_includes = "\n".join(
        f'#include "{config.root_cppcuit_path}/{header}"' for header in DEFAULT_HEADERS
    )

    signal_includes = "\n".join(
        f'#include "{config.root_signals_path}/{header}"' for header in headers
    )

    file = f"""
        {default_includes}
        {signal_includes}
    
        {call}
    """

    print(file)


if __name__ == "__main__":
    main()
