from typing import Set

from pycircuit.circuit_builder.circuit import Circuit, Component, ComponentInput
from pycircuit.cpp_codegen.call_generation.call_metadata import CallMetaData
from pycircuit.cpp_codegen.call_generation.ephemeral import is_ephemeral
from pycircuit.cpp_codegen.type_data import (
    get_alias_for,
    get_sorted_inputs,
    get_type_name_for_input,
)

# On one hand, having this largely rely on auto
# make the codegen easier.
#
# On the other, it introduces huge room for error esepcially around reference autoconversion

OUTPUT_NAME = "__output__"


def get_parent_name(
    c: ComponentInput, circuit: Circuit, non_ephemeral_components: Set[str]
) -> str:
    if c.parent == "external":
        return f"externals.{c.output_name}"
    else:
        parent = circuit.components[c.parent]
        if is_ephemeral(parent, non_ephemeral_components):
            root_name = f"{parent.name}_EV"
        else:
            root_name = f"outputs.{c.parent}"

        return f"{root_name}.{c.output_name}"


def generate_single_call(
    component: Component, circuit: Circuit, non_ephemeral_components: Set[str]
) -> str:
    # TODO static vs stateful
    # Maybe another todo impermanent (only exist within a single graph) vs stored?
    # TODO How to deal with generics? Can/should just do in order

    class_name = get_alias_for(component)
    output_name = f"outputs.{component.name}"

    if is_ephemeral(component, non_ephemeral_components):
        ephemeral_line = f"{class_name}::Output {component.name}_EV;"
        output_line = f"{class_name}::Output& {OUTPUT_NAME} = {component.name}_EV;"
    else:
        ephemeral_line = ""
        output_line = f"{class_name}::Output& {OUTPUT_NAME} = {output_name};"

    sorted_by_idx = get_sorted_inputs(component)

    assert list(i.input_idx for i in sorted_by_idx) == list(
        range(0, len(sorted_by_idx))
    )

    input_names = [
        f"{get_parent_name(c, circuit, non_ephemeral_components)}"
        for c in sorted_by_idx
    ]

    all_type_names = [get_type_name_for_input(component, c) for c in sorted_by_idx]

    all_values = [
        f"const {t_name} &{c.input_name}_v = {name};"
        for (t_name, c, name) in zip(all_type_names, sorted_by_idx, input_names)
    ]

    input_list = ",".join(f"{c.input_name}_v" for c in sorted_by_idx)

    if component.definition.static_call:
        call_name = f"{class_name}::call({input_list}, {OUTPUT_NAME});"
    else:
        object_name = f"objects.{component.name}"
        call_name = f"{object_name}.call({input_list}, {OUTPUT_NAME});"

    values = "\n".join(all_values)
    return f"""
    {ephemeral_line}
    {{
        {values}
        {output_line}
        {call_name}
    }}
    """
