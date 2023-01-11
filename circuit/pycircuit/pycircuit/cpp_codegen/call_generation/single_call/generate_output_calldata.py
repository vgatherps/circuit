from typing import List, Sequence, Set

from pycircuit.circuit_builder.circuit import Component
from pycircuit.cpp_codegen.call_generation.call_data import CallData, ReturnValue
from pycircuit.cpp_codegen.generation_metadata import AnnotatedComponent
from pycircuit.cpp_codegen.type_names import (
    generate_output_type_alias_name,
    get_alias_for,
)

VALID_DATA_NAME = "__valid__"
OUTPUT_STRUCT_NAME = "__OUTPUT__"
OUTPUT_NAME = "__output__"


def get_valid_path(component: AnnotatedComponent, output: str):
    output_metadata = component.output_data[output]
    if output_metadata.validity_index is None:
        return f"{component.component.name}_{output}_IV"
    else:
        return f"outputs_is_valid[{output_metadata.validity_index}]"


def generate_is_valid_inits(
    annotated_component: AnnotatedComponent, used_outputs: Sequence[str]
):
    used_outputs = list(used_outputs)
    is_valid_init_lines = []

    for output in used_outputs:
        # This is already correct for always-invalid outputs
        output_metadata = annotated_component.output_data[output]
        if output_metadata.validity_index is None:
            if annotated_component.component.definition.d_output_specs[
                output
            ].always_valid:
                valid_value = "true"
                valid_prefix = "constexpr bool"
            else:
                valid_value = "false"
                valid_prefix = "bool"
            is_valid_init_lines.append(
                f"{valid_prefix} {get_valid_path(annotated_component, output)} = {valid_value};"
            )

    return "\n".join(is_valid_init_lines)


# can I SFINAE my way into having this work for a bool OR a struct with the right name?
# something like the improved visitor overload for std::variant?

# Worried the below would bloat compile times,
# although it provides drastically better diagnostics
"""
struct extractor {
    template<class T>
    static bool extract(const T& b) {
        if constexpr (std::is_same_v<T, bool>) {
            return b;
        } else if constexpr (requires (T t) {t.a;}) {
            static_assert(std::is_same_v<decltype(b.a), bool>);
            return b.a;
        } else {
            static_assert(false, "The return type of the value does not contain the correct fields");
            return false;
        }
    }
};
"""


def deconstruct_valid_output(
    annotated_component: AnnotatedComponent, used_outputs: Sequence[str]
):
    if len(used_outputs) == 0:
        return ""
    elif len(used_outputs) == 1:
        first_output = list(used_outputs)[0]
        if annotated_component.component.definition.d_output_specs[
            first_output
        ].always_valid:
            return ""
        output_name = get_valid_path(annotated_component, first_output)
        return f"{output_name} = {VALID_DATA_NAME};"
    else:
        return "\n".join(
            f"{get_valid_path(annotated_component, output)} = {VALID_DATA_NAME}.{output};"
            for output in used_outputs
            if not annotated_component.component.definition.d_output_specs[
                output
            ].always_valid
        )


def generate_local_output_ref_name(component_name: str, output_name: str) -> str:
    return f"{component_name}_{output_name}"


def generate_output_init(
    annotated_component: AnnotatedComponent, output: str
) -> List[str]:
    output_metadata = annotated_component.output_data[output]

    definition = annotated_component.component.definition
    name = annotated_component.component.name
    class_name = get_alias_for(annotated_component.component)

    output_class = definition.d_output_specs[output].type_path
    type_header = f"{class_name}::{output_class}"
    var_name = generate_local_output_ref_name(name, output)

    reference_header = f"{type_header}& {var_name}"

    if output_metadata.is_value_ephemeral:

        init_var_name = f"{var_name}_EV__"
        return [
            f"{type_header} {init_var_name}{definition.d_output_specs[output].get_ctor()};",
            f"{reference_header} = {init_var_name};",
        ]
    else:
        return [f"{reference_header} = _outputs.{name}_{output};"]


def generate_value_inits(
    annotated_component: AnnotatedComponent, used_outputs: Sequence[str]
):
    used_outputs = list(used_outputs)
    output_lines = []

    for output in used_outputs:

        output_lines += generate_output_init(annotated_component, output)

    return "\n".join(output_lines)


def generate_output_struct(component: Component, used_outputs: Sequence[str]) -> str:
    used_outputs = list(used_outputs)
    lines = []
    for output in used_outputs:
        lines.append(
            f"{generate_output_type_alias_name(component.name, output)}& {output};"
        )
    struct_lines = "\n".join(lines)
    return f"""{{
{struct_lines}
}}"""


def generate_output_struct_initializers(
    component: Component, used_outputs: Sequence[str]
) -> str:
    used_outputs = list(used_outputs)
    lines = []
    for output in used_outputs:
        var_name = generate_local_output_ref_name(component.name, output)
        lines.append(f".{output} = {var_name},")

    lines_str = "\n".join(lines)

    return f"""{{
{lines_str}
}}"""


def generate_output_calldata(
    annotated_component: AnnotatedComponent,
    all_outputs: Set[str],
    initialize_outputs: bool = True,
) -> CallData:
    outputs = list(all_outputs)
    value_inits = generate_value_inits(annotated_component, outputs)
    is_valid_inits = generate_is_valid_inits(annotated_component, outputs)
    validity_deconstruction = deconstruct_valid_output(annotated_component, outputs)

    output_struct = generate_output_struct(annotated_component.component, outputs)
    output_struct_inits = generate_output_struct_initializers(
        annotated_component.component, outputs
    )

    call_prefix = f"""
        struct {OUTPUT_STRUCT_NAME} {output_struct};

        {OUTPUT_STRUCT_NAME} {OUTPUT_NAME} {output_struct_inits};
    """

    if validity_deconstruction:
        ret = ReturnValue(name=VALID_DATA_NAME)
    else:
        ret = None

    if initialize_outputs:
        global_prefix = "\n".join([value_inits, is_valid_inits])
    else:
        global_prefix = ""

    return CallData(
        global_prefix=global_prefix,
        local_prefix=call_prefix,
        static_return_type=ret,
        local_postfix=validity_deconstruction,
        call_params=[OUTPUT_NAME],
    )
