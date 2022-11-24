from pycircuit.circuit_builder.circuit import Component, ComponentInput


def get_alias_for(component: Component) -> str:
    return f"{component.name}_A"


def get_type_name_for_input(component: Component, input: ComponentInput):
    return f"{component.name}_{input.input_name}_T"
