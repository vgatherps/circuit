from typing import Callable, Optional
from frozendict import frozendict
from pycircuit.circuit_builder.definition import CallSpec, Definition, OutputSpec
from pycircuit.circuit_builder.definition import BasicInput
from pycircuit.circuit_builder.component import HasOutput, Component
from pycircuit.circuit_builder.circuit_context import CircuitContextManager
from .running_name import get_novel_name


def generate_bbo_definition(name: str) -> Definition:
    return Definition(
        class_name=f"BBO{name}",
        output_specs=frozendict(out=OutputSpec(ephemeral=True, type_path="Output")),
        inputs=frozendict({"bbo": BasicInput()}),
        static_call=True,
        header="signals/market_data/bbo.hh",
        generic_callset=CallSpec(
            observes=frozenset(),
            written_set=frozenset(["bbo"]),
            callback="on_bbo",
            outputs=frozenset(["out"]),
        ),
    ).validate()


def make_bbo_op(name: str) -> Callable[[HasOutput], Component]:
    def the_op(on: HasOutput):
        f"Takes the bbo and computes the {name}"

        defin = generate_bbo_definition(name)
        defin_name = f"bbo::{name}"

        circuit = CircuitContextManager.active_circuit()

        circuit.add_definition(defin_name, defin)

        return circuit.make_component(
            defin_name, name=get_novel_name(name), inputs={"bbo": on}
        )

    return the_op


bbo_mid = make_bbo_op("Mid")
bbo_wmid = make_bbo_op("WMid")
bbo_bid_price = make_bbo_op("BidPrice")
bbo_ask_price = make_bbo_op("AskPrice")
