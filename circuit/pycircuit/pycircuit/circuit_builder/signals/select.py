from typing import List
from pycircuit.circuit_builder.circuit import Component, HasOutput
from pycircuit.circuit_builder.signals.running_name import get_novel_name
from pycircuit.circuit_builder.circuit_context import CircuitContextManager

# Selects a if the selector is true, otherwise b
def select(a: HasOutput, b: HasOutput, selector: HasOutput) -> Component:

    context = CircuitContextManager.active_circuit()

    return context.make_component(
        definition_name="select",
        name=get_novel_name("select"),
        inputs={"a": a, "b": b, "select_a": selector},
    )
