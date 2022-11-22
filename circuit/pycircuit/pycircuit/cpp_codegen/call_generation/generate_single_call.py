from typing import Set

from pycircuit.circuit_builder.circuit import CircuitBuilder, Component, ComponentInput
from pycircuit.cpp_codegen.generation_metadata import (
    AnnotatedComponent,
    GenerationMetadata,
)
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


def get_parent_name(c: ComponentInput, meta: GenerationMetadata) -> str:
    if c.parent == "external":
        return f"externals.{c.output_name}"
    else:
        parent = meta.annotated_components[c.parent]
        if meta.annotated_components[c.parent].is_ephemeral:
            root_name = f"{parent.component.name}_EV"
        else:
            root_name = f"outputs.{c.parent}"

        return f"{root_name}.{c.output_name}"


def get_valid_path(component: AnnotatedComponent):
    if component.ephemeral_data is None:
        return f"{component.component.name}_IV"
    else:
        return f"outputs.is_valid[{component.ephemeral_data.validity_index}]"


def get_valid_path_external(input: ComponentInput, gen_data: GenerationMetadata):
    if input.parent == "external":
        the_external = gen_data.circuit.external_inputs[input.output_name]
        return f"externals.is_valid[{the_external.index}]"
    else:
        return get_valid_path(gen_data.annotated_components[input.parent])


def generate_single_call(
    annotated_component: AnnotatedComponent, gen_data: GenerationMetadata
) -> str:
    # TODO How to deal with generics? Can/should just do in order

    component = annotated_component.component

    class_name = get_alias_for(component)
    output_name = f"outputs.{component.name}"

    own_valid_path = get_valid_path(annotated_component)
    if annotated_component.ephemeral_data is None:
        ephemeral_line = f"{class_name}::Output {component.name}_EV;"
        valid_line = f"bool {own_valid_path} = false;"
        output_line = f"{class_name}::Output& {OUTPUT_NAME} = {component.name}_EV;"
    else:
        ephemeral_line = ""
        valid_line = ""
        output_line = f"{class_name}::Output& {OUTPUT_NAME} = {output_name};"

    sorted_by_idx = get_sorted_inputs(component)

    assert list(i.input_idx for i in sorted_by_idx) == list(
        range(0, len(sorted_by_idx))
    )

    input_names = [f"{get_parent_name(c, gen_data)}" for c in sorted_by_idx]

    all_type_names = [get_type_name_for_input(component, c) for c in sorted_by_idx]

    all_values = [
        f"""
            bool is_{c.input_name}_v = {get_valid_path_external(c, gen_data)};
            optional_reference<const {t_name}> {c.input_name}_v({name}, is_{c.input_name}_v);
        """
        for (t_name, c, name) in zip(all_type_names, sorted_by_idx, input_names)
    ]

    input_list = ",".join(f"{c.input_name}_v" for c in sorted_by_idx)

    call_name = f"{annotated_component.call_path}({input_list}, {OUTPUT_NAME})"

    values = "\n".join(all_values)
    return f"""
    {ephemeral_line}
    {valid_line}
    {{
        {values}
        {output_line}
        {own_valid_path} = {call_name}
    }}
    """
