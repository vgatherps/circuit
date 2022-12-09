from typing import Set

from pycircuit.cpp_codegen.call_generation.call_metadata import CallMetaData
from pycircuit.cpp_codegen.call_generation.find_children_of import find_all_children_of
from pycircuit.cpp_codegen.generation_metadata import GenerationMetadata


def get_call_headers_for(meta: CallMetaData, gen_data: GenerationMetadata) -> Set[str]:
    children_for_call = find_all_children_of(meta.triggered, gen_data.circuit)
    return {comp.component.definition.header for comp in children_for_call}
