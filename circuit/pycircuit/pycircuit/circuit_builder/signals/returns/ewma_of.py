from typing import Optional, Sequence
from pycircuit.circuit_builder.component import HasOutput, Component
from pycircuit.circuit_builder.circuit_context import CircuitContextManager
from pycircuit.circuit_builder.circuit import OutputArray
from ..running_name import get_novel_name
from ..minmax import clamp


def ewma_of(
    signal: HasOutput, decay_sources: HasOutput | Sequence[HasOutput]
) -> Component:
    circuit = CircuitContextManager.active_circuit()

    match decay_sources:
        case HasOutput():
            sources_list = [decay_sources]
        case _:
            sources_list = list(decay_sources)

    return circuit.make_component(
        "ewma",
        name=get_novel_name("ewma"),
        inputs={
            "signal": signal,
            "decay": OutputArray(inputs=[{"decay": dec} for dec in sources_list]),
        },
    )


def returns_against_ewma(
    signal: HasOutput,
    decay_sources: HasOutput | Sequence[HasOutput],
    clamp_to: Optional[float] = None,
) -> Component:
    ewma = ewma_of(signal, decay_sources)

    ret = (signal - ewma) / signal

    if clamp_to is not None:
        return clamp(ret, clamp_to)
    else:
        return ret


def difference_to_ewma(
    signal: HasOutput, decay_sources: HasOutput | Sequence[HasOutput]
) -> Component:
    ewma = ewma_of(signal, decay_sources)

    return signal - ewma
