from frozendict import frozendict
from pycircuit.circuit_builder.definition import CallSpec, Definition, OutputSpec
from pycircuit.circuit_builder.definition import BasicInput


def generate_binary_definition(diff_name: str, operator_name: str) -> Definition:
    return Definition(
        class_name=operator_name,
        output_specs=frozendict(out=OutputSpec(ephemeral=True, type_path="Output")),
        inputs=frozendict({"a": BasicInput(), "b": BasicInput()}),
        static_call=True,
        header="signals/basic_arithmetic.hh",
        generic_callset=CallSpec(
            observes=frozenset(),
            written_set=frozenset(["a", "b"]),
            callback="call",
            outputs=frozenset(["out"]),
            input_struct_path="Input",
        ),
        generics_order=frozendict(a=0, b=1),
        differentiable_operator_name=diff_name,
        metadata=frozendict({"include_param_names": False}),
    ).validate()
