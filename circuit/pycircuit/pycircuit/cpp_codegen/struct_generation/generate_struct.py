from typing import List

from pycircuit.circuit_builder.circuit import (
    TIME_TYPE,
    CallStruct,
    CircuitData,
    Component,
)
from pycircuit.cpp_codegen.call_generation.call_lookup.generate_call_lookup import (
    LOAD_CALL_TYPE,
    top_level_real_loader,
)
from pycircuit.cpp_codegen.call_generation.timer import generate_timer_signature
from pycircuit.cpp_codegen.generation_metadata import (
    AnnotatedComponent,
    GenerationMetadata,
    generate_true_call_signature,
    generate_wrapper_call,
)
from pycircuit.cpp_codegen.struct_generation.generate_val_load import (
    generate_real_output_lookup_signature,
)
from pycircuit.cpp_codegen.type_data import get_alias_for, get_using_declarations_for

EXTERNALS_STRUCT_NAME = "externals"
OUTPUT_STRUCT_NAME = "output"


def generate_ext_check(ext_type: str, ext_name: str):
    check = f"std::is_default_constructible_v<{ext_type}>"
    msg = f"External {ext_name} with type {ext_type} is must be default constructible"

    return f'static_assert({check}, "{msg}");'


def generate_externals_struct(circuit: CircuitData) -> str:
    externals = "\n".join(
        f"{ext.type} {name};" for (name, ext) in circuit.external_inputs.items()
    )

    asserts = "\n".join(
        set(
            generate_ext_check(ext.type, ext.name)
            for ext in circuit.external_inputs.values()
        )
    )
    validity = f"""
    bool is_valid[{len(circuit.external_inputs)}];
    """
    return f"""
        struct Externals final {{
            {asserts}

            {externals}

            {validity}

            Externals() = default;
        }};
    """


def generate_output_declarations_for_component(
    component: Component, output: str
) -> str:
    output_type = component.definition.d_output_specs[output].type_path
    return f"{get_alias_for(component)}::{output_type} {component.name}_{output};"


def generate_default_constructible_static_checks_for_output(
    component: Component, output: str
) -> str:
    output_type = component.definition.d_output_specs[output].type_path
    type_name = f"{get_alias_for(component)}::{output_type}"

    check = f"std::is_default_constructible_v<{type_name}>"
    msg = f"Output {output} of component {component.name} must be default constructible"

    return f'static_assert({check}, "{msg}");'


def generate_output_substruct(
    metadata: GenerationMetadata,
) -> str:

    circuit_declarations = "\n\n".join(
        generate_output_declarations_for_component(component.component, output)
        for component in metadata.annotated_components.values()
        for output in component.component.definition.outputs()
        if not component.output_data[output].is_value_ephemeral
    )

    assert_declarations = "\n".join(
        set(
            generate_default_constructible_static_checks_for_output(
                component.component, output
            )
            for component in metadata.annotated_components.values()
            for output in component.component.definition.outputs()
        )
    )

    return f"""
        struct Outputs final
        {{
            {assert_declarations}

            {circuit_declarations}

            bool is_valid[{metadata.required_validity_markers}];

            Outputs() = default;
        }};
    """


def generate_default_constructible_static_checks_for_component(
    component: Component,
) -> str:
    type_name = get_alias_for(component)

    check = f"std::is_default_constructible_v<{type_name}>"
    msg = f"Class {component.definition.class_name} for component {component.name} must always be default constructible"

    return f'static_assert({check}, "{msg}");'


def generate_object_declarations_for_component(component: Component) -> str:
    return f"{get_alias_for(component)} {component.name};"


def generate_objects_substruct(
    metadata: GenerationMetadata,
) -> str:

    assert_declarations = "\n".join(
        set(
            generate_default_constructible_static_checks_for_component(
                component.component
            )
            for component in metadata.annotated_components.values()
        )
    )

    object_declarations = "\n\n".join(
        generate_object_declarations_for_component(component.component)
        for component in metadata.annotated_components.values()
        if not component.component.definition.static_call
    )

    return f"""
        struct Objects final
        {{
            {assert_declarations}

            {object_declarations}

            Objects() = default;
        }};
    """


def generate_usings_for(
    annotated_components: List[AnnotatedComponent], circuit: CircuitData
) -> str:
    using_declarations_list: List[str] = sum(
        [
            get_using_declarations_for(component, circuit)
            for component in annotated_components
        ],
        [],
    )
    return "\n".join(using_declarations_list)


def generate_single_input_struct(struct_name: str, struct: CallStruct) -> str:

    if struct.external_struct is not None:
        return f"using {struct_name} = {struct.external_struct.struct_name};"
    else:
        struct_lines = "\n".join(
            f"Optionally<{type}>::Optional {name};"
            for (name, type) in struct.d_inputs.items()
        )
        return f"""struct {struct_name} {{
{struct_lines}
}};"""


def generate_circuit_struct(circuit: CircuitData, gen_data: GenerationMetadata):

    usings = generate_usings_for(list(gen_data.annotated_components.values()), circuit)
    externals = generate_externals_struct(circuit)
    output = generate_output_substruct(gen_data)
    objects = generate_objects_substruct(gen_data)

    calls = "\n".join(
        generate_true_call_signature(call, circuit, "static void ") + ";"
        for call in gen_data.call_endpoints
    )
    wrapper_calls = "\n".join(
        generate_wrapper_call(call, circuit) + ";" for call in gen_data.call_endpoints
    )

    struct_calls = "\n".join(
        generate_single_input_struct(name, struct)
        for (name, struct) in circuit.call_structs.items()
    )

    timer_calls = "\n".join(
        f"{generate_timer_signature(component)};"
        for component in circuit.components.values()
        if component.definition.timer_callset is not None
    )

    top_level_loader = top_level_real_loader()
    output_loader = generate_real_output_lookup_signature("", "override")

    return f"""
    struct {gen_data.struct_name} final : public Circuit {{
        {usings}

        using OWN_STRUCT_NAME = {gen_data.struct_name};

        {externals}
        Externals externals;

        {output}
        Outputs outputs;

        {objects}
        Objects objects;

        struct InputTypes {{
            {struct_calls}
        }};

        bool alwaystrue = true;

        {gen_data.struct_name}(nlohmann::json);

        {calls}

        {wrapper_calls}

        {timer_calls}

        template<class T>
        using {LOAD_CALL_TYPE} = void ({gen_data.struct_name}::*)({TIME_TYPE}, T, RawCall<const Circuit *>);

        {top_level_loader} override;

        {output_loader};

        void update_time({TIME_TYPE} new_time) {{
            externals.time = new_time > externals.time ? new_time : externals.time;
        }}


    }};
    """
