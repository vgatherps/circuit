from typing import Any, Dict, Optional
from frozendict import frozendict
from pycircuit.circuit_builder.definition import (
    CallSpec,
    Definition,
    InputMetadata,
    OutputSpec,
    InitSpec,
)
from pycircuit.circuit_builder.definition import BasicInput
from pycircuit.circuit_builder.component import HasOutput


def clean_float_name(f_name: str) -> str:
    return f_name.replace(".", "_").replace("-", "_")


def make_double(val: float) -> HasOutput:
    from pycircuit.circuit_builder.circuit_context import CircuitContextManager

    circuit = CircuitContextManager.active_circuit()
    return circuit.make_constant("double", str(val))


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


def _do_generate_parameter_definition(required: bool, op_name: str) -> Definition:
    defin = Definition(
        class_name=f"DoubleParameter<{str(required).lower()}>",
        output_specs=frozendict(
            out=OutputSpec(
                type_path="Output",
                always_valid=True,
            )
        ),
        inputs=frozendict(
            {"a": BasicInput(meta=InputMetadata(optional=True, allow_unused=True))}
        ),
        static_call=True,
        header="signals/parameter.hh",
        init_spec=InitSpec(
            init_call="init",
            takes_params=True,
        ),
        differentiable_operator_name=op_name,
    )
    defin.validate()
    return defin


def generate_parameter_definition(required: bool) -> Definition:
    return _do_generate_parameter_definition(required, "parameter")


def generate_summary_definition(summary: str) -> Definition:
    return _do_generate_parameter_definition(False, summary)
