from typing import List, Sequence

from pycircuit.circuit_builder.circuit import Component, ComponentInput
from pycircuit.circuit_builder.definition import CallSpec
from pycircuit.cpp_codegen.call_generation.callset import get_inputs_for_callset
from pycircuit.cpp_codegen.generation_metadata import (
    AnnotatedComponent,
    GenerationMetadata,
    OutputMetadata,
)
from pycircuit.cpp_codegen.type_names import (
    generate_output_type_alias_name,
    get_alias_for,
    get_type_name_for_input,
)

# On one hand, having this largely rely on auto
# make the codegen easier.
#
# On the other, it introduces huge room for error esepcially around reference autoconversion

# TODO move as much of this as possible into the metadata/graph generation phase
# completely decoupling the logic generation from the code generation

OUTPUT_STRUCT_NAME = "__OUTPUT__"
OUTPUT_NAME = "__output__"
INPUT_STRUCT_NAME = "__INPUT__"
INPUT_NAME = "__input__"
VALID_DATA_NAME = "__valid__"


def get_parent_name(c: ComponentInput, meta: GenerationMetadata) -> str:
    if c.parent == "external":
        return f"externals.{c.output_name}"
    else:
        parent = meta.annotated_components[c.parent]
        if meta.annotated_components[c.parent].output_data[c.output_name].is_ephemeral:
            root_name = f"{parent.component.name}_{c.output_name}_EV__"
        else:
            # TODO post-refactor nest this struct
            root_name = f"outputs.{c.parent}_{c.output_name}"

        return f"{root_name}"


def get_valid_path(component: AnnotatedComponent, output: str):
    output_metadata = component.output_data.get(
        output, OutputMetadata(validity_index=None)
    )
    if output_metadata.is_ephemeral:
        return f"{component.component.name}_{output}_IV"
    else:
        return f"outputs.is_valid[{output_metadata.validity_index}]"


def get_valid_path_external(input: ComponentInput, gen_data: GenerationMetadata):
    if input.parent == "external":
        the_external = gen_data.circuit.external_inputs[input.output_name]
        return f"externals.is_valid[{the_external.index}]"
    else:
        return get_valid_path(
            gen_data.annotated_components[input.parent], input.output_name
        )


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
        output_name = get_valid_path(annotated_component, first_output)
        return f"{output_name} = {VALID_DATA_NAME};"
    else:
        return "\n".join(
            f"{get_valid_path(annotated_component, output)} = {VALID_DATA_NAME}.{output};"
            for output in used_outputs
        )


def generate_is_valid_inits(
    annotated_component: AnnotatedComponent, used_outputs: Sequence[str]
):
    used_outputs = list(used_outputs)
    is_valid_init_lines = []

    for output in used_outputs:
        output_metadata = annotated_component.output_data.get(
            output, OutputMetadata(validity_index=None)
        )
        if output_metadata.is_ephemeral:
            is_valid_init_lines.append(
                f"bool {get_valid_path(annotated_component, output)} = false;"
            )

    return "\n".join(is_valid_init_lines)


def generate_local_output_ref_name(component_name: str, output_name: str) -> str:
    return f"{component_name}_{output_name}"


def generate_value_inits(
    annotated_component: AnnotatedComponent, used_outputs: Sequence[str]
):
    used_outputs = list(used_outputs)
    output_lines = []

    definition = annotated_component.component.definition
    name = annotated_component.component.name
    class_name = get_alias_for(annotated_component.component)
    for output in used_outputs:
        output_metadata = annotated_component.output_data.get(
            output, OutputMetadata(validity_index=None)
        )

        output_class = definition.output_specs[output].type_path
        type_header = f"{class_name}::{output_class}"
        var_name = generate_local_output_ref_name(name, output)

        reference_header = f"{type_header}& {var_name}"

        if output_metadata.is_ephemeral:

            init_var_name = f"{var_name}_EV__"
            output_line = [
                f"{type_header} {init_var_name}{{}};",
                f"{reference_header} = {init_var_name};",
            ]
        else:
            output_line = [f"{reference_header} = this->outputs.{name}_{output};"]

        output_lines += output_line

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


def generate_single_call(
    annotated_component: AnnotatedComponent,
    callset: CallSpec,
    gen_data: GenerationMetadata,
    postfix_args: List[str] = [],
) -> str:
    # TODO How to deal with generics? Can/should just do in order

    component = annotated_component.component

    is_valid_inits = generate_is_valid_inits(annotated_component, list(callset.outputs))
    validity_deconstruction = deconstruct_valid_output(
        annotated_component, list(callset.outputs)
    )
    value_inits = generate_value_inits(annotated_component, list(callset.outputs))

    inputs = get_inputs_for_callset(callset, component)

    input_names = [f"{get_parent_name(c, gen_data)}" for c in inputs]

    all_type_names = [get_type_name_for_input(component, c.input_name) for c in inputs]

    # TODO get tests set up that create the entire set of metadata
    all_values = [
        f"""
            bool is_{c.input_name}_v = {get_valid_path_external(c, gen_data)};
            optional_reference<const {t_name}> {c.input_name}_v({name}, is_{c.input_name}_v);
        """
        for (t_name, c, name) in zip(all_type_names, inputs, input_names)
    ]

    input_struct_fields = "\n".join(
        f"optional_reference<const {t_name}> {c.input_name};"
        for (t_name, c) in zip(all_type_names, inputs)
    )

    input_struct_initializers = "\n".join(
        f".{c.input_name} = {c.input_name}_v," for c in inputs
    )

    output_struct = generate_output_struct(component, list(callset.outputs))
    output_struct_inits = generate_output_struct_initializers(
        component, list(callset.outputs)
    )

    input_list = ",".join([INPUT_NAME] + postfix_args + [OUTPUT_NAME])

    call_name = f"{annotated_component.call_path}({input_list})"

    values = "\n".join(all_values)
    return f"""
    {value_inits}
    {is_valid_inits}
    {{

        struct {INPUT_STRUCT_NAME} {{
            {input_struct_fields}
        }};

        {values}

        {INPUT_STRUCT_NAME} {INPUT_NAME} = {{
            {input_struct_initializers}
        }};

        struct {OUTPUT_STRUCT_NAME} {output_struct};

        {OUTPUT_STRUCT_NAME} {OUTPUT_NAME} {output_struct_inits};

        auto {VALID_DATA_NAME} = {call_name};
        {validity_deconstruction}
    }}
    """
