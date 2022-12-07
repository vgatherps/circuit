from pycircuit.cpp_codegen.call_generation.find_children_of import (
    find_all_children_of_from_outputs,
)
from pycircuit.cpp_codegen.call_generation.single_call.generate_single_call import (
    generate_single_call,
)
from pycircuit.cpp_codegen.generation_metadata import (
    AnnotatedComponent,
    GenerationMetadata,
)


def generate_timer_signature(component: AnnotatedComponent, prefix: str = ""):
    call_type = f"{component.component.definition.timer_callback.ping_with_type} &__timer_data__"
    return f"void {prefix}{component.component.name}TimerCallback({call_type})"


def generate_timer_name(component: AnnotatedComponent) -> str:
    return f"{component.component.name}_timer_event_queue"


def generate_timer_call_body_for(
    component: AnnotatedComponent, gen_data: GenerationMetadata
) -> str:

    if component.component.definition.timer_callback is None:
        raise ValueError(
            f"Component {component.component.name} of type {component.component.definition.class_name} has no timer callback"
        )

    all_outputs = {
        component.component.output(which)
        for which in component.component.definition.timer_callback.call.outputs
    }

    children_for_call = find_all_children_of_from_outputs(gen_data.circuit, all_outputs)

    all_children = "\n".join(
        generate_single_call(
            gen_data.annotated_components[child_component.component.name],
            gen_data,
            children_for_call,
        )
        for child_component in children_for_call
    )

    signature = generate_timer_signature(component, prefix=f"{gen_data.struct_name}::")

    timer_callback = generate_single_call(
        component, gen_data, children_for_call, postfix_args=["__timer_data__"]
    )

    return f"""
    {signature} {{
        {timer_callback}
        {all_children}
    }}
    """
