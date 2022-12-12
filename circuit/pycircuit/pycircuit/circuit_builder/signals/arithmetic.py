from frozendict import frozendict
from pycircuit.circuit_builder.definition import CallSpec, Definition, OutputSpec


def generate_binary_definition(operator_name: str) -> Definition:
    return Definition(
        class_name=operator_name,
        output_specs=frozendict(out=OutputSpec(ephemeral=True, type_path="Output")),
        inputs=frozenset(["a", "b"]),
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
    )
