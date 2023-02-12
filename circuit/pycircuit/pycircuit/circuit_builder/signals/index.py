from frozendict import frozendict
from pycircuit.circuit_builder.definition import CallSpec, Definition, OutputSpec
from pycircuit.circuit_builder.definition import BasicInput


def generate_static_index_definition(offset: int) -> Definition:
    return Definition(
        class_name=f"StaticIndex",
        output_specs=frozendict(out=OutputSpec(ephemeral=True, type_path="Output")),
        inputs=frozendict({"a": BasicInput()}),
        static_call=True,
        header="signals/basic_operators.hh",
        generic_callset=CallSpec(
            observes=frozenset(),
            written_set=frozenset(["a"]),
            callback="call",
            outputs=frozenset(["out"]),
        ),
        # TODO once we support arrays can definitely have
        # a differentiable operator
        metadata=frozendict({"include_param_names": False}),
        generics_order=frozendict({"a": 0}),
        class_generics=frozendict({"N": 0}),
    ).validate()
