from pycircuit.cpp_codegen.call_generation.call_data import CallData
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

INPUT_JSON_NAME = "__IN_JSON__"


def get_params_lookup(component_name: str) -> str:
    return f'{INPUT_JSON_NAME}["{component_name}"]'


def generate_single_init_for(
    annotated_component: AnnotatedComponent, gen_data: GenerationMetadata
) -> CallGen:
    component = annotated_component.component
    definition = component.definition

    assert definition.init_spec is not None

    init_spec = definition.init_spec

    all_outputs = set(definition.outputs())

    output_calls = generate_output_calldata(annotated_component, all_outputs)

    call_datas = [output_calls]

    if init_spec.metadata:
        metadata = generate_metadata_calldata(
            annotated_component, set(init_spec.metadata), gen_data
        )

        call_datas.append(metadata)

    if init_spec.takes_params:
        json_data = f'{INPUT_JSON_NAME}["{component.name}"]'
        call_datas.append(CallData(call_params=[json_data]))

    call_path = f"{annotated_component.call_root}{init_spec.init_call}"

    return CallGen(call_datas=call_datas, call_path=call_path)
