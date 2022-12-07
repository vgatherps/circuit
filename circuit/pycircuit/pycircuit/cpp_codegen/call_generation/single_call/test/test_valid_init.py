import pytest
from pycircuit.cpp_codegen.call_generation.single_call.generate_output_calldata import (
    generate_is_valid_inits,
    generate_value_inits,
)
from pycircuit.cpp_codegen.test.test_common import (
    COMPONENT_NAME,
    OUT_A,
    OUT_B,
    OUT_C,
    basic_annotated,
)


def test_no_output_init():
    annotated = basic_annotated()

    output_inits = generate_value_inits(annotated, set())
    assert output_inits == ""


def test_single_output_init_ephemeral():
    annotated = basic_annotated()

    output_inits = generate_is_valid_inits(annotated, {OUT_A})
    assert output_inits == f"bool {COMPONENT_NAME}_{OUT_A}_IV = false;"


def test_single_output_init_nonephemeral():
    annotated = basic_annotated()

    output_inits = generate_is_valid_inits(annotated, {OUT_B})
    assert output_inits == ""


def test_both_output_init():
    annotated = basic_annotated()

    output_inits = generate_is_valid_inits(annotated, [OUT_B, OUT_A])
    assert output_inits == f"bool {COMPONENT_NAME}_{OUT_A}_IV = false;"


@pytest.mark.parametrize("is_c_ephemeral", [True, False])
def test_single_output_init_always_valid(is_c_ephemeral: bool):
    annotated = basic_annotated(is_c_ephemeral=is_c_ephemeral)

    output_inits = generate_is_valid_inits(annotated, [OUT_C])
    assert output_inits == f"constexpr bool {COMPONENT_NAME}_{OUT_C}_IV = true;"
