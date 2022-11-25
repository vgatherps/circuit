from pycircuit.cpp_codegen.call_generation.generate_single_call import (
    VALID_DATA_NAME,
    deconstruct_valid_output,
)
from pycircuit.cpp_codegen.test.test_common import (
    COMPONENT_NAME,
    OUT_A,
    OUT_B,
    OUT_B_VALID_INDEX,
    basic_annotated,
)


def test_empty_validity_deconstruction():
    annotated = basic_annotated()

    deconstructed_valid = deconstruct_valid_output(annotated, set())
    assert deconstructed_valid == ""


# TODO we can make something that optionally pulls a bool out of this expression
# and returns it, OR queries the single output name
def test_single_validity_deconstruction_ephemeral():
    annotated = basic_annotated()

    deconstructed_valid = deconstruct_valid_output(annotated, {OUT_A})
    assert deconstructed_valid == f"{COMPONENT_NAME}_{OUT_A}_IV = {VALID_DATA_NAME};"


def test_single_validity_deconstruction_nonephemeral():
    annotated = basic_annotated()

    deconstructed_valid = deconstruct_valid_output(annotated, {OUT_B})
    assert (
        deconstructed_valid
        == f"outputs.is_valid[{OUT_B_VALID_INDEX}] = {VALID_DATA_NAME};"
    )


def test_both_validity_deconstruction():
    annotated = basic_annotated()

    deconstructed_valid = deconstruct_valid_output(annotated, [OUT_B, OUT_A])
    assert (
        deconstructed_valid
        == f"""outputs.is_valid[{OUT_B_VALID_INDEX}] = {VALID_DATA_NAME}.{OUT_B};
{COMPONENT_NAME}_{OUT_A}_IV = {VALID_DATA_NAME}.{OUT_A};"""
    )
