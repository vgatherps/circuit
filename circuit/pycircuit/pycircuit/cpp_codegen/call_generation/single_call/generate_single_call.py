from typing import List

from pycircuit.circuit_builder.definition import CallSpec
from pycircuit.cpp_codegen.call_generation.call_data import CallData, assemble_call_from
from pycircuit.cpp_codegen.call_generation.single_call.generate_input_calldata import (
    generate_input_calldata,
)
from pycircuit.cpp_codegen.call_generation.single_call.generate_metadata_calldata import (
    generate_metadata_calldata,
)
from pycircuit.cpp_codegen.call_generation.single_call.generate_output_calldata import (
    generate_output_calldata,
)
from pycircuit.cpp_codegen.generation_metadata import (
    AnnotatedComponent,
    GenerationMetadata,
)


def generate_single_call(
    annotated_component: AnnotatedComponent,
    callset: CallSpec,
    gen_data: GenerationMetadata,
) -> str:
    if callset.callback is None:
        raise ValueError("Call generation called for a callset with no callback")
    input_data = generate_input_calldata(annotated_component, callset, gen_data)
    output_data = generate_output_calldata(annotated_component, set(callset.outputs))
    call_path = f"{annotated_component.call_root}{callset.callback}"

    call_data = [input_data, output_data]
    if callset.metadata:
        metadata = generate_metadata_calldata(
            annotated_component, set(callset.metadata), gen_data
        )
        call_data.append(metadata)
    return assemble_call_from(call_path, call_data)
