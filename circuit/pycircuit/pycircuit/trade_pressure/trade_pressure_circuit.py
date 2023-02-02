import sys
from dataclasses import dataclass
from shutil import rmtree
from typing import List, Tuple

from argparse_dataclass import ArgumentParser
from pycircuit.circuit_builder.circuit import (
    TIME_TYPE,
    CallGroup,
    CircuitBuilder,
    CircuitData,
    ComponentOutput,
)
from pycircuit.circuit_builder.component import ComponentOutput
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
from pycircuit.circuit_builder.circuit import OutputArray
from pycircuit.circuit_builder.component import HasOutput
from pycircuit.trade_pressure.ephemeral_sum import ephemeral_sum
from pycircuit.trade_pressure.trade_pressure_config import (
    TradePressureConfig,
    TradePressureMarketConfig,
    TradePressureVenueConfig,
)
from pycircuit.loader.write_circuit_dot import generate_full_circuit_dot

from .call_clang_format import call_clang_format
from pycircuit.circuit_builder.signals.tree_sum import tree_sum

HEADER = "pressure"
STRUCT = "TradePressure"


@dataclass
class TradePressureOptions:
    out_dir: str


def generate_trades_circuit_for_market_venue(
    circuit: CircuitBuilder,
    market: str,
    venue: str,
    fair: ComponentOutput,
    decay_source: HasOutput,
) -> Tuple[ComponentOutput, ComponentOutput]:
    trades_name = f"{market}_{venue}_trades"

    tick_detector = circuit.make_component(
        definition_name="tick_detector",
        name=f"{market}_{venue}_tick_detector",
        inputs={
            "trade": circuit.get_external(trades_name, "const Trade *").output(),
        },
    )

    raw_venue_pressure = circuit.make_component(
        definition_name="tick_aggregator",
        name=f"{market}_{venue}_tick_aggregator",
        inputs={
            "trade": circuit.get_external(trades_name, "const Trade *").output(),
            "fair": fair,
            "tick": tick_detector.output(),
        },
    )

    circuit.add_call_group(
        trades_name,
        CallGroup(struct="TradeUpdate", external_field_mapping={"trade": trades_name}),
    )

    triggered_tick_decay = circuit.make_triggerable_constant(
        "double", raw_venue_pressure.output("tick"), "0.98"
    )

    per_market_venue_decaying_ticks_sum = circuit.make_component(
        definition_name="running_sum",
        name=f"{market}_{venue}_decaying_tick_sum",
        inputs={
            "tick": raw_venue_pressure.output("tick"),
            "decay": OutputArray(
                inputs=[{"decay": decay_source}, {"decay": triggered_tick_decay}]
            ),
        },
    )

    return per_market_venue_decaying_ticks_sum.output(), raw_venue_pressure.output(
        "running"
    )


def generate_depth_circuit_for_market_venue(
    circuit: CircuitBuilder, market: str, venue: str, config: TradePressureVenueConfig
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
        },
    )

    circuit.add_call_group(
        depth_name,
        CallGroup(struct="DepthUpdate", external_field_mapping={"depth": depth_name}),
    )

    return fair.output()


def generate_circuit_for_market(
    circuit: CircuitBuilder,
    market: str,
    config: TradePressureMarketConfig,
    decay_source: ComponentOutput,
):
    all_running = []
    all_ticks: List[ComponentOutput] = []
    for (venue, venue_config) in config.venues.items():
        fair = generate_depth_circuit_for_market_venue(
            circuit, market, venue, venue_config
        )
        tick, running = generate_trades_circuit_for_market_venue(
            circuit, market, venue, fair, decay_source
        )

        all_ticks.append(tick)
        all_running.append(running)

    per_market_running_sum = tree_sum(all_running)

    # todo tick_decay_source as well

    per_market_ticks_sum = ephemeral_sum(circuit, all_ticks)

    total_pressure = per_market_running_sum + per_market_ticks_sum
    total_pressure.force_stored()
    circuit.rename_component(total_pressure, f"{market}_sum_tick_running")


def generate_trade_pressure_circuit(
    circuit: CircuitBuilder, config: TradePressureConfig, decay_source: ComponentOutput
) -> CircuitData:

    for (market, market_config) in config.markets.items():
        generate_circuit_for_market(circuit, market, market_config, decay_source)

    return circuit


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
    trade_pressure = TradePressureConfig.from_json(trade_pressure_str)
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

    decay_source = circuit.make_component(
        definition_name="exp_decay_source",
        name="global_decay_source",
        inputs={},
    )

    with CircuitContextManager(circuit):
        generate_trade_pressure_circuit(circuit, trade_pressure, decay_source)

    # This could be much better abstracted...
    cc_names = []
    for (market, market_config) in trade_pressure.markets.items():
        for venue in market_config.venues.keys():
            local_name = f"{market}_{venue}_trades.cc"
            cc_names.append(local_name)
            file_name = f"{out_dir}/{local_name}"
            trades_call_name = f"{market}_{venue}_trades"

            options = CallStructOptions(
                struct_name=STRUCT,
                struct_header=HEADER,
                call_name=trades_call_name,
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

            with open(f"{out_dir}/{market}_{venue}_trades.dot", "w") as write_to:
                write_to.write(dot_content)

    for (market, market_config) in trade_pressure.markets.items():
        for venue in market_config.venues.keys():
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
