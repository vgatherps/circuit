from pycircuit.circuit_builder.circuit import Component


def get_alias_for(component: Component) -> str:
    return f"{component.name}TypeAlias"


def get_type_name_for_input(component: Component, input_name: str):
    assert input_name in component.inputs
    assert input_name in component.definition.inputs
    return f"{component.name}_{input_name}_T"

def get_type_name_for_array_input(component: Component, idx: int, input_name: str):
    assert input_name in component.inputs
    assert input_name in component.definition.inputs
    return f"{component.name}_{input_name}_{idx}_T"


def generate_output_type_alias_name(component_name: str, output: str) -> str:
    return f"{component_name}_{output}_O_T"


def generate_output_type_alias(component: Component, output: str):
    output_type = component.definition.d_output_specs[output].type_path
    type_name = generate_output_type_alias_name(component.name, output)
    return f"using {type_name} = {get_alias_for(component)}::{output_type};"
