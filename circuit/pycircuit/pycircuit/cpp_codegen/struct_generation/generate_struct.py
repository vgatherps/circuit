from typing import List

from pycircuit.circuit_builder.circuit import CircuitData, Component
from pycircuit.cpp_codegen.generation_metadata import (
    AnnotatedComponent,
    GenerationMetadata,
    generate_call_signature,
)
from pycircuit.cpp_codegen.type_data import get_alias_for, get_using_declarations_for

EXTERNALS_STRUCT_NAME = "externals"
OUTPUT_STRUCT_NAME = "output"


def generate_externals_struct(circuit: CircuitData) -> str:
    externals = "\n".join(
        f"{ext.type} {name};" for (name, ext) in circuit.external_inputs.items()
    )
    validity = f"""
    bool is_valid[{len(circuit.external_inputs)}];
    """
    return f"""
        struct Externals {{
            {externals}

            {validity}
        }};
    """


def generate_output_type_alias_name(component_name: str, output: str) -> str:
    return f"{component_name}_{output}_O_T"


def generate_output_type_alias(component: Component, output: str):
    output_type = component.definition.d_outputs[output].type_path
    type_name = generate_output_type_alias_name(component.name, output)
    return f"using {type_name} = {get_alias_for(component)}::{output_type};"


def generate_output_declarations_for_component(component: Component, output: str):
    output_type = component.definition.d_outputs[output].type_path
    return f"{get_alias_for(component)}::{output_type} {component.name}_{output};"


def generate_output_substruct(
    metadata: GenerationMetadata,
) -> str:

    circuit_declarations = "\n\n".join(
        generate_output_declarations_for_component(component.component, output)
        for component in metadata.annotated_components.values()
        for output in component.component.definition.all_outputs()
        if not component.output_data[output].is_ephemeral
    )

    num_valid_outputs = len(metadata.non_ephemeral_components)

    return f"""
        struct Outputs {{
            {circuit_declarations}

            bool is_valid[{num_valid_outputs + 1}];
        }};
    """


def generate_usings_for(
    annotated_components: List[AnnotatedComponent], circuit: CircuitData
) -> str:
    using_declarations_list: List[str] = sum(
        [
            get_using_declarations_for(component, circuit)
            for component in annotated_components
        ],
        [],
    )
    return "\n".join(using_declarations_list)


def generate_circuit_struct(circuit: CircuitData, gen_data: GenerationMetadata):

    usings = generate_usings_for(list(gen_data.annotated_components.values()), circuit)
    externals = generate_externals_struct(circuit)
    output = generate_output_substruct(gen_data)

    calls = "\n".join(
        generate_call_signature(call) + ";" for call in gen_data.call_endpoints
    )

    return f"""
    struct {gen_data.struct_name} {{
        {usings}

        {externals}
        Externals externals;

        {output}
        Outputs outputs;

        {calls}
    }};
    """
