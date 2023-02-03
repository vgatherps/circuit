from typing import List, Set

from pycircuit.circuit_builder.component import ComponentOutput
from pycircuit.circuit_builder.definition import CallSpec
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
from pycircuit.cpp_codegen.call_generation.call_data import CallGen

# TODO this path here could *really* get cleaned up


def generate_array_call(
    annotated_component: AnnotatedComponent,
    callset: CallSpec,
    gen_data: GenerationMetadata,
    all_written: Set[ComponentOutput],
) -> List[CallGen]:

    calls = callset.calls()
    if calls is None:
        raise ValueError("Call generation called for a callset with no callback")

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
        case [*many_array]:
            raise ValueError(f"Somehow wrote multiple array inputs: {many_array}")

    written_indices = [
        idx
        for (idx, batch) in enumerate(array_input.inputs)
        if any(batch_input in all_written for batch_input in batch.inputs.values())
    ]

    assert written_indices

    all_calls = []

    for idx in written_indices:
        for callback in calls:
            call_datas = []
            single_input_data = generate_single_input_calldata(
                annotated_component, callset, gen_data, all_written
            )
            array_input_data = generate_array_input_calldata(
                annotated_component, callset, gen_data, all_written, idx
            )

            call_datas.append(single_input_data)
            call_datas.append(array_input_data)

            if callset.outputs:
                output_data = generate_output_calldata(
                    annotated_component,
                    set(callset.outputs),
                )
                call_datas.append(output_data)

            if callset.metadata:
                metadata = generate_metadata_calldata(
                    annotated_component, set(callset.metadata), gen_data
                )
                call_datas.append(metadata)

            call_path = f"{annotated_component.call_root}{callback}"

            all_calls.append(CallGen(call_path=call_path, call_datas=call_datas))

    return all_calls
