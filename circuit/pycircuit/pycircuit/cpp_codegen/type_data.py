from typing import List

from pycircuit.circuit_builder.circuit import CircuitData, Component, ComponentInput
from pycircuit.cpp_codegen.generation_metadata import AnnotatedComponent
from pycircuit.cpp_codegen.type_names import (
    generate_output_type_alias,
    get_alias_for,
    get_type_name_for_input,
)


def get_class_declaration_type_for(component: AnnotatedComponent) -> str:
    return f"{component.component.definition.class_name}{component.class_generics}"


def get_using_declarations_for(
    annotated: AnnotatedComponent, circuit: CircuitData
) -> List[str]:
    class_declaration = get_class_declaration_type_for(annotated)
    component = annotated.component
    names = []
    for c in component.inputs.values():
        if c.parent == "external":
            dtype = circuit.external_inputs[c.output_name].type
        else:
            parent_c = circuit.components[c.parent]
            parent_output_path = parent_c.definition.d_output_specs[
                c.output_name
            ].type_path
            dtype = f"{get_alias_for(parent_c)}::{parent_output_path}"

        type_name = get_type_name_for_input(component, c.input_name)
        name = f"using {type_name} = {dtype};"
        names.append(name)

    names += [f"using {get_alias_for(component)} = {class_declaration};"]

    for output in component.definition.outputs():
        names.append(generate_output_type_alias(component, output))

    names += ["\n"]
    return names
