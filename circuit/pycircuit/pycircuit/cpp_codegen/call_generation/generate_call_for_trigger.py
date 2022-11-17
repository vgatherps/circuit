from typing import Set

from pycircuit.cpp_codegen.call_generation.call_metadata import CallMetaData
from pycircuit.cpp_codegen.call_generation.find_children_of import find_all_children_of
from pycircuit.cpp_codegen.call_generation.generate_single_call import (
    generate_single_call,
)
from pycircuit.cpp_codegen.generation_metadata import GenerationMetadata


def generate_calls_for(meta: CallMetaData, gen_data: GenerationMetadata) -> str:

    children_for_call = find_all_children_of(meta.triggered, gen_data.circuit)
    all_children = "\n".join(
        generate_single_call(
            gen_data.annotated_components[component.name],
            gen_data,
        )
        for component in children_for_call
    )

    return f"""
    void {meta.call_name}() {{
        {all_children}
    }}
    """
    pass
