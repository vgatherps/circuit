from typing import List

from pycircuit.circuit_builder.circuit import ComponentInput
from pycircuit.circuit_builder.definition import CallSpec, OutputSpec
from pycircuit.cpp_codegen.call_generation.call_data import CallData
from pycircuit.cpp_codegen.call_generation.callset import get_inputs_for_callset
from pycircuit.cpp_codegen.call_generation.find_children_of import CalledComponent
from pycircuit.cpp_codegen.call_generation.single_call.generate_output_calldata import (
    get_valid_path,
)
from pycircuit.cpp_codegen.generation_metadata import (
    AnnotatedComponent,
    GenerationMetadata,
)
from pycircuit.cpp_codegen.type_names import get_type_name_for_input

# This is sort of duplicated?
# For always valid outputs that *are not* written as part of the call tree
# Generate something referencing true
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
        if input.parent != 'external'
    ]

    static_defs = [
        f"constexpr bool {get_valid_path(component, input.output_name)} = true;"
        for (input, component) in input_with_component
        if (input.parent not in called_children_names)
        and component.component.definition.d_output_specs.get(
            input.output_name,
            OutputSpec(ephemeral=False, type_path="", always_valid=False),
        ).always_valid
    ]

    return "\n".join(static_defs)
