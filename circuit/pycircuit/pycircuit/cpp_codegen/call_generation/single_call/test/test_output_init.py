from pycircuit.cpp_codegen.call_generation.single_call.generate_output_calldata import (
    generate_value_inits,
)
from pycircuit.cpp_codegen.test.test_common import (
    COMPONENT_NAME,
    OUT_A,
    OUT_A_CLASS,
    OUT_B,
    OUT_B_CLASS,
    basic_annotated,
)

INIT_A_LINE = (
    f"{COMPONENT_NAME}TypeAlias::{OUT_A_CLASS} {COMPONENT_NAME}_{OUT_A}_EV__{{}};"
)
REF_A_LINE = f"{COMPONENT_NAME}TypeAlias::{OUT_A_CLASS}& {COMPONENT_NAME}_{OUT_A} = {COMPONENT_NAME}_{OUT_A}_EV__;"
REF_B_LINE = f"{COMPONENT_NAME}TypeAlias::{OUT_B_CLASS}& {COMPONENT_NAME}_{OUT_B} = _outputs.{COMPONENT_NAME}_{OUT_B};"


def test_no_output_init():
    annotated = basic_annotated()

    output_inits = generate_value_inits(annotated, set())
    assert output_inits == ""


def test_single_output_init_ephemeral():
    annotated = basic_annotated()

    output_inits = generate_value_inits(annotated, {OUT_A})

    assert output_inits == "\n".join([INIT_A_LINE, REF_A_LINE])


def test_single_output_init_nonephemeral():
    annotated = basic_annotated()

    output_inits = generate_value_inits(annotated, {OUT_B})
    assert output_inits == REF_B_LINE


def test_both_output_init():
    annotated = basic_annotated()

    output_inits = generate_value_inits(annotated, [OUT_B, OUT_A])
    assert output_inits == "\n".join([REF_B_LINE, INIT_A_LINE, REF_A_LINE])
