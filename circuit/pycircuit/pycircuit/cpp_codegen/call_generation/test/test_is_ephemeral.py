from pycircuit.circuit_builder.circuit import ComponentOutput, OutputOptions
from pycircuit.cpp_codegen.call_generation.ephemeral import is_ephemeral
from pycircuit.cpp_codegen.test.test_common import (
    COMPONENT_NAME,
    OUT_A,
    OUT_B,
    basic_component,
)


# Test that output a, which is allowed to be ephemeral, is ephemeral with no callers
def test_is_allowed_ephemeral_ephemeral():
    component = basic_component()

    assert is_ephemeral(component, OUT_A, set())


# Test that output b, which is not allowed to be ephemeral, is not ephemeral even with no callers
def test_is_not_allowed_ephemeral_not_ephemeral():
    component = basic_component()

    assert not is_ephemeral(component, OUT_B, set())


# Test that output a, which is allowed to be ephemeral, is ephemeral with no callers
def test_is_allowed_ephemeral_force_store_not_ephemeral():
    component = basic_component()

    component.output_options[OUT_A] = OutputOptions(force_stored=True)

    assert not is_ephemeral(component, OUT_A, set())


# Test that output a, which is allowed to be ephemeral, is ephemeral with no callers
def test_is_allowed_ephemeral_is_used_not_ephemeral():
    component = basic_component()

    assert not is_ephemeral(
        component,
        OUT_A,
        set([ComponentOutput(parent=COMPONENT_NAME, output_name=OUT_A)]),
    )


# Test that output a, which is allowed to be ephemeral, is ephemeral with no callers
def test_is_allowed_ephemeral_other_is_used_ephemeral():
    component = basic_component()

    assert is_ephemeral(
        component,
        OUT_A,
        set([ComponentOutput(parent=COMPONENT_NAME, output_name=OUT_B)]),
    )
