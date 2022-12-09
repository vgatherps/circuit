import sys
from dataclasses import dataclass
from shutil import rmtree

from argparse_dataclass import ArgumentParser
from pycircuit.circuit_builder.circuit import (
    TIME_TYPE,
    CallGroup,
    CircuitBuilder,
    CircuitData,
    OutputOptions,
)
from pycircuit.circuit_builder.definition import Definitions
from pycircuit.loader.loader_config import CoreLoaderConfig
from pycircuit.loader.write_circuit_call import CallStructOptions, generate_circuit_call
from pycircuit.loader.write_circuit_init import InitStructOptions, generate_circuit_init
from pycircuit.loader.write_circuit_struct import generate_circuit_struct_file
from pycircuit.loader.write_timer_call import (
    TimerCallStructOptions,
    generate_timer_call,
)
from pycircuit.trade_pressure.trade_pressure_config import (
    TradePressureConfig,
    TradePressureMarketConfig,
    TradePressureVenueConfig,
)

from .call_clang_format import call_clang_format
from .tree_sum import tree_sum

HEADER = "pressure"
STRUCT = "TradePressure"


@dataclass
class TradePressureOptions:
    out_dir: str


def generate_circuit_for_market_venue(
    circuit: CircuitBuilder, market: str, venue: str, config: TradePressureVenueConfig
):
    trades_name = f"{market}_{venue}_trades"
    raw_venue_pressure = circuit.make_component(
        definition_name="tick_aggregator",
        name=f"{market}_{venue}_tick_aggregator",
        inputs={
            "trade": circuit.get_external(trades_name, "Trade").output(),
            "fair": circuit.get_external(f"{market}_{venue}_fair", "double").output(),
            "tick": circuit.get_external(f"{market}_{venue}_end_tick", "Tick").output(),
            "time": circuit.get_external(f"time", TIME_TYPE).output(),
        },
    )

    circuit.add_call_group(trades_name, CallGroup(inputs={trades_name}))

    return raw_venue_pressure.output("tick"), raw_venue_pressure.output("running")


def generate_circuit_for_market(
    circuit: CircuitBuilder, market: str, config: TradePressureMarketConfig
):
    all_running = []
    all_ticks = []
    for (venue, venue_config) in config.venues.items():
        tick, running = generate_circuit_for_market_venue(
            circuit, market, venue, venue_config
        )

        all_ticks.append(tick)
        all_running.append(running)

    return all_running + all_ticks


def generate_trade_pressure_circuit(
    circuit: CircuitBuilder, config: TradePressureConfig
) -> CircuitData:

    all_sums = []
    for (market, market_config) in config.markets.items():
        all_sums += generate_circuit_for_market(circuit, market, market_config)

    total_sum = tree_sum(circuit, all_sums)

    circuit.components[total_sum.parent].output_options["out"] = OutputOptions(
        force_stored=True
    )

    return circuit


# TODO it appears like this doesn't actually
# trigger the always-valid checks


def generate_cmake_file(lib_name: str, cc_names) -> str:
    ccs = " ".join(cc_names)
    return f"""add_library({lib_name} {ccs})
target_link_libraries({lib_name} PRIVATE cppcuit_lib nlohmann_json::nlohmann_json)"""


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

    generate_trade_pressure_circuit(circuit, trade_pressure)

    # This could be much better abstracted...
    cc_names = []
    for (market, market_config) in trade_pressure.markets.items():
        for venue in market_config.venues.keys():
            local_name = f"{market}_{venue}_trades.cc"
            cc_names.append(local_name)
            file_name = f"{out_dir}/{local_name}"
            trades_call_name = f"{market}_{venue}_trades"
            content = generate_circuit_call(
                CallStructOptions(
                    struct_name=STRUCT,
                    struct_header=HEADER,
                    call_name=trades_call_name,
                ),
                config=core_config,
                circuit=circuit,
            )
            with open(file_name, "w") as write_to:
                write_to.write(call_clang_format(content))

    # Fill out some timer calls
    for component in circuit.components.values():
        timer = component.definition.timer_callback
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
        cmake_file.write(generate_cmake_file(HEADER, cc_names))


if __name__ == "__main__":
    main()
