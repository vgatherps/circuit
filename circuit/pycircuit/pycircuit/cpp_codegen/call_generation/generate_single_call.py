from typing import Set

from pycircuit.circuit_builder.circuit import Component, ComponentInput
from pycircuit.cpp_codegen.call_generation.call_metadata import CallMetaData
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


def get_parent_name(c: ComponentInput) -> str:
    if c.parent == "external":
        return f"externals.{c.output_name}"
    else:
        return f"outputs.{c.parent}.{c.output_name}"


def generate_single_call(component: Component) -> str:
    # TODO static vs stateful
    # Maybe another todo impermanent (only exist within a single graph) vs stored?
    # TODO How to deal with generics? Can/should just do in order

    sorted_by_idx = get_sorted_inputs(component)

    assert list(i.input_idx for i in sorted_by_idx) == list(
        range(0, len(sorted_by_idx))
    )

    input_names = [f"{get_parent_name(c)}" for c in sorted_by_idx]

    all_type_names = [get_type_name_for_input(component, c) for c in sorted_by_idx]

    all_values = [
        f"const {t_name} &{c.input_name}_v = {name};"
        for (t_name, c, name) in zip(all_type_names, sorted_by_idx, input_names)
    ]

    input_list = ",".join(f"{c.input_name}_v" for c in sorted_by_idx)
    output_name = f"outputs.{component.name}"

    class_name = get_alias_for(component)
    if component.definition.static_call:
        call_name = f"{class_name}::call({input_list}, {OUTPUT_NAME});"
    else:
        object_name = f"objects.{component.name}"
        call_name = f"{object_name}.call({input_list}, {output_name});"

    values = "\n".join(all_values)
    return f"""
    {{
        {values}
        {class_name}::Output& __output__ = {output_name};
        {call_name}
    }}
    """
