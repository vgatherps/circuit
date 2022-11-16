from collections import OrderedDict
from typing import List, Set

from pycircuit.circuit_builder.circuit import Circuit, Component, ComponentOutput


# This is not fast, but in practice
# there will only be one iteration of actual work since insertions into the circuit
# already tend to happen in order
def find_all_children_of(external_set: Set[str], circuit: Circuit) -> List[Component]:
    used_outputs = {ComponentOutput(parent="external", output=e) for e in external_set}

    components = list(circuit.components.values())

    called = OrderedDict()

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
