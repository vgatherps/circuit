from pycircuit.cpp_codegen.call_generation.call_metadata import CallMetaData
from pycircuit.cpp_codegen.call_generation.find_children_of import find_all_children_of
from pycircuit.cpp_codegen.call_generation.generate_extra_vars import (
    generate_extra_validity_references,
)
from pycircuit.cpp_codegen.call_generation.single_call.generate_single_call import (
    generate_single_call,
)
from pycircuit.cpp_codegen.generation_metadata import (
    LOCAL_DATA_LOAD_PREFIX,
    GenerationMetadata,
    generate_call_signature,
)


def generate_external_call_body_for(
    meta: CallMetaData, gen_data: GenerationMetadata
) -> str:

    children_for_call = find_all_children_of(meta.triggered, gen_data.circuit)

    # Dedup a bit here
    all_outputs = {
        child.component.output(output)
        for child in children_for_call
        for output in child.callset.outputs
    }

    extra_validity = generate_extra_validity_references(children_for_call, gen_data)
    all_children = "\n".join(
        generate_single_call(
            gen_data.annotated_components[called_component.component.name],
            called_component.callset,
            gen_data,
            all_outputs,
        )
        for called_component in children_for_call
    )

    signature = generate_call_signature(meta, prefix=f"{gen_data.struct_name}::")

    return f"""
    {signature} {{
{LOCAL_DATA_LOAD_PREFIX}
{extra_validity}
{all_children}
    }}
    """
