from pycircuit.circuit_builder.circuit import CircuitBuilder, CircuitData
from pycircuit.trade_pressure.trade_pressure_config import (
    TradePressureConfig,
    TradePressureMarketConfig,
    TradePressureVenueConfig,
)
from tree_sum import tree_sum

from pycircuit.pycircuit.circuit_builder.circuit import OutputOptions


def generate_circuit_for_market_venue(
    circuit: CircuitBuilder, market: str, venue: str, config: TradePressureVenueConfig
):
    raw_venue_pressure = circuit.make_component(
        definition_name="tick_aggregator",
        name=f"{market}_{venue}_tick_aggregator",
        inputs={
            "trade": circuit.get_external(f"{market}_{venue}_trades", "Trade").output(),
            "fair": circuit.get_external(f"{market}_{venue}_fair", "double").output(),
            "tick": circuit.get_external(f"{market}_{venue}_end_tick", "Tick").output(),
        },
    )

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
