from dataclasses import dataclass
from typing import Set

from pycircuit.circuit_builder.circuit import Component
from pycircuit.circuit_builder.definition import CallSpec, Metadata
from pycircuit.cpp_codegen.call_generation.call_data import CallData
from pycircuit.cpp_codegen.generation_metadata import (
    AnnotatedComponent,
    GenerationMetadata,
)

# This is pretty close to what we run for initialization...
# init has no inputs, really only difference

GRAPH_TIMER_NAME = "timer_queue"
TIMER_HANDLE_NAME = "TimerHandle"
META_STRUCT_TYPE = "LocalMetadata"
META_VAR_NAME = "__metadata__"
TIMER_VAR_NAME = "__timer_handle_var__"
TIMER_CALL_NAME = "__timer_handle_call__"


@dataclass
class MetaVar:
    local_lines: str
    param_type: str
    param_name: str


def create_timer_field(component: Component, struct_name: str) -> MetaVar:
    from pycircuit.cpp_codegen.call_generation.timer import generate_timer_name

    timer_callback_name = generate_timer_name(component)
    timer_handle_type = f"TimerHandle"
    local_line = f"""
        {timer_handle_type} {TIMER_VAR_NAME}(__myself->timer,  {timer_callback_name});
    """
    return MetaVar(
        local_lines=local_line,
        param_type=timer_handle_type,
        param_name=TIMER_VAR_NAME,
    )


META_CREATORS = {Metadata.Timer: create_timer_field}

# TODO testme


def generate_metadata_calldata(
    annotated_component: AnnotatedComponent,
    metadata: Set[Metadata],
    gen_data: GenerationMetadata,
) -> CallData:
    # TODO How to deal with generics? Can/should just do in order

    assert len(metadata) > 0

    component = annotated_component.component
    local_lines_list = []
    struct_lines_list = []
    struct_inits_list = []

    for meta in metadata:
        var = META_CREATORS[meta](component, gen_data.struct_name)
        local_lines_list.append(var.local_lines)
        struct_lines_list.append(f"{var.param_type} {meta.value};")
        struct_inits_list.append(f".{meta.value} = {var.param_name}")

    local_lines = "\n".join(local_lines_list)
    struct_lines = ",\n".join(struct_lines_list)
    struct_inits = "\n".join(struct_inits_list)

    prefix_lines = f"""
{local_lines}

struct {META_STRUCT_TYPE} {{
    {struct_lines}
}};

{META_STRUCT_TYPE} {META_VAR_NAME} {{
    {struct_inits}
}};
"""

    return CallData(local_prefix=prefix_lines, call_params=[META_VAR_NAME])
