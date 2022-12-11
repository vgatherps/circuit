from pycircuit.circuit_builder.circuit import CallStruct
from pycircuit.cpp_codegen.struct_generation.generate_struct import (
    generate_single_input_struct,
)
from pycircuit.cpp_codegen.test.test_common import (
    COMPONENT_NAME,
    OUT_B,
    OUT_B_CLASS,
    basic_component,
)


def test_call_struct():
    component = basic_component()

    assert (
        generate_single_input_struct(
            "test", CallStruct.from_input_dict({"a": "a_type", "b": "b_type"})
        )
        == f"""struct test {{
Optionally<a_type>::Optional a;
Optionally<b_type>::Optional b;
}};"""
    )
