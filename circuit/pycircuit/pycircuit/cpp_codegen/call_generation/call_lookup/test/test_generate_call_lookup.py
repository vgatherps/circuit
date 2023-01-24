import pytest
from pycircuit.circuit_builder.circuit import CallGroup
from pycircuit.cpp_codegen.call_generation.call_lookup.generate_call_lookup import (
    general_load_call_for_struct,
    generate_lookup_of,
)


def test_lookup_of():
    assert (
        generate_lookup_of("test_call", "test_struct", postfix="_void")
        == """\
if ("test_call" == __name__) {
    const std::type_info &the_type = typeid(InputTypes::test_struct);
    if (the_type == __typeid__) {
        return (void *)&test_call_void;
    } else {
        return WrongCallbackType {
            .type=the_type
        };
    }
}"""
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
if ("test_call_a" == __name__) {{
    const std::type_info &the_type = typeid(InputTypes::test_struct);
    if (the_type == __typeid__) {{
        return (void *)&{prefix}test_call_a_void;
    }} else {{
        return WrongCallbackType {{
            .type=the_type
        }};
    }}
}}

if ("test_call_b" == __name__) {{
    const std::type_info &the_type = typeid(InputTypes::test_struct);
    if (the_type == __typeid__) {{
        return (void *)&{prefix}test_call_b_void;
    }} else {{
        return WrongCallbackType {{
            .type=the_type
        }};
    }}
}}"""
    )
