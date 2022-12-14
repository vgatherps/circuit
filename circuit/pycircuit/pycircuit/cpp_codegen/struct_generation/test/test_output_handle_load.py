import pytest
from pycircuit.cpp_codegen.struct_generation.generate_val_load import (
    generate_check_for_loadable_output,
    generate_check_for_output,
    generate_checks_for_component,
    generate_error_for_ephemeral_component,
    get_component_validity,
)
from pycircuit.cpp_codegen.test.test_common import (
    COMPONENT_CLASS,
    COMPONENT_NAME,
    OUT_A,
    OUT_B,
    OUT_B_CLASS,
    OUT_B_VALID_INDEX,
    OUT_C,
    OUT_C_CLASS,
    basic_annotated,
    basic_component,
)


def test_component_validity():
    annotated = basic_annotated()

    assert (
        get_component_validity(annotated, OUT_B)
        == f"&this->outputs.is_valid[{OUT_B_VALID_INDEX}]"
    )


def test_component_validity_always_valid():
    annotated = basic_annotated()

    assert get_component_validity(annotated, OUT_C) == f"&this->alwaystrue"


@pytest.mark.parametrize("direct", [True, False])
def test_component_output_checks(direct: bool):
    if direct:
        call = generate_check_for_loadable_output
    else:
        call = generate_check_for_output
    annotated = basic_annotated()

    assert (
        call(annotated, OUT_B, annotated.component.definition.output_specs[OUT_B])
        == f"""\
if ("{OUT_B}" == __output__) {{
    if (typeid({COMPONENT_NAME}TypeAlias::{OUT_B_CLASS}) == __typeid__) {{
        const char *output = reinterpret_cast<const char *>(&this->outputs.{COMPONENT_NAME}_{OUT_B});
        const char *valid = reinrerpret_cast<const char *>(&this->outputs.is_valid[{OUT_B_VALID_INDEX}]);

        std::uint32_t value_offset = output - __base__;
        std::uint32_t valid_offset = valid - __base__;

        return RawOutputHandle(value_offset, valid_offset);
    }} else {{
        throw std::runtime_error("Component {COMPONENT_NAME} got wrong type requesting {OUT_B}");
    }}
}}"""
    )


@pytest.mark.parametrize("direct", [True, False])
def test_component_output_checks_always_valid(direct: bool):
    if direct:
        call = generate_check_for_loadable_output
    else:
        call = generate_check_for_output
    annotated = basic_annotated(is_c_ephemeral=False)

    assert (
        call(annotated, OUT_C, annotated.component.definition.output_specs[OUT_C])
        == f"""\
if ("{OUT_C}" == __output__) {{
    if (typeid({COMPONENT_NAME}TypeAlias::{OUT_C_CLASS}) == __typeid__) {{
        const char *output = reinterpret_cast<const char *>(&this->outputs.{COMPONENT_NAME}_{OUT_C});
        const char *valid = reinrerpret_cast<const char *>(&this->alwaystrue);

        std::uint32_t value_offset = output - __base__;
        std::uint32_t valid_offset = valid - __base__;

        return RawOutputHandle(value_offset, valid_offset);
    }} else {{
        throw std::runtime_error("Component {COMPONENT_NAME} got wrong type requesting {OUT_C}");
    }}
}}"""
    )


@pytest.mark.parametrize("direct", [True, False])
def test_component_output_ephemeral_error(direct: bool):
    if direct:
        call = lambda a, b, c: generate_error_for_ephemeral_component(a, b)
    else:
        call = generate_check_for_output

    annotated = basic_annotated()

    assert (
        call(annotated, OUT_A, annotated.component.definition.output_specs[OUT_A])
        == f"""\
if ("{OUT_A}" == __output__) {{
    throw std::runtime_error("Component {COMPONENT_NAME} requesting handle to ephemeral output {OUT_A}");
}}"""
    )


def test_whole_component_check():
    annotated = basic_annotated()

    assert (
        generate_checks_for_component(annotated)
        == f"""\
if ("{COMPONENT_NAME}" == __component__) {{
if ("{OUT_A}" == __output__) {{
    throw std::runtime_error("Component {COMPONENT_NAME} requesting handle to ephemeral output {OUT_A}");
}}

if ("{OUT_B}" == __output__) {{
    if (typeid({COMPONENT_NAME}TypeAlias::{OUT_B_CLASS}) == __typeid__) {{
        const char *output = reinterpret_cast<const char *>(&this->outputs.{COMPONENT_NAME}_{OUT_B});
        const char *valid = reinrerpret_cast<const char *>(&this->outputs.is_valid[{OUT_B_VALID_INDEX}]);

        std::uint32_t value_offset = output - __base__;
        std::uint32_t valid_offset = valid - __base__;

        return RawOutputHandle(value_offset, valid_offset);
    }} else {{
        throw std::runtime_error("Component {COMPONENT_NAME} got wrong type requesting {OUT_B}");
    }}
}}

if ("{OUT_C}" == __output__) {{
    if (typeid({COMPONENT_NAME}TypeAlias::{OUT_C_CLASS}) == __typeid__) {{
        const char *output = reinterpret_cast<const char *>(&this->outputs.{COMPONENT_NAME}_{OUT_C});
        const char *valid = reinrerpret_cast<const char *>(&this->alwaystrue);

        std::uint32_t value_offset = output - __base__;
        std::uint32_t valid_offset = valid - __base__;

        return RawOutputHandle(value_offset, valid_offset);
    }} else {{
        throw std::runtime_error("Component {COMPONENT_NAME} got wrong type requesting {OUT_C}");
    }}
}}

throw std::runtime_error("Could not find outputs for component {COMPONENT_NAME}")
}}"""
    )
