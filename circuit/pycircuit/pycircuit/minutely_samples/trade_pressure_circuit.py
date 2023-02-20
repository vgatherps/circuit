# So much duplicated code... just a quick hack/test
import sys
from dataclasses import dataclass
from shutil import rmtree
from typing import Tuple

from argparse_dataclass import ArgumentParser
from pycircuit.circuit_builder.circuit import (
    TIME_TYPE,
    CallGroup,
    CircuitBuilder,
    CircuitData,
    ComponentOutput,
    OutputOptions,
)
from pycircuit.circuit_builder.circuit_context import CircuitContextManager
from pycircuit.circuit_builder.definition import Definitions
from pycircuit.loader.loader_config import CoreLoaderConfig
from pycircuit.loader.write_circuit_call import CallStructOptions, generate_circuit_call
from pycircuit.loader.write_circuit_call_dot import generate_circuit_call_dot
from pycircuit.loader.write_circuit_init import InitStructOptions, generate_circuit_init
from pycircuit.loader.write_circuit_struct import generate_circuit_struct_file
from pycircuit.loader.write_timer_call import (
    TimerCallStructOptions,
    generate_timer_call,
)
from pycircuit.circuit_builder.circuit import ExternalStruct
from pycircuit.minutely_samples.sample_config import MinutelySampleConfig
from pycircuit.loader.write_circuit_dot import generate_full_circuit_dot

from pycircuit.circuit_builder.signals.tree_sum import tree_sum
from pycircuit.circuit_builder.signals.bbo import bbo_mid, bbo_wmid

from pycircuit.trade_pressure.call_clang_format import call_clang_format

HEADER = "pressure"
STRUCT = "TradePressure"

SAMPLE_NAME_LIST = [
    "min_mid",
    "max_mid",
    "mean_mid",
    "mean_book_fair",
    "mean_weighted_mid",
]


@dataclass
class TradePressureOptions:
    out_dir: str


def generate_samples_for_market_venue(
    circuit: CircuitBuilder, market: str, venue: str
) -> ComponentOutput:
    depth_name = f"{market}_{venue}_depth"
    book = circuit.make_component(
        definition_name="book_updater",
        name=f"{market}_{venue}_book_updater",
        inputs={
            "depth": circuit.get_external(depth_name, "const DepthUpdate *").output(),
        },
    )

    fair = circuit.make_component(
        definition_name="book_impulse_tracker",
        name=f"{market}_{venue}_book_impulse_tracker",
        inputs={
            "updates": book.output("updates"),
            "book": book.output("book"),
            "time": circuit.get_external("time", TIME_TYPE).output(),
        },
    )

    circuit.add_call_group(
        depth_name,
        CallGroup(struct="DepthUpdate", external_field_mapping={"depth": depth_name}),
    )

    mid = bbo_mid(book.output("book"))

    mid_mean = circuit.make_component(
        definition_name="sampled_mean",
        name=f"{market}_{venue}_mid_mean",
        inputs={
            "a": mid,
        },
    )

    # Duplicate the above circuit.make_component call for min and max of mid

    mid_min = circuit.make_component(
        definition_name="sampled_min",
        name=f"{market}_{venue}_mid_min",
        inputs={
            "a": mid,
        },
    )

    mid_max = circuit.make_component(
        definition_name="sampled_max",
        name=f"{market}_{venue}_mid_max",
        inputs={
            "a": mid,
        },
    )

    wmid = bbo_wmid(book.output("book"))

    wmid_mean = circuit.make_component(
        definition_name="sampled_mean",
        name=f"{market}_{venue}_wmid_mean",
        inputs={
            "a": wmid,
        },
    )

    fair_mean = circuit.make_component(
        definition_name="sampled_mean",
        name=f"{market}_{venue}_fair_mean",
        inputs={
            "a": fair.output("fair"),
        },
    )

    mid_mean.force_stored()
    mid_min.force_stored()
    mid_max.force_stored()
    wmid_mean.force_stored()
    fair_mean.force_stored()

    return fair.output()


# TODO it appears like this doesn't actually
# trigger the always-valid checks


