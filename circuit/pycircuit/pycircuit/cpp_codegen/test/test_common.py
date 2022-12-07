from frozendict import frozendict
from pycircuit.circuit_builder.circuit import Component, ComponentInput
from pycircuit.circuit_builder.definition import (
    CallSpec,
    Definition,
    InitSpec,
    InputSpec,
    OutputSpec,
)
from pycircuit.cpp_codegen.generation_metadata import AnnotatedComponent, OutputMetadata

OUT_B_VALID_INDEX = 2
COMPONENT_NAME = "test"
COMPONENT_CLASS = "TestComponent"
OUT_A = "out_a"
OUT_A_CLASS = "OutA"
OUT_B = "out_b"
OUT_B_CLASS = "OutB"
OUT_C = "out_c"
OUT_C_CLASS = "OutC"

A_INPUT = ComponentInput(parent="external", input_name="a", output_name="val_a")
B_INPUT = ComponentInput(parent="fake", input_name="b", output_name="fake_out")
C_INPUT = ComponentInput(parent="fake", input_name="c", output_name="fake_out_c")

AB_CALLSET = CallSpec(
    written_set=frozenset({"a", "b"}),
    observes=frozenset(),
    callback="call_out_a",
    outputs=frozenset({OUT_A}),
)

BC_CALLSET = CallSpec(
    written_set=frozenset({"b", "c"}),
    observes=frozenset(),
    callback="call_out_b",
    outputs=frozenset({OUT_B}),
)

GENERIC_CALLSET = CallSpec(
    written_set=frozenset({"a", "b", "c"}),
    observes=frozenset(),
    callback="call",
    outputs=frozenset({OUT_A, OUT_B}),
)


def basic_definition(generic_callset=GENERIC_CALLSET) -> Definition:
    return Definition(
        input_specs=frozendict(
            {
                "a": InputSpec(),
                "b": InputSpec(),
                "c": InputSpec(),
            }
        ),
        output_specs=frozendict(
            {
                OUT_A: OutputSpec(ephemeral=True, type_path=OUT_A_CLASS),
                OUT_B: OutputSpec(ephemeral=False, type_path=OUT_B_CLASS),
                OUT_C: OutputSpec(
                    ephemeral=True, type_path=OUT_C_CLASS, always_valid=True
                ),
            }
        ),
        class_name=COMPONENT_CLASS,
        init_spec=InitSpec(init_call="dummy"),
        header="test.hh",
        generic_callset=generic_callset,
        callsets=frozenset(
            {
                AB_CALLSET,
                BC_CALLSET,
            }
        ),
    )


def basic_component() -> Component:
    comp = Component(
        inputs=frozendict({"a": A_INPUT, "b": B_INPUT, "c": C_INPUT}),
        output_options={},
        definition=basic_definition(),
        name="test",
        index=OUT_B_VALID_INDEX,
    )
    comp.validate()
    return comp


def basic_annotated(is_c_ephemeral: bool = False) -> AnnotatedComponent:
    return AnnotatedComponent(
        component=basic_component(),
        output_data={
            OUT_A: OutputMetadata(validity_index=None, is_value_ephemeral=True),
            OUT_B: OutputMetadata(
                validity_index=OUT_B_VALID_INDEX, is_value_ephemeral=False
            ),
            OUT_C: OutputMetadata(
                validity_index=None, is_value_ephemeral=is_c_ephemeral
            ),
        },
        call_root="dummy_for_now",
        class_generics="",
    )
