from typing import Set

from pycircuit.circuit_builder.circuit import ComponentInput, ComponentOutput
from pycircuit.circuit_builder.definition import CallSpec
from pycircuit.cpp_codegen.call_generation.call_data import CallData
from pycircuit.cpp_codegen.call_generation.callset import get_inputs_for_callset
from pycircuit.cpp_codegen.call_generation.single_call.generate_output_calldata import (
    get_valid_path,
)
from pycircuit.cpp_codegen.generation_metadata import (
    AnnotatedComponent,
    GenerationMetadata,
)
from pycircuit.cpp_codegen.type_names import get_alias_for, get_type_name_for_input
from pycircuit.circuit_builder.circuit import SingleComponentInput
from pycircuit.circuit_builder.circuit import Component
from pycircuit.circuit_builder.definition import BasicInput

# On one hand, having this largely rely on auto
# make the codegen easier.
#
# On the other, it introduces huge room for error esepcially around reference autoconversion

# TODO move as much of this as possible into the metadata/graph generation phase
# completely decoupling the logic generation from the code generation

INPUT_STRUCT_NAME = "__INPUT__"
INPUT_NAME = "__input__"


def get_parent_name(
    output: ComponentOutput, meta: GenerationMetadata, written_outputs: Set[ComponentOutput]
) -> str:
    if output.parent == "external":
        return f"_externals.{output.output_name}"
    else:
        parent = meta.annotated_components[output.parent]

        output_spec = parent.output_data[output.output_name]
        if output_spec.is_value_ephemeral:
            output_def = parent.component.definition.d_output_specs[output.output_name]
            if output_def.assume_invalid and output.output() not in written_outputs:
                root_name = "nullptr"
            else:
                root_name = f"{parent.component.name}_{output.output_name}_EV__"

        else:
            # TODO post-refactor nest this struct
            root_name = f"_outputs.{output.parent}_{output.output_name}"

        return root_name


def get_valid_path_external(output: ComponentOutput, gen_data: GenerationMetadata):
    if output.parent == "external":
        the_external = gen_data.circuit.external_inputs[output.output_name]
        return f"_externals.is_valid[{the_external.index}]"
    else:
        return get_valid_path(
            gen_data.annotated_components[output.parent], output.output_name
        )


def generate_input_field_for(t_name: str, single_input: SingleComponentInput, name: str, component: Component, gen_data: GenerationMetadata) -> str:
    match component.definition.inputs[single_input.input_name]:
        case BasicInput(always_valid=True):
            return f"const {t_name} &{single_input.input_name}_v = {name};"
        case _:
            return f"""\
bool is_{single_input.input_name}_v = {get_valid_path_external(single_input.output(), gen_data)};
optional_reference<const {t_name}> {single_input.input_name}_v({name}, is_{single_input.input_name}_v);"""

def generate_struct_field_for(t_name: str, input: SingleComponentInput, component: Component) -> str:
    match component.definition.inputs[input.input_name]:
        case BasicInput(always_valid=True):
            return f"const {t_name} &{input.input_name};"
        case _:
            return f"optional_reference<const {t_name}> {input.input_name};"

def generate_single_input_calldata(
    annotated_component: AnnotatedComponent,
    callset: CallSpec,
    gen_data: GenerationMetadata,
    all_written: Set[ComponentOutput],
) -> CallData:

    component = annotated_component.component

    all_inputs = get_inputs_for_callset(callset, component)

    inputs = set(input for input in all_inputs if isinstance(input, SingleComponentInput))

    input_names = [f"{get_parent_name(single_input.output(), gen_data, all_written)}" for single_input in inputs]

    all_type_names = [get_type_name_for_input(component, single_input.input_name) for single_input in inputs]

    all_values = [
        generate_input_field_for(t_name, single_input, name, component, gen_data)
        for (t_name, single_input, name) in zip(all_type_names, inputs, input_names)
    ]

    values = "\n".join(all_values)

    # Sorting all_values will sort by input name
    # Those manually specifying a struct should be sorted as well to ensure initialization
    # order is correct
    input_struct_initializers_list = sorted(
        f".{c.input_name} = {c.input_name}_v," for c in inputs
    )

    input_struct_initializers = "\n".join(input_struct_initializers_list)

    if callset.input_struct_path is None:
        input_struct_fields_list = sorted(
            generate_struct_field_for(t_name, single_input, component)
            for (t_name, single_input) in zip(all_type_names, inputs)
        )
        input_struct_fields = "\n".join(input_struct_fields_list)
        input_struct = f"struct {INPUT_STRUCT_NAME} {{{input_struct_fields}}};"
        input_struct_name = INPUT_STRUCT_NAME
    else:
        class_name = get_alias_for(annotated_component.component)
        input_struct = ""
        input_struct_name = f"{class_name}::{callset.input_struct_path}"

    inputs_prefix = f"""
{input_struct}

{values}

{input_struct_name} {INPUT_NAME} = {{
    {input_struct_initializers}
}};"""

    return CallData(local_prefix=inputs_prefix, call_params=[INPUT_NAME])
