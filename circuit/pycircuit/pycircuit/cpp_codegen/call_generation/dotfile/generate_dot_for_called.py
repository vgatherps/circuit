from typing import List, Set

from pycircuit.circuit_builder.circuit import ComponentOutput
from pycircuit.cpp_codegen.call_generation.find_children_of import CalledComponent

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


def generate_dot_for_called(
    external_triggered: Set[ComponentOutput], all_called: List[CalledComponent]
) -> str:

    called_outputs = external_triggered | {
        comp.component.output(triggered)
        for comp in all_called
        for triggered in comp.callset.outputs
    }

    all_outputs = {
        output
        for component in all_called
        for input in component.callset.written_set | component.callset.observes
        for output in component.component.inputs[input].outputs()
    }

    uncalled_outputs = all_outputs - called_outputs
    uncalled_parents = {
        output.parent for output in uncalled_outputs if output.parent != "external"
    }

    uncalled_external = {
        output
        for output in uncalled_outputs
        if output.parent == "external"
        if output not in external_triggered and output not in IGNORED_SET
    }

    lines = []

    # First, add list of triggered

    external_node_names = [
        f"{get_parent_name(trigger)}" for trigger in external_triggered
    ]

    # todo assert these are all on the same level
    for trigger_name in external_node_names:
        lines.append(f'{trigger_name} [shape=box label="{trigger_name}"]')

    untriggered_external_node_names = [
        f"{get_parent_name(untriggered)}" for untriggered in uncalled_external
    ]

    # todo assert these are all on the same level
    for trigger_name in untriggered_external_node_names:
        lines.append(f'{trigger_name} [shape=box label="{trigger_name}" style=dashed]')

    external_node_list = " ".join(
        name + ";" for name in external_node_names + untriggered_external_node_names
    )
    rank_line = f"{{rank=same; {external_node_list}}}"
    lines.append(rank_line)

    for component in all_called:
        lines.append(
            f'{component.component.name} [label="{component.component.name}::{component.callset.callback}"]'
        )

    for uncalled_parent in uncalled_parents:
        lines.append(f"{uncalled_parent} [style=dashed]")

    # Generate written (i.e. non-observes) lines
    for component in all_called:
        for input_name in component.callset.written_set | component.callset.observes:
            input = component.component.inputs[input_name]
            for output in input.outputs():

                if output in IGNORED_SET and output not in external_triggered:
                    continue

                if input_name in component.callset.written_set:
                    line_style = "solid"
                else:
                    line_style = "dashed"

                parent_node_name = get_parent_name(output)
                own_node_name = component.component.name

                if output.parent == "external":
                    line_label = input.input_name
                else:
                    line_label = f"{output.output_name} -> {input.input_name}"

                lines.append(
                    f'{parent_node_name} -> {own_node_name} [style={line_style} label="{line_label}"]'
                )

    return "\n".join(lines)
