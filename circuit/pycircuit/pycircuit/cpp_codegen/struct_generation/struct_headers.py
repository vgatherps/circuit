from typing import Set

from pycircuit.cpp_codegen.generation_metadata import GenerationMetadata

DEFAULT_HEADERS = [
    "cppcuit/optional_reference.hh",
    "cppcuit/packed_optional.hh",
    "cppcuit/output_handle.hh",
    "timer/timer_queue.hh",
]
STD_HEADERS = ["type_traits", "cstdint", "nlohmann/json_fwd.hpp", "typeinfo"]


def get_struct_headers_for(gen_data: GenerationMetadata) -> Set[str]:
    return {comp.definition.header for comp in gen_data.circuit.components.values()}
