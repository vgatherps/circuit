from pycircuit.circuit_builder.circuit import Component, HasOutput
from pycircuit.circuit_builder.circuit_context import CircuitContextManager
from pycircuit.circuit_builder.signals.arithmetic import generate_binary_definition
from pycircuit.circuit_builder.signals.running_name import get_novel_name


def _do_minmax_of(
    a: HasOutput, b: HasOutput, def_name: str, class_name: str
) -> Component:
    context = CircuitContextManager.active_circuit()

    definition = generate_binary_definition(class_name)

    context.add_definititon(def_name, definition)

    return context.make_component(
        definition_name=def_name,
        name=get_novel_name(def_name),
        inputs={"a": a.output(), "b": b.output()},
    )


def min_of(a: HasOutput, b: HasOutput) -> Component:
    return _do_minmax_of(a, b, "min", "MinComponent")


def max_of(a: HasOutput, b: HasOutput) -> Component:
    return _do_minmax_of(a, b, "max", "MaxComponent")
