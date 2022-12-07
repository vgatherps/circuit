from typing import List

from pycircuit.circuit_builder.circuit import Component
from pycircuit.circuit_builder.definition import CallSpec
from pycircuit.cpp_codegen.call_generation.call_data import CallData, assemble_call_from
from pycircuit.cpp_codegen.call_generation.single_call.generate_input_calldata import (
    generate_input_calldata,
)
from pycircuit.cpp_codegen.call_generation.single_call.generate_output_calldata import (
    generate_output_calldata,
)
from pycircuit.cpp_codegen.generation_metadata import (
    AnnotatedComponent,
    GenerationMetadata,
)

INPUT_JSON_NAME = "__IN_JSON__"


def get_params_lookup(component_name: str) -> str:
    return f'{INPUT_JSON_NAME}["{component_name}"]'


def generate_single_init_for(annotated_component: AnnotatedComponent) -> str:
    component = annotated_component.component
    definition = component.definition
    all_outputs = set(definition.outputs())

    output_calls = generate_output_calldata(annotated_component, all_outputs)

    call_order = [output_calls]

    assert definition.init_spec is not None

    if definition.init_spec.takes_params:
        json_data = f'{INPUT_JSON_NAME}["{component.name}"]'
        call_order.append(CallData(call_params=[json_data]))

    # HACK to ensure that we're not writing this for a static call
    assert annotated_component.call_root[-1] == "."

    call_path = f"{annotated_component.call_root}{definition.init_spec.init_call}"

    return assemble_call_from(call_path, call_order)
