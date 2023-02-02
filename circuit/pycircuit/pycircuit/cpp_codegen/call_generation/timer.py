from pycircuit.circuit_builder.circuit import Component
from pycircuit.cpp_codegen.call_generation.find_children_of import (
    CalledComponent,
)
from pycircuit.cpp_codegen.generation_metadata import (
    LOCAL_DATA_LOAD_PREFIX,
    LOCAL_TIME_LOAD_PREFIX,
    AnnotatedComponent,
    GenerationMetadata,
)
from pycircuit.circuit_builder.circuit import TIME_TYPE
from pycircuit.cpp_codegen.generation_metadata import TIME_VAR, INPUT_VOID_VAR
from pycircuit.cpp_codegen.call_generation.call_context.call_context import (
    CallContext,
    RecordInfo,
)
from pycircuit.cpp_codegen.call_generation.generate_call_for_trigger import (
    add_calls_to_context,
)


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

    assert component.definition.timer_callset is not None

    signature = generate_timer_signature(
        component, prefix=f"void {gen_data.struct_name}::"
    )

    all_outputs_of_timer = {
        component.output(which) for which in component.definition.timer_callset.outputs
    }

    assert component.definition.timer_callset is not None
    timer_call_extra = CalledComponent(
        callset=component.definition.timer_callset, component=component
    )

    context = CallContext(metadata=gen_data)

    context.append_lines(
        RecordInfo(lines=[LOCAL_DATA_LOAD_PREFIX], description="local load prefix")
    )
    context.append_lines(
        RecordInfo(lines=[LOCAL_TIME_LOAD_PREFIX], description="local time prefix")
    )

    add_calls_to_context(
        all_outputs_of_timer, gen_data, context, prepend_calls=[timer_call_extra]
    )

    call_body = context.generate()

    return f"""\
{signature} {{
{call_body}
}}"""
