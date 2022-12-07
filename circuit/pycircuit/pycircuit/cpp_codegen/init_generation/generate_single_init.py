from pycircuit.circuit_builder.circuit import Component

INPUT_JSON_NAME = "__IN_JSON__"


def get_params_lookup(component_name: str) -> str:
    return f'{INPUT_JSON_NAME}["{component_name}"]'


def generate_parameterized_init_call(
    component_name: str, component_class: str, call_path: str
):
    return f"""{{
    .{component_name} = {component_class}::{call_path}({get_params_lookup(component_name)}),
}}"""


def generate_plain_init_call(component_name: str, component_class: str, call_path: str):
    return f"""{{
    .{component_name} = {component_class}::{call_path}(),
}}"""


def generate_single_init_for(component: Component) -> str:

    init_spec = component.definition.init_spec
    if init_spec is None:
        raise ValueError(
            "Initialization not possible for static calls (no initialization spec)"
        )

    if init_spec.takes_params:
        return generate_parameterized_init_call(
            component.name, component.definition.class_name, init_spec.init_call
        )
    else:
        return generate_plain_init_call(
            component.name, component.definition.class_name, init_spec.init_call
        )
