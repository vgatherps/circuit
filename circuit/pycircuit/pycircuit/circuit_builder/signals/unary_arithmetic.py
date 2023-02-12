from typing import Callable
from frozendict import frozendict
from pycircuit.circuit_builder.definition import CallSpec, Definition, OutputSpec
from pycircuit.circuit_builder.definition import BasicInput
from pycircuit.circuit_builder.circuit_context import CircuitContextManager
from pycircuit.circuit_builder.component import HasOutput, Component
from .running_name import get_novel_name


def generate_unary_definition(diff_name: str, operator_name: str) -> Definition:
    return Definition(
        class_name=operator_name,
        output_specs=frozendict(out=OutputSpec(ephemeral=True, type_path="Output")),
        inputs=frozendict({"a": BasicInput()}),
        static_call=True,
        header="signals/basic_arithmetic.hh",
        generic_callset=CallSpec(
            observes=frozenset(),
            written_set=frozenset(["a"]),
            callback="call",
            outputs=frozenset(["out"]),
            input_struct_path="Input",
        ),
        generics_order=frozendict(a=0),
        differentiable_operator_name=diff_name,
        metadata=frozendict({"include_param_names": False}),
    ).validate()


def _make_unary_component(
    def_name: str, class_name: str
) -> Callable[[HasOutput], Component]:
    def actual(output: HasOutput) -> Component:

        context = CircuitContextManager.active_circuit()

        definition = generate_unary_definition(def_name, class_name)

        context.add_definition(def_name, definition)

        return context.make_component(
            definition_name=def_name,
            name=get_novel_name(def_name),
            inputs={"a": output},
        )

    return actual


clog = _make_unary_component("log", "LogComponent")
cexp = _make_unary_component("exp", "ExpComponent")
csqrt = _make_unary_component("sqrt", "SqrtComponent")
cabs = _make_unary_component("abs", "AbsComponent")
cneg = _make_unary_component("neg", "NegComponent")
