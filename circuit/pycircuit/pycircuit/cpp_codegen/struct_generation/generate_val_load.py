from typing import List

from pycircuit.circuit_builder.component import ComponentOutput
from pycircuit.circuit_builder.definition import OutputSpec
from pycircuit.cpp_codegen.generation_metadata import (
    AnnotatedComponent,
    GenerationMetadata,
)
from pycircuit.cpp_codegen.type_names import get_alias_for

OUTPUT_STR_NAME = "__output__"
COMPONENT_STR_NAME = "__component__"
TYPE_ID_NAME = "__typeid__"
BASE_NAME = "__base__"
REAL_COMPONENT_LOOKUP_NAME = "do_real_component_lookup"


def generate_real_output_lookup_signature(prefix: str, postfix: str) -> str:
    return f"""\
RawOutputHandle {prefix}{REAL_COMPONENT_LOOKUP_NAME} (
    const std::string &{COMPONENT_STR_NAME},
    const std::string &{OUTPUT_STR_NAME},
    const std::type_info &{TYPE_ID_NAME}
) {postfix}
"""


def get_component_validity(annotated: AnnotatedComponent, output: str) -> str:
    if annotated.component.definition.d_output_specs[output].always_valid:
        return "&this->alwaystrue"
    else:
        index = annotated.output_data[output].validity_index
        if index is None:
            raise ValueError(
                f"Tried to load a validity index for output {output} "
                f"of {annotated.component.name}, but there was no index"
            )
        return f"&this->outputs.is_valid[{index}]"


def generate_check_for_loadable_output(
    annotated: AnnotatedComponent, output: str, spec: OutputSpec
) -> str:
    alias = get_alias_for(annotated.component)
    name = annotated.component.name
    type_name = f"{alias}::{spec.type_path}"

    # TODO add the failure mode for ephemeral
    return f"""\
if ("{output}" == {OUTPUT_STR_NAME}) {{
    if (typeid({type_name}) == {TYPE_ID_NAME}) {{
        const char *output = reinterpret_cast<const char *>(&this->outputs.{name}_{output});
        const char *valid = reinterpret_cast<const char *>({get_component_validity(annotated, output)});

        std::uint32_t value_offset = output - {BASE_NAME};
        std::uint32_t valid_offset = valid - {BASE_NAME};

        return RawOutputHandle(value_offset, valid_offset);
    }} else {{
        throw std::runtime_error("Component {name} got wrong type requesting {output}");
    }}
}}"""


def generate_error_for_ephemeral_component(annotated: AnnotatedComponent, output: str):
    name = annotated.component.name
    return f"""\
if ("{output}" == {OUTPUT_STR_NAME}) {{
    throw std::runtime_error("Component {name} requesting handle to ephemeral output {output}");
}}"""


def generate_check_for_output(
    annotated: AnnotatedComponent, output: str, spec: OutputSpec
) -> str:
    if annotated.output_data[output].is_value_ephemeral:
        return generate_error_for_ephemeral_component(annotated, output)
    else:
        return generate_check_for_loadable_output(annotated, output, spec)


def generate_checks_for_component(annotated: AnnotatedComponent):

    name = annotated.component.name
    check_strs = "\n\n".join(
        generate_check_for_output(annotated, output, spec)
        for (output, spec) in annotated.component.definition.d_output_specs.items()
    )

    return f"""\
if ("{name}" == {COMPONENT_STR_NAME}) {{
{check_strs}

throw std::runtime_error("Could not find outputs for component {name}");
}}"""


def generate_checks_for_all_components(
    components: List[AnnotatedComponent], struct_name: str
) -> str:

    component_checks = "\n\n".join(
        generate_checks_for_component(comp) for comp in components
    )

    prefix = f"{struct_name}::"

    return f"""{generate_real_output_lookup_signature(prefix, "")} {{
const char * {BASE_NAME} = reinterpret_cast<const char *>(this);
{component_checks}

throw std::runtime_error("Could not match component name");
}}"""
