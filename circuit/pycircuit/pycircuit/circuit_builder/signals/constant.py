from typing import Optional
from frozendict import frozendict
from pycircuit.circuit_builder.definition import CallSpec, Definition, OutputSpec


def generate_constant_definition(
    constant_type: str, constructor: Optional[str]
) -> Definition:
    return Definition(
        class_name=f"CtorConstant<{constant_type}>",
        output_specs=frozendict(
            out=OutputSpec(
                ephemeral=True,
                type_path="Output",
                always_valid=True,
                assume_default=True,
                default_constructor=f" = {constructor}",
            )
        ),
        inputs=frozenset(),
        static_call=True,
        header="signals/constant.hh",
        generic_callset=CallSpec(
            observes=frozenset(),
            written_set=frozenset(),
            callback=None,
        ),
    )
