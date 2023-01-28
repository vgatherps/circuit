from pycircuit.circuit_builder.component import ComponentOutput
from pycircuit.test_generator.test_action import EqLit, CIRCUIT_NAME


STRUCT_NAME = "struct"

COMPONENT_A = "comp_a"
OUTPUT_A = "output_a"

COMPONENT_B = "comp_b"
OUTPUT_B = "output_b"


def test_eqlit_gen():
    eq_lit = EqLit(ComponentOutput(COMPONENT_A, OUTPUT_A), "1234", "int")

    assert (
        eq_lit.generate_lines()
        == f"""\
{{
    OutputHandle<int> __handle__ = _the_circuit_.load_component_output<int>(
        "comp_a",
        "output_a"
    );

    optional_reference<const int> __handle_ref__ = _the_circuit_.load_from_handle(__handle__);

    EXPECT_TRUE(__handle_ref__.valid()) << "Could not load output output_a of component comp_a";
    EXPECT_EQ((1234), *__handle_ref__)  << "output output_a of component comp_a != 1234";
}}"""
    )
