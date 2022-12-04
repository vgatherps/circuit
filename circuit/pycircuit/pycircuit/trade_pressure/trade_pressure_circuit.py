from pycircuit.circuit_builder.circuit import (
    CallGroup,
    CircuitBuilder,
    CircuitData,
    OutputOptions,
)
from pycircuit.circuit_builder.definition import Definitions
from pycircuit.loader.loader_config import CoreLoaderConfig
from pycircuit.loader.write_circuit_call import StructOptions, generate_circuit_call
from pycircuit.loader.write_circuit_struct import generate_circuit_struct_file

core_confog = CoreLoaderConfig
from pycircuit.trade_pressure.trade_pressure_config import (
    TradePressureConfig,
    TradePressureMarketConfig,
    TradePressureVenueConfig,
)

from .tree_sum import tree_sum


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


def main():
    import os

    dir_path = os.path.dirname(os.path.realpath(__file__))
    definitions_str = open(f"{dir_path}/definitions.json").read()
    trade_pressure_str = open(f"{dir_path}/trade_pressure_config.json").read()
    loader_config_str = open(f"{dir_path}/loader.json").read()
    definitions = Definitions.from_json(definitions_str)
    trade_pressure = TradePressureConfig.from_json(trade_pressure_str)
    core_config = CoreLoaderConfig.from_json(loader_config_str)

    circuit = CircuitBuilder(definitions=definitions.definitions)

    generate_trade_pressure_circuit(circuit, trade_pressure)

    a_call_str = generate_circuit_call(
        StructOptions(
            struct_name="pressure",
            struct_header="pressure.hh",
            call_name="SPY_BATS_trades",
        ),
        config=core_config,
        circuit=circuit,
    )

    print(a_call_str)


if __name__ == "__main__":
    main()
