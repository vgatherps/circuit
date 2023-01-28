from typing import List, Set

from pycircuit.circuit_builder.component import ComponentOutput
from pycircuit.circuit_builder.circuit import CircuitData

IGNORED_SET = {ComponentOutput(parent="external", output_name="time")}


def get_parent_name(output: ComponentOutput) -> str:
    if output.parent == "external":
        return f"{output.parent}_{output.output_name}"
    else:
        return f"{output.parent}"


# TODO these should just be a dataclass?
def get_uncalled_shape(output: ComponentOutput) -> str:
    if output.parent == "external":
        return "square"
    else:
        return "ellipse"


def get_uncalled_outline(output: ComponentOutput) -> str:
    return "dashed"


# TODO generate different input linkages for array and ampping so it's obvious
def generate_dot_for_circuit(circuit: CircuitData) -> str:

    lines = []

    used_outputs = set(
        output
        for component in circuit.components.values()
        for input in component.inputs.values()
        for output in input.outputs()
    )

    # First, add list of triggered

    relevant_externals = [
        external
        for external in circuit.external_inputs.values()
        if external.output() in used_outputs
    ]

    external_node_names = [
        f"{get_parent_name(external.output())}" for external in relevant_externals
    ]

    # todo assert these are all on the same level
    for trigger_name in external_node_names:
        lines.append(f'{trigger_name} [shape=box label="{trigger_name}"]')

    formatted_node_names = " ".join(name + ";" for name in external_node_names)
    rank_line = f"{{rank=same; {formatted_node_names}}}"
    lines.append(rank_line)

    for component in circuit.components.values():

        lines.append(f'{component.name} [label="{component.name}"]')

        for (input_name, input) in component.inputs.items():
            for output in input.outputs():

                if input in component.triggering_inputs():
                    line_style = "solid"
                else:
                    line_style = "dashed"

                parent_node_name = get_parent_name(output)
                own_node_name = component.name

                if output.parent == "external":
                    line_label = input.input_name
                else:
                    line_label = f"{output.output_name} -> {input.input_name}"

                lines.append(
                    f'{parent_node_name} -> {own_node_name} [style={line_style} label="{line_label}"]'
                )

    return "\n".join(lines)
