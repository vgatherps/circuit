from pycircuit.cpp_codegen.call_generation.init_generation.generate_single_init import (
    generate_single_init_for, INPUT_JSON_NAME
)
from pycircuit.cpp_codegen.generation_metadata import GenerationMetadata

# TODO support init calls on static elements - constants are a key example


def generate_init_call(struct_name: str, gen_data: GenerationMetadata) -> str:

    individual_init_calls = "\n".join(
        generate_single_init_for(annotated)
        for annotated in gen_data.annotated_components.values()
        if annotated.component.definition.init_spec is not None
    )

    # TODO what's the type of json
    return f"""
{struct_name}::{struct_name}(nlohmann::json {INPUT_JSON_NAME})
 : externals(), outputs() {{
{individual_init_calls}
}}
"""
