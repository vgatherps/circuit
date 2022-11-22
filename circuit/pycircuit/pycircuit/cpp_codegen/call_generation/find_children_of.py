from collections import OrderedDict
from typing import Dict, List, Set

from pycircuit.circuit_builder.circuit import CircuitData, Component, ComponentOutput


# This is not fast, but in practice
# there will only be one iteration of actual work since insertions into the circuit
# already tend to happen in order
def find_all_children_of_from_outputs(
    circuit: CircuitData, used_outputs: Set[ComponentOutput]
) -> List[Component]:
    components = list(circuit.components.values())

    called: Dict[str, Component] = OrderedDict()

    did_work = True
    while (len(called) < len(components)) and did_work:
        did_work = False
        for component in components:
            if component.name in called:
                continue

            all_outputs = {input.output() for input in component.inputs.values()}
            if any(o in used_outputs for o in all_outputs):
                potentially_written = {
                    ComponentOutput(parent=component.name, output=field)
                    for field in component.definition.output.fields
                }
                used_outputs |= potentially_written
                did_work = True
                called[component.name] = component

    return list(called.values())


def find_all_children_of(
    external_set: Set[str], circuit: CircuitData
) -> List[Component]:
    used_outputs = {ComponentOutput(parent="external", output=e) for e in external_set}
    return find_all_children_of_from_outputs(circuit, used_outputs)
