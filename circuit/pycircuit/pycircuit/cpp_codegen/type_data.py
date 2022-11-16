from typing import List

from pycircuit.circuit_builder.circuit import Component, ComponentInput


def get_sorted_inputs(component: Component) -> List[ComponentInput]:
    return sorted(component.inputs.values(), key=lambda x: x.input_idx)


def get_type_name_for_input(component: Component, input: ComponentInput):
    return f"{component.name}_{input.input_name}_T"


def get_using_declarations_for(
    struct_name: str, externals_name: str, component: Component
) -> List[str]:
    names = []
    for c in component.inputs.values():
        if c.parent == "external":
            value_path = f"{externals_name}::{c.output_name}"
        else:
            value_path = f"{struct_name}::{c.parent}.{c.output_name}"

        type_name = get_type_name_for_input(component, c)
        name = f"using {type_name} = decltype({value_path});"
        names.append(name)

    return names


def get_output_types_for(component: Component):
    return [get_type_name_for_input(component, c) for c in get_sorted_inputs(component)]
