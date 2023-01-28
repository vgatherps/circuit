from typing import List, Set

from pycircuit.circuit_builder.component import ComponentOutput
from pycircuit.circuit_builder.definition import CallSpec
from pycircuit.cpp_codegen.call_generation.call_data import CallData, assemble_call_from
from pycircuit.cpp_codegen.call_generation.single_call.generate_input_calldata import (
    generate_single_input_calldata,
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
from pycircuit.circuit_builder.component import ArrayComponentInput
from pycircuit.cpp_codegen.call_generation.single_call.generate_input_calldata import (
    generate_array_input_calldata,
)

# TODO this path here could *really* get cleaned up


def generate_array_call(
    annotated_component: AnnotatedComponent,
    callset: CallSpec,
    gen_data: GenerationMetadata,
    all_written: Set[ComponentOutput],
) -> str:
    if callset.callback is None:
        raise ValueError("Call generation called for a callset with no callback")

    call_data = []

    inputs = callset.inputs()
    assert inputs

    all_callset_written = [
        annotated_component.component.inputs[written] for written in callset.written_set
    ]

    all_array = [
        input for input in all_callset_written if isinstance(input, ArrayComponentInput)
    ]

    match all_array:
        case []:
            raise ValueError("Called array call for non-array callset")
        case [array_input]:
            pass
        case [*inputs]:
            raise ValueError("Somehow wrote multiple array inputs")

    written_indices = [
        idx
        for (idx, batch) in enumerate(array_input.inputs)
        if any(batch_input in all_written for batch_input in batch.inputs.values())
    ]

    assert written_indices

    must_initialize_outputs = True

    calls = []

    for idx in written_indices:
        single_input_data = generate_single_input_calldata(
            annotated_component, callset, gen_data, all_written
        )
        array_input_data = generate_array_input_calldata(
            annotated_component, callset, gen_data, all_written, idx
        )

        call_data.append(single_input_data)
        call_data.append(array_input_data)

        if callset.outputs:
            output_data = generate_output_calldata(
                annotated_component,
                set(callset.outputs),
                initialize_outputs=must_initialize_outputs,
            )
            call_data.append(output_data)
            must_initialize_outputs = False

        if callset.metadata:
            metadata = generate_metadata_calldata(
                annotated_component, set(callset.metadata), gen_data
            )
            call_data.append(metadata)

        call_path = f"{annotated_component.call_root}{callset.callback}"

        calls.append(assemble_call_from(call_path, call_data))

    return "\n\n".join(calls)
