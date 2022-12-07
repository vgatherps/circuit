from typing import Set

from pycircuit.cpp_codegen.generation_metadata import GenerationMetadata

DEFAULT_HEADERS = ["optional_reference.hh"]
STD_HEADERS = ["type_traits"]


def get_struct_headers_for(gen_data: GenerationMetadata) -> Set[str]:
    return {comp.definition.header for comp in gen_data.circuit.components.values()}
