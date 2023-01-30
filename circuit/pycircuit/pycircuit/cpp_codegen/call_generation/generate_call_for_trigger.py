from pycircuit.circuit_builder.circuit import CallGroup, CircuitData
from pycircuit.cpp_codegen.call_generation.call_metadata import CallMetaData
from pycircuit.cpp_codegen.call_generation.find_children_of import find_all_children_of
from pycircuit.cpp_codegen.call_generation.generate_extra_vars import (
    generate_default_value_generators,
    generate_extra_validity_references,
)
from pycircuit.cpp_codegen.call_generation.single_call.generate_single_call import (
    generate_single_call,
)
from pycircuit.cpp_codegen.generation_metadata import (
    LOCAL_DATA_LOAD_PREFIX,
    STRUCT_VAR,
    CALL_VAR,
    GenerationMetadata,
    generate_true_call_signature,
)

# TODO generate thing to load data from external calls


def generate_init_externals(group: CallGroup, circuit: CircuitData):
    lines = []
    for (field, external_name) in group.external_field_mapping.items():
        external = circuit.external_inputs[external_name]
        init_code = f"""if (Optionally<{external.type}>::valid({STRUCT_VAR}.{field})) [[likely]] {{
_externals.is_valid[{external.index}] = true;
_externals.{external_name} = std::move(Optionally<{external.type}>::value({STRUCT_VAR}.{field}));
}} else {{
_externals.is_valid[{external.index}] = false;
}}"""
        lines.append(init_code)

    return "\n".join(lines)


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
    external_initialization = generate_init_externals(
        gen_data.circuit.call_groups[meta.call_name], gen_data.circuit
    )
    default_values = generate_default_value_generators(
        children_for_call, gen_data, all_outputs
    )

    all_children = "\n".join(
        generate_single_call(
            gen_data.annotated_components[called_component.component.name],
            called_component.callset,
            gen_data,
            all_outputs,
        )
        for called_component in children_for_call
    )

    all_cleanups = "\n".join(
        generate_single_call(
            gen_data.annotated_components[called_component.component.name],
            called_component.callset,
            gen_data,
            all_outputs,
            is_cleanup=True,
        )
        for called_component in children_for_call
        if called_component.callset.cleanup is not None
    )

    signature = generate_true_call_signature(
        meta, gen_data.circuit, prefix=f"void {gen_data.struct_name}::"
    )

    return f"""{signature} {{
{LOCAL_DATA_LOAD_PREFIX}
{external_initialization}
{extra_validity}
{default_values}
{all_children}

if ({CALL_VAR}) {{
    {CALL_VAR}.call(__myself);
}}

{all_cleanups}
}}"""
