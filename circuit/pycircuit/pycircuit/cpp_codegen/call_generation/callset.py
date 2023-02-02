from typing import List, Optional, Set

from pycircuit.circuit_builder.component import (
    Component,
    ComponentInput,
    ComponentOutput,
)
from pycircuit.circuit_builder.definition import CallSpec
from pycircuit.circuit_builder.definition import CallsetGroup


def find_all_callsets(
    component: Component, all_outputs: Set[ComponentOutput]
) -> Set[CallSpec]:

    found_callsets = set()
    for call_spec in component.definition.callsets:
        for requested in call_spec.written_set:
            the_input = component.inputs[requested]

            # should this be (not any) or (not all)
            # it's not clear how to disambiguate a batch update.
            # I think I should change this to *only* match entirely correct batches?
            # So that we we can get a proper disambiguation method here.
            if not any(i_output in all_outputs for i_output in the_input.outputs()):
                break
        else:
            found_callsets.add(call_spec)

    return found_callsets


def disambiguate_callsets(
    name: str, groups: Set[CallsetGroup], callsets: Set[CallSpec]
) -> Optional[List[CallSpec]]:

    if len(callsets) > 1:

        name_to_set = {}
        for callset in callsets:
            if callset.name is None:
                raise ValueError(
                    f"Component {name} had multiple matching callsets "
                    f"and some had no name for disambiguation {list(callsets)}"
                )
            name_to_set[callset.name] = callset

        names = frozenset(name_to_set.keys())

        for group in groups:
            if group.names() == names:
                name_to_idx = {name: idx for (idx, name) in enumerate(group.callsets)}

                sorted_by_order = sorted(names, key=lambda n: name_to_idx[n])

                return [name_to_set[name] for name in sorted_by_order]

        # We couldn't find a matching callset group
        raise ValueError(
            f"Component {name} had multiple matching callsets "
            f"and no matching callset group: {names}"
        )

    elif len(callsets) == 0:
        return None
    else:
        assert len(callsets) == 1
        return list(callsets)


def find_callset_for(
    component: Component, all_outputs: Set[ComponentOutput]
) -> List[CallSpec]:

    possible_callset = None

    all_callsets = find_all_callsets(component, all_outputs)

    possible_callset = disambiguate_callsets(
        component.name, set(component.definition.callset_groups), all_callsets
    )

    match (possible_callset, component.definition.generic_callset):
        case (None, None):
            raise ValueError(
                f"Component {component.name} had no matching callset and no generic callset defined"
            )

        case (None, CallSpec() as c):
            return [c]

        case ([*cs], _):
            return cs

    raise ValueError("Bad types")


def get_inputs_for_callset(
    callset: CallSpec, component: Component
) -> Set[ComponentInput]:
    all_inputs = callset.observes | callset.written_set
    return {component.inputs[name] for name in all_inputs}
