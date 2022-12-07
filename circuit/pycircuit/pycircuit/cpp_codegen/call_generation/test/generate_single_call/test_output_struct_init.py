from pycircuit.cpp_codegen.call_generation.generate_output_calldata import (
    generate_output_struct_initializers,
)
from pycircuit.cpp_codegen.test.test_common import (
    COMPONENT_NAME,
    OUT_A,
    OUT_B,
    basic_component,
)


def test_empty_validity_deconstruction():
    component = basic_component()

    empty_struct = generate_output_struct_initializers(component, set())
    assert (
        empty_struct
        == f"""{{

}}"""
    )


# TODO we can make something that optionally pulls a bool out of this expression
# and returns it, OR queries the single output name
def test_single_output_struct():
    component = basic_component()

    assert (
        generate_output_struct_initializers(component, {OUT_A})
        == f"""{{
.{OUT_A} = {COMPONENT_NAME}_{OUT_A},
}}"""
    )
    assert (
        generate_output_struct_initializers(component, {OUT_B})
        == f"""{{
.{OUT_B} = {COMPONENT_NAME}_{OUT_B},
}}"""
    )


def test_both_output_struct():
    component = basic_component()

    assert (
        generate_output_struct_initializers(component, [OUT_A, OUT_B])
        == f"""{{
.{OUT_A} = {COMPONENT_NAME}_{OUT_A},
.{OUT_B} = {COMPONENT_NAME}_{OUT_B},
}}"""
    )
