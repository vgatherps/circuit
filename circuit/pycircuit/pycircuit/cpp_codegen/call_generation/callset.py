from typing import Set

from pycircuit.circuit_builder.circuit import Component, ComponentInput, ComponentOutput
from pycircuit.circuit_builder.definition import CallSpec


def find_callset_for(
    component: Component, all_outputs: Set[ComponentOutput]
) -> CallSpec:
    possible_callset = None
    for call_spec in component.definition.callsets:
        callset_matches = True
        for requested in call_spec.written_set:
            the_input = component.inputs[requested]
            if the_input.output() not in all_outputs:
                callset_matches = False
                break

        if callset_matches:
            if possible_callset is not None:
                raise ValueError(
                    f"Component {component.name} had multiple matching callsets: {possible_callset} and {call_spec}"
                )
            possible_callset = call_spec

    if possible_callset is None:
        possible_callset = component.definition.generic_callset

    if possible_callset is None:
        raise ValueError(
            f"Component {component.name} had no matching callset and no generic callset defined"
        )

    return possible_callset


def get_inputs_for_callset(
    callset: CallSpec, component: Component
) -> Set[ComponentInput]:
    return {component.inputs[name] for name in (callset.observes | callset.written_set)}
