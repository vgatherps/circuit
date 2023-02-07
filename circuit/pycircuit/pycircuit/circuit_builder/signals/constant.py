from typing import Optional
from frozendict import frozendict
from pycircuit.circuit_builder.definition import (
    CallSpec,
    Definition,
    OutputSpec,
    InitSpec,
)
from pycircuit.circuit_builder.definition import BasicInput


def clean_float_name(f_name: str) -> str:
    return f_name.replace(".", "_").replace("-", "_")


def generate_constant_definition(constant_type: str, constructor: str) -> Definition:
    defin = Definition(
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
        inputs=frozendict(),
        static_call=True,
        header="signals/constant.hh",
        differentiable_operator_name="constant",
        metadata=frozendict({"constant_value": constructor}),
    )
    defin.validate()
    return defin


def generate_triggerable_constant_definition(
    constant_type: str, constructor: str
) -> Definition:
    defin = Definition(
        class_name=f"TriggerableConstant<{constant_type}>",
        output_specs=frozendict(
            out=OutputSpec(
                ephemeral=True,
                type_path="Output",
                assume_invalid=True,
                assume_default=True,
                default_constructor=f" = {constructor}",
            )
        ),
        inputs=frozendict({"tick": BasicInput()}),
        static_call=True,
        header="signals/constant.hh",
        generic_callset=CallSpec(
            written_set=frozenset(["tick"]),
            observes=frozenset(),
            outputs=frozenset(["out"]),
            callback="tick",
        ),
        differentiable_operator_name="constant",
        metadata=frozendict({"constant_value": constructor}),
    )

    defin.validate()
    return defin


def generate_parameter_definition(required: bool) -> Definition:
    defin = Definition(
        class_name=f"DoubleParameter<{str(required).lower()}>",
        output_specs=frozendict(
            out=OutputSpec(
                type_path="Output",
                always_valid=True,
            )
        ),
        inputs=frozendict(),
        static_call=True,
        header="signals/parameter.hh",
        init_spec=InitSpec(
            init_call="init",
            takes_params=True,
        ),
        differentiable_operator_name="parameter",
    )
    defin.validate()
    return defin
