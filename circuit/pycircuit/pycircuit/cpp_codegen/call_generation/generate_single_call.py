from typing import Dict, List, Set

from pycircuit.circuit_builder.circuit import CircuitBuilder, Component, ComponentInput
from pycircuit.circuit_builder.definition import CallSpec
from pycircuit.cpp_codegen.generation_metadata import (
    AnnotatedComponent,
    GenerationMetadata,
)
from pycircuit.cpp_codegen.type_data import get_alias_for, get_type_name_for_input

# On one hand, having this largely rely on auto
# make the codegen easier.
#
# On the other, it introduces huge room for error esepcially around reference autoconversion

OUTPUT_NAME = "__output__"
INPUT_STRUCT_NAME = "__INPUT__"
INPUT_NAME = "__input__"


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


def find_writeset_for(
    component: Component, all_components: Dict[str, Component]
) -> Set[ComponentInput]:

    possible_callset = None
    for call_spec in component.definition.callsets:
        callset_matches = True
        for requested in call_spec.written_set:
            the_input = component.inputs[requested]

            if the_input.parent not in all_components:
                callset_matches = False
                break

        if callset_matches:
            if possible_callset is not None:
                raise ValueError(
                    f"Component {component.name} had multiple matching callsets: {possible_callset} and {call_spec}"
                )
            possible_callset = call_spec

    if possible_callset is None:
        if component.definition.generic_callback is not None:
            inputs = set(component.inputs.values())
        else:
            raise ValueError(
                f"Component {component.name} had no matching callset and no generic callset defined"
            )
    else:
        inputs = {
            component.inputs[name]
            for name in (possible_callset.observes | possible_callset.written_set)
        }

    return inputs


def generate_single_call(
    annotated_component: AnnotatedComponent,
    gen_data: GenerationMetadata,
    all_children: List[Component],
    postfix_args: List[str] = [],
) -> str:
    # TODO How to deal with generics? Can/should just do in order

    named_children = {child.name: child for child in all_children}

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

    inputs = list(find_writeset_for(component, named_children))

    input_names = [f"{get_parent_name(c, gen_data)}" for c in inputs]

    all_type_names = [get_type_name_for_input(component, c) for c in inputs]

    all_values = [
        f"""
            bool is_{c.input_name}_v = {get_valid_path_external(c, gen_data)};
            optional_reference<const {t_name}> {c.input_name}_v({name}, is_{c.input_name}_v);
        """
        for (t_name, c, name) in zip(all_type_names, inputs, input_names)
    ]

    input_struct_fields = "\n".join(
        f"optional_reference<const {t_name}> {c.input_name};"
        for (t_name, c) in zip(all_type_names, inputs)
    )

    input_struct_initializers = "\n".join(
        f".{c.input_name} = {c.input_name}_v," for c in inputs
    )

    input_list = ",".join([INPUT_NAME] + postfix_args + [OUTPUT_NAME])

    call_name = f"{annotated_component.call_path}({input_list})"

    values = "\n".join(all_values)
    return f"""
    {ephemeral_line}
    {valid_line}
    {{

        struct {INPUT_STRUCT_NAME} {{
            {input_struct_fields}
        }};

        {values}

        {INPUT_STRUCT_NAME} {INPUT_NAME} = {{
            {input_struct_initializers}
        }};

        {output_line}
        {own_valid_path} = {call_name}
    }}
    """
