import json
import sys
from dataclasses import dataclass
from shutil import rmtree
from typing import List, Set, Tuple

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
from pycircuit.circuit_builder.component import Component
from pycircuit.circuit_builder.signals.regressions.activations import (
    relu,
)
from pycircuit.circuit_builder.signals.regressions.mlp import Layer, mlp
from pycircuit.circuit_builder.signals.constant import make_double
from pycircuit.circuit_builder.component import ComponentOutput
from pycircuit.circuit_builder.signals.regressions.activations import tanh
from pycircuit.circuit_builder.signals.normalizer import Normalizer
from pycircuit.circuit_builder.signals.book.static_book_fair import (
    make_static_book_fair,
)
from pycircuit.trade_pressure.trade_pressure_config import StaticBookFairConfig
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


@dataclass
class TradePressureOptions:
    out_dir: str


def pointless_mlp(inputs: List[HasOutput], prefix: str) -> List[HasOutput]:
    return mlp(
        inputs,
        [
            Layer.parameter_layer(
                2 * len(inputs),
                len(inputs),
                activation=tanh,
                prefix=f"{prefix}_tanh_scaleup",
            ),
            Layer.parameter_layer(
                2 * len(inputs),
                2 * len(inputs),
                activation=relu,
                prefix=f"{prefix}_relu",
            ),
            Layer.parameter_layer(
                len(inputs),
                2 * len(inputs),
                activation=tanh,
                prefix=f"{prefix}_tanh_scaledown",
            ),
        ],
    )


def generate_cascading_soft_combos(
    circuit: CircuitBuilder,
    inputs: List[HasOutput],
    parameter_prefix: str,
    use_symmetric=USE_SYMMETRIC,
    use_soft_linreg=USE_SOFT_LINREG,
    use_linreg=USE_LINREG,
    normalize: bool | Normalizer = True,
    denormalize: bool = True,
) -> Component:

    match normalize:
        case True as do_normalize:
            do_normalize = normalize
            normalizer = Normalizer(inputs[0])
        case False as do_normalize:
            pass
        case Normalizer() as normalizer:
            do_normalize = True

    if do_normalize:
        inputs = [normalizer.normalize(input) for input in inputs]

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
            post_coeffs=sym_move_reg_params,
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
            inputs, soft_parameters, post_coeffs=soft_linreg_parameters
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

    if do_normalize and denormalize:
        combined = normalizer.denormalize(combined)

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


