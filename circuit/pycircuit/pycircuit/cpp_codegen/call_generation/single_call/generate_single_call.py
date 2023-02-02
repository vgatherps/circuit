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
from pycircuit.cpp_codegen.call_generation.call_data import CallGen


def generate_single_call(
    annotated_component: AnnotatedComponent,
    callset: CallSpec,
    gen_data: GenerationMetadata,
    all_written: Set[ComponentOutput],
) -> List[CallGen]:
    calls = callset.calls()
    if calls is None:
        raise ValueError("Call generation called for a callset with no callback")

    gen_calls = []

    for callback in calls:
        call_data = []

        if callset.inputs():
            input_data = generate_single_input_calldata(
                annotated_component, callset, gen_data, all_written
            )
            call_data.append(input_data)

        if callset.outputs:
            output_data = generate_output_calldata(
                annotated_component,
                set(callset.outputs),
            )
            call_data.append(output_data)

        if callset.metadata:
            metadata = generate_metadata_calldata(
                annotated_component, set(callset.metadata), gen_data
            )
            call_data.append(metadata)

        call_path = f"{annotated_component.call_root}{callback}"

        gen_calls.append(CallGen(call_datas=call_data, call_path=call_path))

    return gen_calls
