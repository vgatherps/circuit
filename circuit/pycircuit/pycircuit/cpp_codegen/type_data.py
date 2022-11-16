from typing import List

from pycircuit.circuit_builder.circuit import Circuit, Component, ComponentInput


def get_class_declaration_for(component: Component) -> str:
    generics = ",".join(get_output_types_for(component))
    return f"{component.definition.class_name}<{generics}>::Output {component.name}"


def get_alias_for(component: Component) -> str:
    return f"{component.name}_A"


def get_sorted_inputs(component: Component) -> List[ComponentInput]:
    return sorted(component.inputs.values(), key=lambda x: x.input_idx)


def get_type_name_for_input(component: Component, input: ComponentInput):
    return f"{component.name}_{input.input_name}_T"


def get_using_declarations_for(component: Component, circuit: Circuit) -> List[str]:
    class_declaration = get_class_declaration_for(component)
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


def get_output_types_for(component: Component):
    return [get_type_name_for_input(component, c) for c in get_sorted_inputs(component)]
