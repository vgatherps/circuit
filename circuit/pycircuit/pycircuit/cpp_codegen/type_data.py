from typing import List

from pycircuit.circuit_builder.circuit import CircuitData, Component, ComponentInput
from pycircuit.cpp_codegen.generation_metadata import AnnotatedComponent
from pycircuit.cpp_codegen.type_names import get_alias_for, get_type_name_for_input


def get_class_declaration_type_for(component: AnnotatedComponent) -> str:
    return f"{component.component.definition.class_name}{component.class_generics}"


def get_sorted_inputs(component: Component) -> List[ComponentInput]:
    return sorted(component.inputs.values(), key=lambda x: x.input_idx)


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
            value_path = f"{get_alias_for(parent_c)}::Output::{c.output_name}"
            dtype = f"decltype({value_path})"

        type_name = get_type_name_for_input(component, c)
        name = f"using {type_name} = {dtype};"
        names.append(name)

    names += [f"using {get_alias_for(component)} = {class_declaration};"]
    names += ["\n"]
    return names
