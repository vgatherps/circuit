import pytest
from pycircuit.cpp_codegen.call_generation.callset import find_callset_for
from pycircuit.cpp_codegen.test.test_common import (
    A_INPUT,
    AB_CALLSET,
    B_INPUT,
    BC_CALLSET,
    C_INPUT,
    COMPONENT_NAME,
    GENERIC_CALLSET,
    OUT_A,
    OUT_B,
    basic_component,
    basic_definition,
)


def test_find_ab_callset_from_a():
    component = basic_component()

    ab_callset = find_callset_for(component, set([A_INPUT.output(), B_INPUT.output()]))

    assert ab_callset == AB_CALLSET


def test_find_bc_callset_from_a():
    component = basic_component()

    bc_callset = find_callset_for(component, set([C_INPUT.output(), B_INPUT.output()]))

    assert bc_callset == BC_CALLSET


@pytest.mark.parametrize("single", [A_INPUT, B_INPUT, C_INPUT])
def test_single_finds_generic(single):
    component = basic_component()
    generic = find_callset_for(component, set([single.output()]))
    assert generic == GENERIC_CALLSET


@pytest.mark.parametrize("single", [A_INPUT, B_INPUT, C_INPUT])
def test_single_explodes_no_generic(single):
    component = basic_component()
    component.definition = basic_definition(generic_callset=None)

    with pytest.raises(
        ValueError,
        match=f"Component {COMPONENT_NAME} had no matching callset and no generic callset defined",
    ):
        find_callset_for(component, set([single.output()]))


def test_callset_many_match():
    component = basic_component()

    with pytest.raises(
        ValueError,
        match=f"Component {COMPONENT_NAME} had multiple matching callsets",
    ):
        find_callset_for(
            component, set([A_INPUT.output(), B_INPUT.output(), C_INPUT.output()])
        )
