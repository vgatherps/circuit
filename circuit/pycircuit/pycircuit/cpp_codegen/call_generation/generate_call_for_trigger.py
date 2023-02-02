from typing import Optional, Set, List

from pycircuit.circuit_builder.circuit import CallGroup, CircuitData
from pycircuit.circuit_builder.component import ArrayComponentInput, ComponentOutput
from pycircuit.circuit_builder.definition import CallSpec
from pycircuit.cpp_codegen.call_generation.call_metadata import CallMetaData
from pycircuit.cpp_codegen.call_generation.single_call.generate_array_call import (
    generate_array_call,
)
from pycircuit.cpp_codegen.call_generation.single_call.generate_single_call import (
    generate_single_call,
)
from pycircuit.cpp_codegen.generation_metadata import (
    CALL_VAR,
    LOCAL_DATA_LOAD_PREFIX,
    STRUCT_VAR,
    AnnotatedComponent,
    GenerationMetadata,
    generate_true_call_signature,
)
from pycircuit.cpp_codegen.call_generation.call_context.call_context import CallContext
from pycircuit.cpp_codegen.call_generation.call_context.call_context import RecordInfo
from pycircuit.cpp_codegen.call_generation.call_data import CallGen
from pycircuit.cpp_codegen.generation_metadata import LOCAL_TIME_LOAD_PREFIX
from pycircuit.cpp_codegen.call_generation.find_children_of import (
    CalledComponent,
    find_all_children_of_from_outputs,
)

# TODO generate thing to load data from external calls

CALL_OUTWARD = f"""if ({CALL_VAR}) {{
    {CALL_VAR}.call(__myself);
}}"""


def generate_init_externals(group: CallGroup, circuit: CircuitData) -> List[str]:
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

    return lines


def call_dispatch(
    annotated_component: AnnotatedComponent,
    callset: CallSpec,
    gen_data: GenerationMetadata,
    all_written: Set[ComponentOutput],
) -> List[CallGen]:
    pass

    is_array = any(
        isinstance(annotated_component.component.inputs[written], ArrayComponentInput)
        for written in callset.written_set
    )

    if is_array:
        return generate_array_call(annotated_component, callset, gen_data, all_written)
    else:
        return generate_single_call(annotated_component, callset, gen_data, all_written)


def add_calls_to_context(
    triggered: Set[ComponentOutput],
    gen_data: GenerationMetadata,
    context: CallContext,
    callable: Optional[str] = None,
    prepend_calls: List[CalledComponent] = [],
):
    children_for_call = prepend_calls + find_all_children_of_from_outputs(
        gen_data.circuit, triggered
    )

    all_outputs = {
        child.component.output(output)
        for child in children_for_call
        for output in child.callset.outputs
    }

    def with_callset(callset: CallSpec, called_component: CalledComponent):
        call_gen = call_dispatch(
            gen_data.annotated_components[called_component.component.name],
            callset,
            gen_data,
            all_outputs,
        )

        for gen in call_gen:
            context.add_a_call(gen)

    for called_component in children_for_call:
        if called_component.callset.skippable:
            continue
        with_callset(called_component.callset, called_component)

    if callable is not None:
        context.append_lines(
            RecordInfo(lines=[callable], description="Call passed callback")
        )

    for called_component in children_for_call:
        if called_component.callset.cleanup is not None:
            with_callset(called_component.callset.as_cleanup(), called_component)


def generate_external_call_body_for(
    meta: CallMetaData, gen_data: GenerationMetadata
) -> str:

    used_outputs = {
        ComponentOutput(parent="external", output_name=output)
        for output in meta.triggered
    }

    external_initialization = generate_init_externals(
        gen_data.circuit.call_groups[meta.call_name], gen_data.circuit
    )

    signature = generate_true_call_signature(
        meta, gen_data.circuit, prefix=f"void {gen_data.struct_name}::"
    )

    context = CallContext(metadata=gen_data)

    context.append_lines(
        RecordInfo(lines=[LOCAL_DATA_LOAD_PREFIX], description="local load prefix")
    )
    context.append_lines(
        RecordInfo(lines=[LOCAL_TIME_LOAD_PREFIX], description="local time prefix")
    )

    context.append_lines(
        RecordInfo(lines=external_initialization, description="initialize externals")
    )

    add_calls_to_context(used_outputs, gen_data, context, callable=CALL_OUTWARD)

    call_body = context.generate()

    return f"""\
{signature} {{
{call_body}
}}"""
