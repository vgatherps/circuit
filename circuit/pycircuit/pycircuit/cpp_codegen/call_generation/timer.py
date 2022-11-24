from pycircuit.cpp_codegen.call_generation.find_children_of import (
    find_all_children_of_from_outputs,
)
from pycircuit.cpp_codegen.call_generation.generate_single_call import (
    generate_single_call,
)
from pycircuit.cpp_codegen.generation_metadata import (
    AnnotatedComponent,
    GenerationMetadata,
)
from pycircuit.cpp_codegen.type_data import get_sorted_inputs, get_type_name_for_input

from pycircuit.pycircuit.cpp_codegen.call_generation.generate_single_call import (
    get_valid_path_external,
)


def generate_timer_signature(component: AnnotatedComponent, prefix: str = ""):
    return f"void {prefix}{component.component.name}TimerCallback()"


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
        for which in component.component.definition.output.fields
    }

    children_for_call = find_all_children_of_from_outputs(gen_data.circuit, all_outputs)

    all_children = "\n".join(
        generate_single_call(
            gen_data.annotated_components[child_component.name],
            gen_data,
            children_for_call,
        )
        for child_component in children_for_call
    )

    signature = generate_timer_signature(component, prefix=f"{gen_data.struct_name}::")

    timer_callback = generate_single_call(
        component, gen_data, children_for_call, postfix_args=["__front__"]
    )

    return f"""
    {signature} {{

        auto &__timer__ = this->{generate_timer_name(component)};

        if (__timer__.size() == 0) [[unlikely]] {{
            return;
        }}

        // TODO would be nice to find a good way to do this in place instead of moving out of the timer queue
        // Maybe the optimizer could do this if we shifted pop_front to being after, HOWEVER this would
        // also imply that we aren't able to reuse the same space, assuming that most timer callbacks will
        // want to schedule new work
        {component.component.definition.timer_callback.ping_with_type} __front__ = std::move(__timer__.front());
        __timer__.pop_front();

        {timer_callback}


        {all_children}
    }}
    """
