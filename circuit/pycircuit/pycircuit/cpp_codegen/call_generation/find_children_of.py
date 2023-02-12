from collections import OrderedDict
from dataclasses import dataclass
from typing import Dict, List, Set

from pycircuit.circuit_builder.circuit import CircuitData
from pycircuit.circuit_builder.component import Component, ComponentOutput
from pycircuit.circuit_builder.definition import CallSpec
from pycircuit.cpp_codegen.call_generation.callset import find_callset_for

# TODO start testing these


@dataclass
class CalledComponent:
    callset: CallSpec
    component: Component


# This is not fast, but in practice
# there will only be one iteration of actual work since insertions into the circuit
# already tend to happen in order
def topologically_sort(
    circuit: CircuitData, used_outputs: Set[ComponentOutput]
) -> List[Component]:
    used_outputs = set(used_outputs)
    components = list(circuit.components.values())

    conservatively_called: Dict[str, Component] = OrderedDict()

    # 1. do a lazy, conservative, topological sort

    rounds = 0
    did_work = True
    while (len(conservatively_called) < len(components)) and did_work:
        rounds += 1
        did_work = False
        for component in components:
            if component.name in conservatively_called:
                continue

            if any(
                i_output in used_outputs
                for i in component.triggering_inputs()
                for i_output in i.outputs()
            ):
                potentially_written = {
                    ComponentOutput(parent=component.name, output_name=field)
                    for field in component.definition.outputs()
                }
                used_outputs |= potentially_written
                did_work = True
                conservatively_called[component.name] = component

    return list(conservatively_called.values())


# TODO as an optimization, could drop ephemeral components
# which have no outputs?
# Most likely it's better to warn, as this could just sort of
# "auto-delete" down a huge tree if there was an error?
# Alternatively, they can *only* exist as a side effect,
# So such components should be removed anyways unless specifically marked
# with warnings generated as such


def find_all_children_of_from_outputs(
    circuit: CircuitData, used_outputs: Set[ComponentOutput]
) -> List[CalledComponent]:

    sorted = topologically_sort(circuit, used_outputs)

    # With a topologically sorted set of inputs
    # iterate through them and discover what writesets actually propagate

    called = []
    seen_outputs = set(used_outputs)
    for component in sorted:
        # Skip calling components where *nothing* is triggered
        # TODO is this correct?
        if not any(
            i_output in seen_outputs
            for input in component.triggering_inputs()
            for i_output in input.outputs()
        ):
            continue

        callsets = find_callset_for(component, seen_outputs)

        for callset in callsets:
            if callset.skippable:
                continue

            writes = callset.outputs
            new_outs = {
                ComponentOutput(parent=component.name, output_name=field)
                for field in writes
            }

            seen_outputs |= new_outs

            called.append(CalledComponent(callset=callset, component=component))

    return called


def find_all_children_of(
    external_set: Set[str], circuit: CircuitData
) -> List[CalledComponent]:
    used_outputs = {
        ComponentOutput(parent="external", output_name=e) for e in external_set
    }
    return find_all_children_of_from_outputs(circuit, used_outputs)
