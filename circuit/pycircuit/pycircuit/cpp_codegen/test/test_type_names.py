from pycircuit.cpp_codegen.test.test_common import (
    COMPONENT_NAME,
    OUT_A,
    OUT_A_CLASS,
    OUT_B,
    OUT_B_CLASS,
    basic_component,
)
from pycircuit.cpp_codegen.type_names import (
    generate_output_type_alias,
    get_alias_for,
    get_type_name_for_input,
    get_type_name_for_array_input
)
import pytest


def test_get_alias():
    component = basic_component()

    assert get_alias_for(component) == f"{COMPONENT_NAME}TypeAlias"


def test_get_type_name_for_input():
    component = basic_component()

    assert get_type_name_for_input(component, "a") == f"{COMPONENT_NAME}_a_T"
    assert get_type_name_for_input(component, "b") == f"{COMPONENT_NAME}_b_T"


@pytest.mark.parametrize("idx", [0, 1])
def test_get_type_name_for_array_input(idx: int):
    component = basic_component()

    assert get_type_name_for_array_input(component, idx, "a") == f"{COMPONENT_NAME}_a_{idx}_T"
    assert get_type_name_for_array_input(component, idx, "b") == f"{COMPONENT_NAME}_b_{idx}_T"


def test_output_type_alias():
    component = basic_component()

    assert (
        generate_output_type_alias(component, OUT_A)
        == f"using {COMPONENT_NAME}_{OUT_A}_O_T = {COMPONENT_NAME}TypeAlias::{OUT_A_CLASS};"
    )
    assert (
        generate_output_type_alias(component, OUT_B)
        == f"using {COMPONENT_NAME}_{OUT_B}_O_T = {COMPONENT_NAME}TypeAlias::{OUT_B_CLASS};"
    )