def generate_cmake_file(cc_names) -> str:
    ccs = " ".join(cc_names)
    return f"""\
if (NOT DEFINED CODEGEN_TARGET_NAME)
    message(FATAL_ERROR "The variable CODEGEN_TARGET_NAME must be set for codegen to call target_sources")
endif (NOT DEFINED CODEGEN_TARGET_NAME)

target_sources(${{CODEGEN_TARGET_NAME}} PRIVATE {ccs})

"""


def main():
    args = ArgumentParser(TradePressureOptions).parse_args(sys.argv[1:])

    out_dir = args.out_dir
    import os

    dir_path = os.path.dirname(os.path.realpath(__file__))
    definitions_str = open(f"{dir_path}/definitions.json").read()
    trade_pressure_str = open(f"{dir_path}/trade_pressure_config.json").read()
    loader_config_str = open(f"{dir_path}/loader.json").read()
    if os.path.exists(out_dir):
        rmtree(out_dir)
    os.mkdir(out_dir)

    definitions = Definitions.from_json(definitions_str)
    minutely = MinutelySampleConfig.from_json(trade_pressure_str)
    core_config = CoreLoaderConfig.from_json(loader_config_str)

    circuit = CircuitBuilder(definitions=definitions.definitions)

    circuit.add_call_struct_from(
        "TradeUpdate",
        trade="const Trade *",
        external_struct=ExternalStruct(
            struct_name="TradeInput",
            header="replay/md_inputs.hh",
        ),
    )

    circuit.add_call_struct_from(
        "DepthUpdate",
        depth="const DepthUpdate *",
        external_struct=ExternalStruct(
            struct_name="DiffInput",
            header="replay/md_inputs.hh",
        ),
    )

    cc_names = []
    with CircuitContextManager(circuit) as c:
        for (venue, markets) in minutely.venues.items():
            for market in markets:
                generate_samples_for_market_venue(circuit, market, venue)

                local_name = f"{market}_{venue}_depth.cc"
                cc_names.append(local_name)
                file_name = f"{out_dir}/{local_name}"
                depth_call_name = f"{market}_{venue}_depth"

                options = CallStructOptions(
                    struct_name=STRUCT,
                    struct_header=HEADER,
                    call_name=depth_call_name,
                )
                content = generate_circuit_call(
                    struct_options=options,
                    config=core_config,
                    circuit=circuit,
                )
                with open(file_name, "w") as write_to:
                    write_to.write(call_clang_format(content))

                dot_content = generate_circuit_call_dot(
                    struct_options=options,
                    config=core_config,
                    circuit=circuit,
                )

                with open(f"{out_dir}/{market}_{venue}_depth.dot", "w") as write_to:
                    write_to.write(dot_content)

    # Fill out some timer calls
    for component in circuit.components.values():
        timer = component.definition.timer_callset
        if timer is None:
            continue
        fname = f"{component.name}_timer_callback.cc"

        cc_names.append(fname)

        call = generate_timer_call(
            TimerCallStructOptions(
                struct_name=STRUCT, struct_header=HEADER, component_name=component.name
            ),
            core_config,
            circuit,
        )

        with open(f"{out_dir}/{fname}", "w") as timer_file:
            timer_file.write(call_clang_format(call))

    struct_content = generate_circuit_struct_file(
        STRUCT, config=core_config, circuit=circuit
    )
    with open(f"{out_dir}/{HEADER}.hh", "w") as struct_file:
        struct_file.write(call_clang_format(struct_content))

    dot_content = generate_full_circuit_dot(circuit)

    with open(f"{out_dir}/{HEADER}.dot", "w") as circuit_dot_file:
        circuit_dot_file.write(dot_content)

    init_content = generate_circuit_init(
        InitStructOptions(struct_name=STRUCT, struct_header=HEADER),
        config=core_config,
        circuit=circuit,
    )
    cc_names.append("init.cc")

    with open(f"{out_dir}/init.cc", "w") as init_file:
        init_file.write(call_clang_format(init_content))

    # TODO smarter parameterization
    with open(f"{out_dir}/CMakeLists.txt", "w") as cmake_file:
        cmake_file.write(generate_cmake_file(cc_names))


if __name__ == "__main__":
    main()
