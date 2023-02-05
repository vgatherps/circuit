import sys
from dataclasses import dataclass
from shutil import rmtree
from typing import Dict, List, Optional, Tuple

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
from pycircuit.differentiator.trainer.data_writer_config import WriterConfig
from pycircuit.loader.write_timer_call import (
    TimerCallStructOptions,
    generate_timer_call,
)
from pycircuit.circuit_builder.circuit import ExternalStruct
from pycircuit.circuit_builder.circuit import OutputArray
from pycircuit.circuit_builder.component import HasOutput
from pycircuit.circuit_builder.signals.bounded_sum import bounded_sum, soft_bounded_sum
from pycircuit.trade_pressure.ephemeral_sum import ephemeral_sum
from pycircuit.trade_pressure.trade_pressure_config import (
    TradePressureConfig,
    TradePressureMarketConfig,
    TradePressureVenueConfig,
)
from pycircuit.loader.write_circuit_dot import generate_full_circuit_dot

from .call_clang_format import call_clang_format
from pycircuit.circuit_builder.signals.tree_sum import tree_sum
from pycircuit.circuit_builder.signals.bbo import bbo_wmid, bbo_mid
from pycircuit.circuit_builder.signals.returns.sided_bbo_returns import (
    sided_bbo_returns,
)
from pycircuit.circuit_builder.signals.returns.ewma_of import returns_against_ewma
from pycircuit.circuit_builder.signals.symmetric.multi_symmetric_move import (
    multi_symmetric_move,
)
from pycircuit.differentiator.graph import Graph

HEADER = "pressure"
STRUCT = "TradePressure"

USE_SYMMETRIC = True
USE_SOFT_LINREG = True


@dataclass
class TradePressureOptions:
    out_dir: str


def generate_trades_circuit_for_market_venue(
    circuit: CircuitBuilder,
    market: str,
    venue: str,
    fair: HasOutput,
    decay_source: HasOutput,
) -> Tuple[HasOutput, HasOutput]:
    trades_name = f"{market}_{venue}_trades"

    tick_detector = circuit.make_component(
        definition_name="tick_detector",
        name=f"{market}_{venue}_tick_detector",
        inputs={
            "trade": circuit.get_external(trades_name, "const Trade *"),
        },
    )

    raw_venue_pressure = circuit.make_component(
        definition_name="tick_aggregator",
        name=f"{market}_{venue}_tick_aggregator",
        inputs={
            "trade": circuit.get_external(trades_name, "const Trade *"),
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

    circuit.make_component(
        "bucket_sampler",
        name=f"{market}_{venue}_bucket_sampler",
        inputs={
            "trade": circuit.get_external(trades_name, "const Trade *"),
        },
    )

    return per_market_venue_decaying_ticks_sum, raw_venue_pressure.output("running")


def generate_depth_circuit_for_market_venue(
    circuit: CircuitBuilder,
    market: str,
    venue: str,
    config: TradePressureVenueConfig,
    decay_source: HasOutput,
) -> HasOutput:
    depth_name = f"{market}_{venue}_depth"
    book = circuit.make_component(
        definition_name="book_updater",
        name=f"{market}_{venue}_book_updater",
        inputs={
            "depth": circuit.get_external(depth_name, "const DepthUpdate *"),
        },
    )

    wmid = bbo_wmid(book.output("bbo"))

    mid = bbo_mid(book.output("bbo"))
    circuit.rename_component(mid, f"{market}_{venue}_mid")

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

    wmid_returns = returns_against_ewma(wmid, decay_source)
    fair_returns = returns_against_ewma(fair, decay_source)
    bbo_returns = sided_bbo_returns(book.output("bbo"), decay_source)

    inputs: List[HasOutput] = [wmid_returns, fair_returns, bbo_returns]

    if USE_SYMMETRIC:

        sym_move_params: List[List[HasOutput]] = []
        sym_move_reg_params: List[List[HasOutput]] = []

        for i in range(0, len(inputs)):
            row: List[HasOutput] = []
            row_reg: List[HasOutput] = []
            for j in range(0, len(inputs)):
                name = f"{market}_{venue}_symmetric_soft_{i}_{j}"
                row.append(circuit.make_parameter(name))
                name = f"{market}_{venue}_symmetric_reg_{i}_{j}"
                row_reg.append(circuit.make_parameter(name))
            sym_move_params.append(row)
            sym_move_reg_params.append(row_reg)

        move = multi_symmetric_move(
            inputs, sym_move_params, scale=10000, post_coeffs=sym_move_reg_params
        )
    else:
        move = circuit.make_constant("double", "0")

    if USE_SOFT_LINREG:
        soft_parameters: List[HasOutput] = [
            circuit.make_parameter(f"{market}_{venue}_soft_{i}")
            for i in range(0, len(inputs))
        ]
        soft_linreg_parameters: List[HasOutput] = [
            circuit.make_parameter(f"{market}_{venue}_softreg_{i}")
            for i in range(0, len(inputs))
        ]
        softreg = soft_bounded_sum(
            inputs, soft_parameters, scale=10000, post_coeffs=soft_linreg_parameters
        )
    else:
        softreg = circuit.make_constant("double", "0")

    linreg_params: List[HasOutput] = [
        circuit.make_parameter(f"{market}_{venue}_linreg_{i}")
        for i in range(0, len(inputs))
    ]

    linreg = tree_sum([inputs[i] * linreg_params[i] for i in range(0, len(inputs))])

    combined = softreg + move + linreg

    circuit.rename_component(combined, f"{market}_{venue}_depth_move")
    return combined


def generate_circuit_for_market(
    circuit: CircuitBuilder,
    market: str,
    config: TradePressureMarketConfig,
    decay_source: ComponentOutput,
):
    all_running = []
    all_ticks = []
    for (venue, venue_config) in config.venues.items():
        fair = generate_depth_circuit_for_market_venue(
            circuit, market, venue, venue_config, decay_source
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

    for (market, market_config) in trade_pressure.markets.items():
        for venue in market_config.venues.keys():
            market_venue_graph = Graph.discover_from_circuit(
                circuit, circuit.components[f"{market}_{venue}_depth_move"]
            )

            market_venue_graph.mark_stored(circuit)

            with open(f"{out_dir}/{market}_{venue}_depth_graph.json", "w") as write_to:
                write_to.write(market_venue_graph.to_json())

            target = circuit.components[f"{market}_{venue}_mid"]
            sampler = circuit.components[f"{market}_{venue}_bucket_sampler"]

            target.force_stored()
            sampler.force_stored()

            sample_config = WriterConfig(
                outputs=market_venue_graph.find_edges(),
                target_output=target.output(),
                sample_on=sampler.output(),
                ms_future=1000 * 2,
            )

            with open(
                f"{out_dir}/{market}_{venue}_writer_config.json", "w"
            ) as write_to:
                write_to.write(sample_config.to_json())

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

    with open(f"{out_dir}/CMakeLists.txt", "w") as cmake_file:
        cmake_file.write(generate_cmake_file(cc_names))


if __name__ == "__main__":
    main()
