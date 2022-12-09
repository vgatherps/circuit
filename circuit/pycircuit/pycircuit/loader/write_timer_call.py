import json
import sys
from dataclasses import dataclass

from argparse_dataclass import ArgumentParser
from pycircuit.circuit_builder.circuit import CircuitData
from pycircuit.cpp_codegen.call_generation.call_metadata import CallMetaData
from pycircuit.cpp_codegen.call_generation.generate_call_for_trigger import (
    generate_external_call_body_for,
)
from pycircuit.cpp_codegen.call_generation.timer import generate_timer_call_body_for
from pycircuit.cpp_codegen.generation_metadata import generate_global_metadata
from pycircuit.loader.loader_config import CoreLoaderConfig


@dataclass
class TimerCallOptions:
    loader_config: str
    circuit_json: str

    struct_name: str
    struct_header: str
    component_name: str


@dataclass
class TimerCallStructOptions:
    struct_name: str
    struct_header: str
    component_name: str


def generate_timer_call(
    struct_options: TimerCallStructOptions,
    config: CoreLoaderConfig,
    circuit: CircuitData,
) -> str:
    if struct_options.component_name not in circuit.components:
        raise ValueError(f"COmponent {struct_options.component_name} does not exist")

    gen_metadata = generate_global_metadata(circuit, [], struct_options.struct_name)

    annotated = gen_metadata.annotated_components[struct_options.component_name]

    call_str = generate_timer_call_body_for(annotated, gen_metadata)

    struct_include = f'#include "{struct_options.struct_header}.hh"'

    return f"""
        {struct_include}
        {call_str}
    """


def main():
    args = ArgumentParser(TimerCallOptions).parse_args(sys.argv[1:])

    config = CoreLoaderConfig.from_dict(json.load(open(args.loader_config)))

    circuit = CircuitData.from_dict(json.load(open(args.circuit_json)))

    struct = TimerCallStructOptions(
        call_name=args.call_name,
        struct_header=args.struct_header,
        struct_name=args.struct_name,
    )

    print(generate_timer_call(struct, config, circuit))


if __name__ == "__main__":
    main()
