from typing import List

from pycircuit.circuit_builder.circuit import ComponentInput
from pycircuit.circuit_builder.definition import CallSpec
from pycircuit.cpp_codegen.call_generation.call_data import CallData
from pycircuit.cpp_codegen.call_generation.callset import get_inputs_for_callset
from pycircuit.cpp_codegen.call_generation.find_children_of import CalledComponent
from pycircuit.cpp_codegen.call_generation.single_call.generate_output_calldata import (
    get_valid_path,
)
from pycircuit.cpp_codegen.generation_metadata import (
    AnnotatedComponent,
    GenerationMetadata,
)
from pycircuit.cpp_codegen.type_names import get_type_name_for_input


def generate_all_validity_references(
    children_for_call: List[CalledComponent], metadata: GenerationMetadata
) -> str:
    pass
