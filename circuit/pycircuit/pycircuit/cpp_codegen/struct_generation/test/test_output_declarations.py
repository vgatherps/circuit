from pycircuit.cpp_codegen.struct_generation.generate_struct import (
    generate_output_declarations_for_component,
)
from pycircuit.cpp_codegen.test.test_common import (
    COMPONENT_NAME,
    OUT_B,
    OUT_B_CLASS,
    basic_component,
)


def test_output_declaration():
    component = basic_component()

    assert (
        generate_output_declarations_for_component(component, OUT_B)
        == f"{COMPONENT_NAME}TypeAlias::{OUT_B_CLASS} {COMPONENT_NAME}_{OUT_B};"
    )
