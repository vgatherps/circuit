from typing import Dict, Set

from pycircuit.circuit_builder.circuit import Component, ComponentInput


def find_writeset_for(
    component: Component, all_components: Dict[str, Component]
) -> Set[ComponentInput]:

    possible_callset = None
    for call_spec in component.definition.callsets:
        callset_matches = True
        for requested in call_spec.written_set:
            the_input = component.inputs[requested]

            if the_input.parent not in all_components:
                callset_matches = False
                break

        if callset_matches:
            if possible_callset is not None:
                raise ValueError(
                    f"Component {component.name} had multiple matching callsets: {possible_callset} and {call_spec}"
                )
            possible_callset = call_spec

    if possible_callset is None:
        possible_callset = component.definition.generic_callback

    if possible_callset is None:
        raise ValueError(
            f"Component {component.name} had no matching callset and no generic callset defined"
        )

    inputs = {
        component.inputs[name]
        for name in (possible_callset.observes | possible_callset.written_set)
    }

    return inputs
