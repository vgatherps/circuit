from pycircuit.circuit_builder.circuit import Component
from pycircuit.cpp_codegen.call_generation.find_children_of import (
    CalledComponent,
    find_all_children_of_from_outputs,
)
from pycircuit.cpp_codegen.call_generation.generate_extra_vars import (
    generate_default_value_generators,
    generate_extra_validity_references,
)
from pycircuit.cpp_codegen.call_generation.single_call.generate_single_call import (
    generate_single_call,
)
from pycircuit.cpp_codegen.generation_metadata import (
    LOCAL_DATA_LOAD_PREFIX,
    LOCAL_TIME_LOAD__PREFIX,
    AnnotatedComponent,
    GenerationMetadata,
)
from pycircuit.circuit_builder.circuit import TIME_TYPE
from pycircuit.cpp_codegen.generation_metadata import TIME_VAR, INPUT_VOID_VAR


def generate_timer_name(component: Component):
    assert component.definition.timer_callset is not None
    return f"{component.name}TimerCallback"


def generate_timer_signature(component: Component, prefix: str = ""):
    assert component.definition.timer_callset is not None
    name = generate_timer_name(component)
    return f"{prefix}{name}(void *{INPUT_VOID_VAR}, {TIME_TYPE} {TIME_VAR})"


def generate_timer_call_body_for(
    annotated_component: AnnotatedComponent, gen_data: GenerationMetadata
) -> str:

    component = annotated_component.component

    if component.definition.timer_callset is None:
        raise ValueError(
            f"Component {component.name} of type {component.definition.class_name} has no timer callback"
        )

    all_outputs_of_timer = {
        component.output(which) for which in component.definition.timer_callset.outputs
    }

    children_for_call = find_all_children_of_from_outputs(
        gen_data.circuit, all_outputs_of_timer
    )

    all_outputs = all_outputs_of_timer | {
        child.component.output(output)
        for child in children_for_call
        for output in child.callset.outputs
    }

    first_called = CalledComponent(
        component=component,
        callset=component.definition.timer_callset,
    )
    extra_validity = generate_extra_validity_references(
        [first_called] + children_for_call, gen_data
    )
    default_values = generate_default_value_generators(
        children_for_call, gen_data, all_outputs
    )

    all_children = "\n".join(
        generate_single_call(
            gen_data.annotated_components[child_component.component.name],
            child_component.callset,
            gen_data,
            all_outputs,
        )
        for child_component in children_for_call
    )

    signature = generate_timer_signature(
        component, prefix=f"void {gen_data.struct_name}::"
    )

    timer_callback = generate_single_call(
        annotated_component, component.definition.timer_callset, gen_data, all_outputs
    )

    return f"""{signature} {{
{LOCAL_DATA_LOAD_PREFIX}
{LOCAL_TIME_LOAD__PREFIX}
{extra_validity}
{default_values}
{timer_callback}
{all_children}
}}"""
