from typing import Optional, Set

from pycircuit.circuit_builder.circuit import Component, ComponentInput, ComponentOutput
from pycircuit.circuit_builder.definition import CallSpec


def find_all_callsets(
    component: Component, all_outputs: Set[ComponentOutput]
) -> Set[CallSpec]:
    found_callsets = set()
    for call_spec in component.definition.callsets:
        callset_matches = True
        for requested in call_spec.written_set:
            the_input = component.inputs[requested]
            if the_input.output() not in all_outputs:
                callset_matches = False
                break
        if callset_matches:
            found_callsets.add(call_spec)

    return found_callsets


def disambiguate_callsets(name: str, callsets: Set[CallSpec]) -> Optional[CallSpec]:

    if len(callsets) > 1:

        all_written = frozenset(
            call_written for callset in callsets for call_written in callset.written_set
        )

        matching = set(
            callset for callset in callsets if callset.written_set == all_written
        )

        if len(matching) == 0:
            raise ValueError(
                f"Component {name} had multiple matching callsets and no superset: {list(callsets)}"
            )

        if len(matching) > 1:
            # We allow disambiguation if a single callset's written set is a superset of the others
            # First, construct the set of all callests and select all callsets that match it
            raise ValueError(
                f"Component {name} had multiple matching callsets and multiple supersets: {list(matching)}"
            )

        assert len(matching) == 1

        callsets = matching

    if len(callsets) == 0:
        return None

    if len(callsets) == 1:
        return list(callsets)[0]


def find_callset_for(
    component: Component, all_outputs: Set[ComponentOutput]
) -> CallSpec:
    possible_callset = None

    all_callsets = find_all_callsets(component, all_outputs)

    possible_callset = disambiguate_callsets(component.name, all_callsets)

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
