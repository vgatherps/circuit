from pycircuit.circuit_builder.circuit import ComponentOutput
from pycircuit.cpp_codegen.call_generation.call_metadata import CallMetaData
from pycircuit.cpp_codegen.call_generation.dotfile.generate_dot_for_called import (
    generate_dot_for_called,
)
from pycircuit.cpp_codegen.call_generation.find_children_of import find_all_children_of
from pycircuit.cpp_codegen.generation_metadata import GenerationMetadata


def generate_external_dot_body_for(
    meta: CallMetaData, gen_data: GenerationMetadata
) -> str:

    children_for_call = find_all_children_of(meta.triggered, gen_data.circuit)

    triggered_outputs = {
        ComponentOutput(parent="external", output_name=triggered)
        for triggered in meta.triggered
    }

    dot_lines = generate_dot_for_called(triggered_outputs, children_for_call)

    return f"""digraph {{
{dot_lines}
}}"""
