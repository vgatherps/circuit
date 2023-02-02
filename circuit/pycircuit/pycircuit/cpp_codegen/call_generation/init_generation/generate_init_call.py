from pycircuit.cpp_codegen.call_generation.init_generation.generate_single_init import (
    INPUT_JSON_NAME,
    generate_single_init_for,
)
from pycircuit.cpp_codegen.generation_metadata import (
    LOCAL_DATA_LOAD_PREFIX,
    GenerationMetadata,
)
from pycircuit.cpp_codegen.call_generation.call_context.call_context import CallContext
from pycircuit.cpp_codegen.call_generation.call_context.call_context import RecordInfo

# TODO support init calls on static elements - constants are a key example


def generate_init_call(struct_name: str, gen_data: GenerationMetadata) -> str:

    context = CallContext(metadata=gen_data)

    context.append_lines(
        RecordInfo(lines=[LOCAL_DATA_LOAD_PREFIX], description="local data preload")
    )

    for annotated in gen_data.annotated_components.values():
        if annotated.component.definition.init_spec is not None:
            call_gen = generate_single_init_for(annotated, gen_data)
            context.add_a_call(call_gen)

    call_body = context.generate()

    return f"""\
{struct_name}::{struct_name}(nlohmann::json {INPUT_JSON_NAME})
 : externals(), outputs(), objects() {{

void *__raw_object__ = static_cast<void *>(this);

{call_body}
}}"""
