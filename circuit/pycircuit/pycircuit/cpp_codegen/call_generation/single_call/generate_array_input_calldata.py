from typing import Optional, Set, List

from pycircuit.circuit_builder.component import ComponentOutput
from pycircuit.circuit_builder.definition import CallSpec
from pycircuit.cpp_codegen.call_generation.callset import get_inputs_for_callset
from pycircuit.cpp_codegen.generation_metadata import (
    AnnotatedComponent,
    GenerationMetadata,
)
from pycircuit.cpp_codegen.type_names import get_alias_for
from pycircuit.circuit_builder.circuit import SingleComponentInput
from pycircuit.circuit_builder.circuit import Component
from pycircuit.circuit_builder.definition import BasicInput

from pycircuit.cpp_codegen.call_generation.single_call.generate_single_input_calldata import (
    get_parent_name,
)
from pycircuit.circuit_builder.component import ArrayComponentInput
from pycircuit.cpp_codegen.call_generation.single_call.generate_single_input_calldata import (
    get_valid_path_external,
)
from pycircuit.circuit_builder.definition import ArrayInput
from pycircuit.cpp_codegen.type_names import get_type_name_for_array_input

# On one hand, having this largely rely on auto
# make the codegen easier.
#
# On the other, it introduces huge room for error esepcially around reference autoconversion

# TODO move as much of this as possible into the metadata/graph generation phase
# completely decoupling the logic generation from the code generation

ARRAY_INPUT_STRUCT_NAME = "__ARRAY_INPUT__"
ARRAY_INPUT_NAME = "__array_input__"


def generate_array_input_field_for(
    t_name: str,
    single_input: SingleComponentInput,
    name: str,
    idx: int,
    component: Component,
    gen_data: GenerationMetadata,
) -> str:
    match component.definition.inputs[single_input.input_name]:
        case ArrayInput(always_valid=True):
            return f"""\
static_assert(
    {get_valid_path_external(single_input.output(), gen_data)},
    "If this fails internal codegen error - always valid input always constexpr true"
);
array_reference<const {t_name}> {single_input.input_name}_v({name}, {idx});"""
        case _:
            return f"""\
bool is_{single_input.input_name}_v = {get_valid_path_external(single_input.output(), gen_data)};
array_optional<const {t_name}> {single_input.input_name}_v({name}, is_{single_input.input_name}_v, {idx});"""


def generate_array_struct_field_for(
    t_name: str, input: SingleComponentInput, component: Component
) -> str:
    match component.definition.inputs[input.input_name]:
        case ArrayInput(always_valid=True):
            return f"array_reference<const {t_name}> {input.input_name};"
        case _:
            return f"array_optional<const {t_name}> {input.input_name};"


def generate_array_input_prefix(
    annotated_component: AnnotatedComponent,
    callset: CallSpec,
    gen_data: GenerationMetadata,
    all_written: Set[ComponentOutput],
    idx: int,
) -> Optional[str]:

    component = annotated_component.component

    all_inputs = get_inputs_for_callset(callset, component)

    array_inputs = [
        input for input in all_inputs if isinstance(input, ArrayComponentInput)
    ]

    match array_inputs:
        case []:
            return None
        case [array_input]:
            input_batch = array_input.inputs[idx]
        case [*_]:
            raise ValueError("Multiple array inputs per callset passed validation")

    ordered_kv = list(input_batch.inputs.items())
    ordered_keys = [x[0] for x in ordered_kv]
    ordered_outputs = [x[1] for x in ordered_kv]

    input_val_names = [
        f"{get_parent_name(single_output, gen_data, all_written)}"
        for single_output in ordered_outputs
    ]

    all_type_names = [
        get_type_name_for_array_input(component, idx, single_input.input_name)
        for single_input in array_inputs
    ]

    all_values = [
        generate_array_input_field_for(
            t_name,
            array_input.as_single_at(idx, field_name),
            val_name,
            idx,
            component,
            gen_data,
        )
        for (t_name, field_name, val_name) in zip(
            all_type_names, ordered_keys, input_val_names
        )
    ]

    values = "\n".join(all_values)

    # Sorting all_values will sort by input name
    # Those manually specifying a struct should be sorted as well to ensure initialization
    # order is correct
    input_struct_initializers_list = sorted(
        f".{c.input_name} = {c.input_name}_v," for c in array_inputs
    )

    input_struct_initializers = "\n".join(input_struct_initializers_list)

    if callset.input_struct_path is None:
        input_struct_fields_list = sorted(
            generate_array_struct_field_for(
                t_name, array_input.as_single_at(idx, key), component
            )
            for (t_name, key) in zip(all_type_names, ordered_keys)
        )
        input_struct_fields = "\n".join(input_struct_fields_list)
        input_struct = f"struct {ARRAY_INPUT_STRUCT_NAME} {{{input_struct_fields}}};"
        input_struct_name = ARRAY_INPUT_STRUCT_NAME
    else:
        class_name = get_alias_for(annotated_component.component)
        input_struct = ""
        input_struct_name = f"{class_name}::{callset.input_struct_path}"

    return f"""
{input_struct}

{values}

{input_struct_name} {ARRAY_INPUT_NAME} = {{
    {input_struct_initializers}
}};"""