def generate_static_book_aggregation(
    circuit: CircuitBuilder,
    market: str,
    venue: str,
    book: HasOutput,
    mid: HasOutput,
    static_fairs: StaticBookFairConfig,
):
    all_static_fairs = []

    for aggregation in static_fairs.aggregation_returns:
        aggregated = circuit.make_component(
            "book_aggregator",
            name=get_novel_name(f"{market}_{venue}_book_aggregation"),
            inputs={"book": book},
            params={"ratio_per_group": aggregation},
            generics={"N": str(static_fairs.levels)},
        )

        for i in range(static_fairs.n_scales):

            fair = make_static_book_fair(
                aggregated,
                mid,
                static_fairs.levels,
                prefix=get_novel_name(f"{market}_{venue}_static_fair_{i}_"),
            )

            all_static_fairs.append(fair)

    returns_to_mid = [(fair - mid) / mid for fair in all_static_fairs]

    # yet again 100000 params for the sake of stressing graph thing
    # theoretically calculating best adjusted mid returns given others...
    norm = Normalizer(returns_to_mid[0])
    mid_projected = generate_cascading_soft_combos(
        circuit,
        returns_to_mid,
        f"{market}_{venue}_projected_static_difference",
        use_symmetric=True,
        use_soft_linreg=True,
        use_linreg=True,
        normalize=norm,
        denormalize=False,
    )

    circuit.rename_component(mid_projected, f"{market}_{venue}_static_fair_projection")

    denorm_min = norm.denormalize(mid_projected)

    return (denorm_min * mid) + mid


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

    # Do not denormalise, as we just pipe this further into more stuff
    combined = generate_cascading_soft_combos(
        circuit, rets, move_name, use_linreg=True, denormalize=False, use_symmetric=True
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

    book_manager = circuit.make_component(
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

    bbo = book_manager.output("bbo")

    wmid = bbo_wmid(bbo)
    circuit.rename_component(wmid, f"{market}_{venue}_wmid")

    mid = bbo_mid(bbo)
    circuit.rename_component(mid, f"{market}_{venue}_mid")

    signals: List[HasOutput] = [wmid, mid]

    # referenced later
    # should one day make this not such spaghetti
    generate_static_book_aggregation(
        circuit,
        market,
        venue,
        book_manager.output("book"),
        wmid,
        config.static_book_fair_config,
    )

    for (idx, impulse_params) in enumerate(config.book_fairs):
        fair = circuit.make_component(
            definition_name="book_impulse_tracker",
            name=f"{market}_{venue}_book_impulse_tracker_{idx}",
            inputs={
                "updates": book_manager.output("updates"),
                "book": book_manager.output("book"),
            },
            params={"scale": impulse_params.scale},
        )

        signals.append(fair)

    moves_per_decay: List[HasOutput] = []
    for decay_source in decay_sources:
        move_for_decay = generate_move_for_decay(
            circuit=circuit,
            market=market,
            venue=venue,
            bbo=book_manager.output("bbo"),
            signals=signals,
            decay_source=decay_source,
        )
        moves_per_decay.append(move_for_decay)

    # This doesn't make much sense but might as well add some parameters

    moves_mlp = pointless_mlp(moves_per_decay, f"{market}_{venue}_move")

    move_set = moves_per_decay + moves_mlp
    if "btc" not in market or False:
        btc_market = "btcusdt"
        btc_lead = circuit.lookup(f"{btc_market}_{venue}_depth_move")
        move_set.append(btc_lead)

    combined = generate_cascading_soft_combos(
        circuit,
        move_set,
        f"{market}_{venue}",
        use_linreg=True,
        use_symmetric=False,
        normalize=False,
        use_soft_linreg=True,
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

    fairs_comb: HasOutput
    if len(all_fair_returns) > 1:
        fairs_comb = generate_cascading_soft_combos(
            circuit,
            all_fair_returns,
            parameter_prefix=f"{market}_all_fairs_combination",
            use_soft_linreg=True,
            use_linreg=True,
            use_symmetric=False,
            normalize=False,
        )
    else:
        fairs_comb = all_fair_returns[0]

    all_trade_pressures: List[HasOutput] = []

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

        all_trade_pressures.append(total_pressure)

    normalizer = Normalizer(all_trade_pressures[0])

    normalized_tp = [normalizer.normalize(tp) for tp in all_trade_pressures]

    tp_mlp = pointless_mlp(normalized_tp, f"{market}_trade_pressure")
    tp_softreg = generate_cascading_soft_combos(
        circuit,
        normalized_tp + tp_mlp,
        f"{market}_networked_trade_pressure",
        use_symmetric=False,
        use_soft_linreg=True,
        use_linreg=True,
        normalize=False,
    )

    # project down to some pesudo-returns sort of space
    # really need to have better built in parameter scaling
    # stuff for the differentiator

    circuit.rename_component(tp_softreg, f"{market}_trade_pressure")

    signals = [fairs_comb, tp_softreg]

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

    normalised_market_pred = generate_cascading_soft_combos(
        circuit,
        signals,
        f"{market}_final",
        use_symmetric=False,
        use_soft_linreg=False,
        use_linreg=True,
        normalize=False,
    )

    circuit.rename_component(normalised_market_pred, f"{market}_overall_pred")

    # TODO re-insert normalization parameters from target
    return normalised_market_pred


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
            market_static = circuit.components[
                f"{market}_{venue}_static_fair_projection"
            ].output()
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
            write_simmable(market, venue, market_static, {}, "static_fair")

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
