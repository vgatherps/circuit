import pytest
from pycircuit.circuit_builder.circuit import CallGroup
from pycircuit.cpp_codegen.call_generation.call_lookup.generate_call_lookup import (
    general_all_load_call_bodies,
    general_load_call,
    generate_all_load_call_signatures,
    generate_load_call_signature,
    generate_lookup_of,
)


def test_lookup_of():
    assert (
        generate_lookup_of("test_call")
        == f"""if ("test_call" == __name__) {{
return &test_call;
}}"""
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
        general_load_call(groups, "test_struct", prefix=prefix)
        == f"""{prefix}TriggerCall<{prefix}InputTypes::test_struct> {prefix}do_lookup_trigger(const std::string &__name__, InputTypes::test_struct **) {{

if ("test_call_a" == __name__) {{
return &{prefix}test_call_a;
}}

if ("test_call_b" == __name__) {{
return &{prefix}test_call_b;
}}

throw std::runtime_error(std::string("No calls matched the given name ") + __name__);}}"""
    )


@pytest.mark.parametrize("prefix", ["", "test_prefix::"])
@pytest.mark.parametrize("postfix", ["", ";"])
def test_all_signatures(prefix: str, postfix: str):
    groups = {
        "test_call_b": CallGroup(struct="test_struct", external_field_mapping={}),
        "test_call_a": CallGroup(struct="test_struct", external_field_mapping={}),
        "test_call_c": CallGroup(struct="test_struct_2", external_field_mapping={}),
    }
    assert (
        generate_all_load_call_signatures(groups, prefix=prefix, postfix=postfix)
        == f"""{prefix}TriggerCall<{prefix}InputTypes::test_struct> {prefix}do_lookup_trigger(const std::string &__name__, InputTypes::test_struct **){postfix}

{prefix}TriggerCall<{prefix}InputTypes::test_struct_2> {prefix}do_lookup_trigger(const std::string &__name__, InputTypes::test_struct_2 **){postfix}"""
    )


@pytest.mark.parametrize("prefix", ["", "test_prefix::"])
def test_whole_lookup_calls(prefix: str):
    groups = {
        "test_call_b": CallGroup(struct="test_struct", external_field_mapping={}),
        "test_call_a": CallGroup(struct="test_struct", external_field_mapping={}),
        "test_call_c": CallGroup(struct="test_struct_2", external_field_mapping={}),
    }

    assert (
        general_all_load_call_bodies(groups, prefix=prefix)
        == f"""{prefix}TriggerCall<{prefix}InputTypes::test_struct> {prefix}do_lookup_trigger(const std::string &__name__, InputTypes::test_struct **) {{

if ("test_call_a" == __name__) {{
return &{prefix}test_call_a;
}}

if ("test_call_b" == __name__) {{
return &{prefix}test_call_b;
}}

throw std::runtime_error(std::string("No calls matched the given name ") + __name__);}}

{prefix}TriggerCall<{prefix}InputTypes::test_struct_2> {prefix}do_lookup_trigger(const std::string &__name__, InputTypes::test_struct_2 **) {{

if ("test_call_c" == __name__) {{
return &{prefix}test_call_c;
}}

throw std::runtime_error(std::string("No calls matched the given name ") + __name__);}}"""
    )
