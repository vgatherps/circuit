import pytest
from pycircuit.circuit_builder.circuit import CallGroup
from pycircuit.cpp_codegen.call_generation.call_lookup.generate_call_lookup import (
    general_load_call_for_struct,
    generate_load_call_signature,
    generate_lookup_of,
)


def test_lookup_of():
    assert (
        generate_lookup_of("test_call", "InputTypes::test_struct", postfix="_void")
        == """\
if (
    "test_call" == __name__ &&
    typeid(InputTypes::test_struct) == __typeid__
) {
    return (void *)&test_call_void;
}"""
    )


@pytest.mark.parametrize("prefix", ["", "test_prefix::"])
@pytest.mark.parametrize("postfix", ["", ";"])
def test_signature(prefix: str, postfix: str):
    assert generate_load_call_signature(
        "test_struct", prefix=prefix, postfix=postfix
    ) == (
        f"{prefix}TriggerCall<{prefix}InputTypes::test_struct> {prefix}do_lookup_trigger"
        f"(const std::string &__name__, InputTypes::test_struct **){postfix}"
    )


@pytest.mark.parametrize("prefix", ["", "test_prefix::"])
def test_single_lookup_call(prefix: str):
    groups = {
        "test_call_b": CallGroup(struct="test_struct", external_field_mapping={}),
        "test_call_a": CallGroup(struct="test_struct", external_field_mapping={}),
    }

    assert (
        general_load_call_for_struct(groups, "test_struct", prefix=prefix)
        == f"""\
if (
    "test_call_a" == __name__ &&
    typeid(test_struct) == __typeid__
) {{
    return (void *)&{prefix}test_call_a_void;
}}

if (
    "test_call_b" == __name__ &&
    typeid(test_struct) == __typeid__
) {{
    return (void *)&{prefix}test_call_b_void;
}}"""
    )
