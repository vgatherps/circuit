from typing import List

from pycircuit.circuit_builder.definition import CallSpec
from pycircuit.cpp_codegen.call_generation.call_data import CallData, assemble_call_from
from pycircuit.cpp_codegen.call_generation.init_generation.generate_single_init import (
    generate_single_init_for,
)
from pycircuit.cpp_codegen.call_generation.single_call.generate_input_calldata import (
    generate_input_calldata,
)
from pycircuit.cpp_codegen.call_generation.single_call.generate_output_calldata import (
    generate_output_calldata,
)
from pycircuit.cpp_codegen.generation_metadata import (
    AnnotatedComponent,
    GenerationMetadata,
)

# TODO support init calls on static elements - constants are a key example


def generate_init_call(struct_name: str, gen_data: GenerationMetadata) -> str:

    individual_init_calls = "\n".join(
        generate_single_init_for(annotated)
        for annotated in gen_data.annotated_components.values()
        if annotated.component.definition.init_spec is not None
    )

    # TODO what's the type of json
    return f"""
{struct_name}::{struct_name}()
 : externals(), outputs() {{
{individual_init_calls}
}}
"""
