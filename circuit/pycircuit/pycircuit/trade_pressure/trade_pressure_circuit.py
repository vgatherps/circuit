from asyncio import all_tasks
import json
import sys
from dataclasses import dataclass
from shutil import rmtree
from typing import List, Optional, Set, Tuple

from argparse_dataclass import ArgumentParser
from pycircuit.circuit_builder.circuit import (
    CallGroup,
    CircuitBuilder,
    CircuitData,
)
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
from pycircuit.circuit_builder.signals.regressions.bounded_sum import soft_bounded_sum
from pycircuit.circuit_builder.signals.minmax import clamp
from pycircuit.circuit_builder.component import Component
from pycircuit.circuit_builder.signals.regressions.activations import (
    relu,
)
from pycircuit.circuit_builder.signals.regressions.mlp import Layer, mlp
from pycircuit.circuit_builder.signals.constant import make_double
from pycircuit.circuit_builder.component import ComponentOutput
from pycircuit.circuit_builder.signals.regressions.activations import tanh
from pycircuit.trade_pressure.ephemeral_sum import ephemeral_sum
from pycircuit.trade_pressure.trade_pressure_config import (
    BasicSignalConfig,
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
from pycircuit.circuit_builder.signals.running_name import get_novel_name

HEADER = "pressure"
STRUCT = "TradePressure"

USE_SYMMETRIC = False
USE_SOFT_LINREG = True
USE_LINREG = True


DISCOUNTED_RETURNS_CLAMP: Optional[float] = 0.005


@dataclass
class TradePressureOptions:
    out_dir: str


def generate_cascading_soft_combos(
    circuit: CircuitBuilder,
    inputs: List[HasOutput],
    parameter_prefix: str,
    scale,
    use_symmetric=USE_SYMMETRIC,
    use_soft_linreg=USE_SOFT_LINREG,
    use_linreg=USE_LINREG,
) -> Component:
    if use_symmetric:

        sym_move_params: List[List[HasOutput]] = []
        sym_move_reg_params: List[List[HasOutput]] = []

        for i in range(0, len(inputs)):
            row: List[HasOutput] = []
            row_reg: List[HasOutput] = []
            for j in range(0, len(inputs)):
                name = f"{parameter_prefix}_symmetric_soft_{i}_{j}"
                row.append(circuit.make_parameter(name))
                name = f"{parameter_prefix}_symmetric_reg_{i}_{j}"
                row_reg.append(circuit.make_parameter(name))
            sym_move_params.append(row)
            sym_move_reg_params.append(row_reg)

        symmetric = multi_symmetric_move(
            inputs,
            sym_move_params,
            scale=scale,
            post_coeffs=sym_move_reg_params,
            discounted_clamp=DISCOUNTED_RETURNS_CLAMP,
        )
    else:
        symmetric = circuit.make_constant("double", "0")

    if use_soft_linreg:
        soft_parameters: List[HasOutput] = [
            circuit.make_parameter(f"{parameter_prefix}_soft_{i}")
            for i in range(0, len(inputs))
        ]
        soft_linreg_parameters: List[HasOutput] = [
            circuit.make_parameter(f"{parameter_prefix}_softreg_{i}")
            for i in range(0, len(inputs))
        ]
        softreg = soft_bounded_sum(
            inputs, soft_parameters, scale=scale, post_coeffs=soft_linreg_parameters
        )
    else:
        softreg = circuit.make_constant("double", "0")

    if use_linreg:
        linreg_params: List[HasOutput] = [
            circuit.make_parameter(f"{parameter_prefix}_linreg_{i}")
            for i in range(0, len(inputs))
        ]

        linreg = tree_sum([inputs[i] * linreg_params[i] for i in range(0, len(inputs))])
    else:
        linreg = circuit.make_constant("double", "0")

    combined = softreg + symmetric + linreg
    if DISCOUNTED_RETURNS_CLAMP is not None:
        combined = clamp(combined, DISCOUNTED_RETURNS_CLAMP)

    return combined


def generate_trades_circuit_for_market_venue(
    circuit: CircuitBuilder,
    market: str,
    venue: str,
    fair: HasOutput,
    decay_source: HasOutput,
    config: TradePressureVenueConfig,
) -> Tuple[HasOutput, HasOutput]:
    trades_name = f"{market}_{venue}_trades"

    tick_detector = circuit.make_component(
        definition_name="tick_detector",
        name=f"{market}_{venue}_tick_detector",
        inputs={
            "trade": circuit.get_external(trades_name, "const Trade *"),
        },
        params={"us_till_batch_ends": 50, "ns_till_batch_invalidation": 2000000},
    )

    raw_venue_pressure = circuit.make_component(
        definition_name="tick_aggregator",
        name=f"{market}_{venue}_tick_aggregator",
        inputs={
            "trade": circuit.get_external(trades_name, "const Trade *"),
            "fair": fair,
            "tick": tick_detector.output(),
        },
        params={
            "pricesize_weight": config.trade_pressures[0].pricesize_weight,
            "distance_weight": config.trade_pressures[0].distance_weight,
        },
    )

    triggered_tick_decay = circuit.make_triggerable_constant(
        "double", raw_venue_pressure.output("tick"), "0.98"
    )

    per_market_venue_decaying_ticks_sum = circuit.make_component(
        definition_name="running_sum",
        name=get_novel_name(f"{market}_{venue}_decaying_tick_sum"),
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


def generate_move_for_decay(
    circuit: CircuitBuilder,
    market: str,
    venue: str,
    bbo: HasOutput,
    signals: List[HasOutput],
    decay_source: HasOutput,
):
    rets: List[HasOutput] = [
        returns_against_ewma(signal, decay_source, 0.01) for signal in signals
    ]

    move_name = get_novel_name(f"{market}_{venue}_decay_depth_move")

    rets.append(sided_bbo_returns(bbo, decay_source))

    combined = generate_cascading_soft_combos(
        circuit, rets, move_name, scale=10000, use_linreg=False
    )
    circuit.rename_component(combined, move_name)
    return combined


def generate_depth_circuit_for_market_venue(
    circuit: CircuitBuilder,
    market: str,
    venue: str,
    config: TradePressureVenueConfig,
    decay_sources: List[HasOutput],
) -> HasOutput:
    depth_name = f"{market}_{venue}_depth"

    book = circuit.make_component(
        definition_name="book_updater",
        name=f"{market}_{venue}_book_updater",
        inputs={
            "depth": circuit.get_external(depth_name, "const DepthUpdate *"),
        },
    )

    circuit.add_call_group(
        depth_name,
        CallGroup(struct="DepthUpdate", external_field_mapping={"depth": depth_name}),
    )

    bbo = book.output("bbo")

    wmid = bbo_wmid(bbo)
    circuit.rename_component(wmid, f"{market}_{venue}_wmid")

    mid = bbo_mid(bbo)
    circuit.rename_component(mid, f"{market}_{venue}_mid")

    signals: List[HasOutput] = [wmid, mid]

    for (idx, impulse_params) in enumerate(config.book_fairs):
        fair = circuit.make_component(
            definition_name="book_impulse_tracker",
            name=f"{market}_{venue}_book_impulse_tracker_{idx}",
            inputs={
                "updates": book.output("updates"),
                "book": book.output("book"),
            },
            params={"scale": impulse_params.scale},
        )

        signals.append(fair)

    if "btc" not in market:
        btc_market = "btcusdt"
        btc_lead = circuit.lookup(f"{btc_market}_{venue}_depth_move")
        signals.append(btc_lead)

    moves_per_decay: List[HasOutput] = []
    for decay_source in decay_sources:
        move_for_decay = generate_move_for_decay(
            circuit=circuit,
            market=market,
            venue=venue,
            bbo=book.output("bbo"),
            signals=signals,
            decay_source=decay_source,
        )
        moves_per_decay.append(move_for_decay)

    combined = generate_cascading_soft_combos(
        circuit,
        moves_per_decay,
        f"{market}_{venue}",
        scale=10000,
        use_linreg=True,
        use_symmetric=False,
    )
    circuit.rename_component(combined, f"{market}_{venue}_depth_move")
    return combined


def generate_circuit_for_market(
    circuit: CircuitBuilder,
    market: str,
    config: TradePressureMarketConfig,
    decay_sources: List[HasOutput],
):

    all_fair_returns = []
    for (venue, venue_config) in config.venues.items():
        fair_returns = generate_depth_circuit_for_market_venue(
            circuit, market, venue, venue_config, decay_sources
        )
        all_fair_returns.append(fair_returns)

    if len(all_fair_returns) > 1:
        fairs_comb = generate_cascading_soft_combos(
            circuit,
            all_fair_returns,
            scale=10000,
            use_soft_linreg=True,
            use_linreg=True,
            use_symmetric=False,
        )
    else:
        fairs_comb = all_fair_returns[0]

    all_trade_pressures = []

    for (venue, venue_config) in config.venues.items():

        trades_name = f"{market}_{venue}_trades"
        circuit.get_external(trades_name, "const Trade *"),
        circuit.add_call_group(
            trades_name,
            CallGroup(
                struct="TradeUpdate", external_field_mapping={"trade": trades_name}
            ),
        )

    for (decay_idx, decay_source) in enumerate(decay_sources):
        all_running = []
        all_ticks = []
        for (venue, venue_config) in config.venues.items():
            # Have to be able to get parameters in there at first
            wmid = circuit.lookup(f"{market}_{venue}_wmid")
            tick, running = generate_trades_circuit_for_market_venue(
                circuit, market, venue, wmid, decay_source, venue_config
            )

            all_ticks.append(tick)
            all_running.append(running)

        per_market_running_sum = tree_sum(all_running)

        # todo tick_decay_source as well

        per_market_ticks_sum = tree_sum(all_ticks)

        total_pressure = per_market_running_sum + per_market_ticks_sum

        circuit.rename_component(
            total_pressure, f"{market}_sum_tick_running_{decay_idx}"
        )

        # Regularize this to some degree, seeing occasional large bursts and getting
        # some nans from things like e^100

        scale_1 = circuit.make_parameter(
            f"{market}_sum_tick_running_{decay_idx}_regularizer_1"
        )
        scale_2 = circuit.make_parameter(
            f"{market}_sum_tick_running_{decay_idx}_regularizer_2"
        )

        regularized_pressure = tanh(scale_1 * total_pressure) * scale_2

        circuit.rename_component(
            regularized_pressure, f"{market}_sum_tick_running_regularized_{decay_idx}"
        )

        all_trade_pressures.append(regularized_pressure)
    # This makes little mathematical sense BUT let's generate some parameters
    # for the differentiator
    networked_pressure = mlp(
        all_trade_pressures,
        [
            Layer.parameter_layer(
                3 * len(decay_sources),
                len(decay_sources),
                prefix=f"{market}_trade_mlp_relu",
                activation=relu,
            ),
            Layer.parameter_layer(
                len(decay_sources),
                3 * len(decay_sources),
                prefix=f"{market}_trade_mlp_tanh",
                activation=tanh,
            ),
        ],
    )

    tp_wacky_resnet = generate_cascading_soft_combos(
        circuit,
        networked_pressure + all_trade_pressures,
        f"{market}_networked_trade_pressure",
        use_symmetric=False,
        use_soft_linreg=True,
        use_linreg=True,
        scale=1,
    )

    # project down to some pesudo-returns sort of space
    # really need to have better built in parameter scaling
    # stuff for the differentiator
    tp_wacky_resnet = tp_wacky_resnet * make_double(1e-2)

    circuit.rename_component(tp_wacky_resnet, f"{market}_trade_pressure")

    signals = [fairs_comb, total_pressure]

    if "btc" not in market:
        btc_signal = circuit.lookup("btcusdt_overall_pred")
        signals.append(btc_signal)

    # if I *really* wanted to generated parameters, could
    # do another fancy combination
    #
    # In theory, these signals are somewhat orthogonal
    # so all the fancy discounting doesn't buy anything
    #
    # It might also horribly mess up scaling

    market_pred = generate_cascading_soft_combos(
        circuit,
        signals,
        f"{market}_final",
        scale=1,
        use_symmetric=False,
        use_soft_linreg=False,
        use_linreg=True,
    )

    circuit.rename_component(market_pred, f"{market}_overall_pred")

    return market_pred


def generate_trade_pressure_circuit(
    circuit: CircuitBuilder, config: BasicSignalConfig, decay_sources: List[HasOutput]
) -> CircuitData:

    for (market, market_config) in config.markets.items():
        generate_circuit_for_market(circuit, market, market_config, decay_sources)

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
    trade_pressure = BasicSignalConfig.from_json(trade_pressure_str)
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

    if not trade_pressure.decay_horizons_ns:
        raise ValueError("No decay half lives given")

    decay_sources = []
    for half_life_ns in trade_pressure.decay_horizons_ns:
        decay_source = circuit.make_component(
            definition_name="exp_decay_source",
            name=f"global_decay_source_{half_life_ns}",
            inputs={},
            params={"half_life_ns": half_life_ns},
        )
        decay_sources.append(decay_source)

    with CircuitContextManager(circuit):
        generate_trade_pressure_circuit(circuit, trade_pressure, decay_sources)

    # SO much duplicate code here

    def write_simmable(
        market: str,
        venue: str,
        track: HasOutput,
        block: Set[ComponentOutput],
        postfix: str,
    ):
        market_venue_graph = Graph.discover_from_circuit(
            circuit, track, block_propagating=block
        )

        market_venue_graph.mark_stored(circuit)

        with open(f"{out_dir}/{market}_{venue}_{postfix}_graph.json", "w") as write_to:
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
            f"{out_dir}/{market}_{venue}_{postfix}_writer_config.json", "w"
        ) as write_to:
            write_to.write(sample_config.to_json())

    for (market, market_config) in trade_pressure.markets.items():
        for venue in market_config.venues.keys():
            market_tp = circuit.components[f"{market}_trade_pressure"].output()
            market_move = circuit.components[f"{market}_{venue}_depth_move"].output()
            market_overall = circuit.components[f"{market}_overall_pred"].output()

            # In a real-world trading setup, you'd need to do this incrementally
            # and have most new signals track the overall prediction instead of their own
            # Since the value isn't
            #   "Who can have a standalone better prediction"
            # it's
            #   "Who can overall increase the value of the feature set"
            #
            # However I don't have the parameterization set up that well to do so
            # You could have more debate about whether this gradient propagation would
            # should go all the way up the tree per round,
            # or just do whatever increases local performance the best
            write_simmable(market, venue, market_tp, {market_move}, "trade_pressure")
            write_simmable(market, venue, market_move, {market_tp}, "depth")
            write_simmable(market, venue, market_overall, {}, "overall")

            # HACKS since I know I only have one lol
            break

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

    with open(f"{out_dir}/params.json", "w") as params_file:
        json.dump(circuit.parameters(), params_file)

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
