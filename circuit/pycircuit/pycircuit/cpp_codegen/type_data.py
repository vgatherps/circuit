from typing import List

from pycircuit.circuit_builder.circuit import CircuitData, Component
from pycircuit.cpp_codegen.generation_metadata import AnnotatedComponent
from pycircuit.cpp_codegen.type_names import (
    generate_output_type_alias,
    get_alias_for,
    get_type_name_for_input,
)
from pycircuit.circuit_builder.component import SingleComponentInput
from pycircuit.circuit_builder.component import ComponentOutput
from pycircuit.circuit_builder.component import ArrayComponentInput
from pycircuit.cpp_codegen.type_names import get_type_name_for_array_input


def get_class_declaration_type_for(component: AnnotatedComponent) -> str:
    return f"{component.component.definition.class_name}{component.class_generics}"


def get_using_declarations_for(
    annotated: AnnotatedComponent, circuit: CircuitData
) -> List[str]:
    class_declaration = get_class_declaration_type_for(annotated)
    component = annotated.component
    names = []
    for c in component.inputs.values():
        match c:
            case SingleComponentInput():
                names.append(generate_usings_for_single_input(component, c, circuit))
            case ArrayComponentInput():
                names += generate_usings_for_array_input(component, c, circuit)

    names += [f"using {get_alias_for(component)} = {class_declaration};"]

    for output in component.definition.outputs():
        names.append(generate_output_type_alias(component, output))

    names += ["\n"]
    return names


def get_datatype_for_output(output: ComponentOutput, circuit: CircuitData) -> str:
    if output.parent == "external":
        return circuit.external_inputs[output.output_name].type
    else:
        parent_c = circuit.components[output.parent]
        parent_output_path = parent_c.definition.d_output_specs[
            output.output_name
        ].type_path
        return f"{get_alias_for(parent_c)}::{parent_output_path}"


def generate_usings_for_single_input(
    component: Component, input: SingleComponentInput, circuit: CircuitData
) -> str:
    output = input.output()

    dtype = get_datatype_for_output(output, circuit)
    type_name = get_type_name_for_input(component, input.input_name)
    name = f"using {type_name} = {dtype};"
    return name


def generate_usings_for_array_input(
    component: Component, input: ArrayComponentInput, circuit: CircuitData
) -> List[str]:

    names = []

    for (idx, output) in enumerate(input.outputs()):
        dtype = get_datatype_for_output(output, circuit)
        type_name = get_type_name_for_array_input(component, idx, input.input_name)
        name = f"using {type_name} = {dtype};"
        names.append(name)

    return names
