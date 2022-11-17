from typing import List, Set

from pycircuit.circuit_builder.circuit import Component


def is_ephemeral(component: Component, non_ephemeral_components: Set[str]):
    return (
        component.name not in non_ephemeral_components
        and not component.force_stored
        and component.definition.ephemeral
    )


def find_required_inputs(components: List[Component]) -> Set[str]:
    own_component_names = {component.name for component in components}
    non_ephemeral_components = set()
    for component in components:
        for input in component.inputs.values():
            if input.parent != "external" and input.parent not in own_component_names:
                non_ephemeral_components.add(input.parent)

    return non_ephemeral_components
