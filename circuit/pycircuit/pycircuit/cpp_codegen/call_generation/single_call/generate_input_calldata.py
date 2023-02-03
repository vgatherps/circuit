from typing import List, Set

from pycircuit.circuit_builder.component import ComponentOutput
from pycircuit.circuit_builder.definition import CallSpec
from pycircuit.cpp_codegen.call_generation.call_data import CallData
from pycircuit.cpp_codegen.generation_metadata import (
    AnnotatedComponent,
    GenerationMetadata,
)

from pycircuit.cpp_codegen.call_generation.single_call.generate_single_input_calldata import (
    INPUT_NAME,
)
from pycircuit.cpp_codegen.call_generation.single_call.generate_single_input_calldata import (
    generate_single_input_prefix,
)
from pycircuit.cpp_codegen.call_generation.single_call.generate_array_input_calldata import (
    ARRAY_INPUT_NAME,
    generate_array_input_prefix,
)
from pycircuit.circuit_builder.component import Component

# TODO just dump these functions?


def get_used_outputs(component: Component, callset: CallSpec) -> Set[ComponentOutput]:
    used_outputs = []
    for input in callset.inputs():
        for output in component.inputs[input].outputs():
            if output.parent != "external":
                used_outputs.append(output)
    return set(used_outputs)


def generate_single_input_calldata(
    annotated_component: AnnotatedComponent,
    callset: CallSpec,
    gen_data: GenerationMetadata,
    all_written: Set[ComponentOutput],
) -> CallData:

    local_prefix = ""

    inputs_prefix = generate_single_input_prefix(
        annotated_component, callset, gen_data, all_written
    )

    if inputs_prefix is None:
        return CallData()

    local_prefix = local_prefix + (inputs_prefix or "")

    return CallData(
        local_prefix=local_prefix,
        call_params=[INPUT_NAME],
        outputs=get_used_outputs(annotated_component.component, callset),
    )


def generate_array_input_calldata(
    annotated_component: AnnotatedComponent,
    callset: CallSpec,
    gen_data: GenerationMetadata,
    all_written: Set[ComponentOutput],
    idx: int,
) -> CallData:

    local_prefix = ""

    inputs_prefix = generate_array_input_prefix(
        annotated_component, callset, gen_data, all_written, idx
    )

    if inputs_prefix is None:
        return CallData()

    local_prefix = local_prefix + (inputs_prefix or "")

    return CallData(
        local_prefix=local_prefix,
        call_params=[ARRAY_INPUT_NAME],
        outputs=get_used_outputs(annotated_component.component, callset),
    )
