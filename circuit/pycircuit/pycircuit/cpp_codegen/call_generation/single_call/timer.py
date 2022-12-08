from pycircuit.cpp_codegen.call_generation.find_children_of import (
    find_all_children_of_from_outputs,
    CalledComponent,
)
from pycircuit.cpp_codegen.call_generation.single_call.generate_single_call import (
    generate_single_call,
)
from pycircuit.cpp_codegen.generation_metadata import (
    LOCAL_DATA_LOAD_PREFIX,
    AnnotatedComponent,
    GenerationMetadata,
)
from pycircuit.cpp_codegen.call_generation.generate_extra_valid_vars import (
    generate_extra_validity_references,
)


def generate_timer_signature(component: AnnotatedComponent, prefix: str = ""):
    assert component.component.definition.timer_callback is not None
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

    first_called = CalledComponent(
        component=component.component,
        callset=component.component.definition.timer_callback.call,
    )
    extra_validity = generate_extra_validity_references(
        [first_called] + children_for_call, gen_data
    )

    all_children = "\n".join(
        generate_single_call(
            gen_data.annotated_components[child_component.component.name],
            child_component.callset,
            gen_data,
        )
        for child_component in children_for_call
    )

    signature = generate_timer_signature(component, prefix=f"{gen_data.struct_name}::")

    timer_callback = generate_single_call(
        component,
        component.component.definition.timer_callback.call,
        gen_data,
    )

    return f"""
    {signature} {{

{LOCAL_DATA_LOAD_PREFIX}
{extra_validity}

        {timer_callback}
        {all_children}
    }}
    """
