from typing import List

from pycircuit.circuit_builder.definition import OutputSpec
from pycircuit.cpp_codegen.call_generation.find_children_of import CalledComponent
from pycircuit.cpp_codegen.call_generation.single_call.generate_output_calldata import (
    get_valid_path,
)
from pycircuit.cpp_codegen.generation_metadata import GenerationMetadata


# This is sort of duplicated?
# For always valid outputs that *are not* written as part of the call tree
# Generate something referencing true
# TODO does it make sense to generate all these validity vars upfront,
# and not worry about it in the function logic?
def generate_extra_validity_references(
    children_for_call: List[CalledComponent], metadata: GenerationMetadata
) -> str:
    called_children_names = set(child.component.name for child in children_for_call)
    requested_inputs = [
        child.component.inputs[input]
        for child in children_for_call
        for input in child.callset.written_set | child.callset.observes
    ]

    input_with_component = [
        (input, metadata.annotated_components[input.parent])
        for input in requested_inputs
        if input.parent != "external"
    ]

    static_valid_defs = [
        f"constexpr bool {get_valid_path(component, input.output_name)} = true;"
        for (input, component) in input_with_component
        if (input.parent not in called_children_names)
        and component.component.definition.d_output_specs[
            input.output_name
        ].always_valid
    ]

    static_invalid_defs = [
        f"constexpr bool {get_valid_path(component, input.output_name)} = false;"
        for (input, component) in input_with_component
        if (input.parent not in called_children_names)
        and component.component.definition.d_output_specs[
            input.output_name
        ].assume_invalid
    ]

    return "\n".join(static_valid_defs + static_invalid_defs)
