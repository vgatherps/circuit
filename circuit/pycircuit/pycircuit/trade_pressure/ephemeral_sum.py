import math
from typing import List, Sequence

from pycircuit.circuit_builder.component import HasOutput
from pycircuit.circuit_builder.circuit import CircuitBuilder, OutputArray
from pycircuit.circuit_builder.component import Component
from pycircuit.circuit_builder.signals.running_name import get_novel_name


def ephemeral_sum(
    circuit: CircuitBuilder, roots: Sequence[HasOutput], type="double"
) -> Component:
    return circuit.make_component(
        definition_name="ephemeral_sum_of",
        name=get_novel_name("ephemeral_sum"),
        inputs={"value": OutputArray(inputs=[{"value": root} for root in roots])},
        generics={"T": type},
    )
