from pycircuit.circuit_builder.circuit import ComponentInput
from pycircuit.circuit_builder.definition import CallSpec
from pycircuit.cpp_codegen.call_generation.call_data import CallData
from pycircuit.cpp_codegen.call_generation.callset import get_inputs_for_callset
from pycircuit.cpp_codegen.call_generation.single_call.generate_output_calldata import (
    get_valid_path,
)
from pycircuit.cpp_codegen.generation_metadata import (
    AnnotatedComponent,
    GenerationMetadata,
)
from pycircuit.cpp_codegen.type_names import get_type_name_for_input

# On one hand, having this largely rely on auto
# make the codegen easier.
#
# On the other, it introduces huge room for error esepcially around reference autoconversion

# TODO move as much of this as possible into the metadata/graph generation phase
# completely decoupling the logic generation from the code generation

INPUT_STRUCT_NAME = "__INPUT__"
INPUT_NAME = "__input__"


def get_parent_name(c: ComponentInput, meta: GenerationMetadata) -> str:
    if c.parent == "external":
        return f"externals.{c.output_name}"
    else:
        parent = meta.annotated_components[c.parent]
        if (
            meta.annotated_components[c.parent]
            .output_data[c.output_name]
            .is_value_ephemeral
        ):
            root_name = f"{parent.component.name}_{c.output_name}_EV__"
        else:
            # TODO post-refactor nest this struct
            root_name = f"outputs.{c.parent}_{c.output_name}"

        return f"{root_name}"


def get_valid_path_external(input: ComponentInput, gen_data: GenerationMetadata):
    if input.parent == "external":
        the_external = gen_data.circuit.external_inputs[input.output_name]
        return f"externals.is_valid[{the_external.index}]"
    else:
        return get_valid_path(
            gen_data.annotated_components[input.parent], input.output_name
        )


# This is pretty close to what we run for initialization...
# init has no inputs, really only difference


def generate_input_calldata(
    annotated_component: AnnotatedComponent,
    callset: CallSpec,
    gen_data: GenerationMetadata,
) -> CallData:
    # TODO How to deal with generics? Can/should just do in order

    component = annotated_component.component

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

    values = "\n".join(all_values)
    inputs_prefix = f"""
    {{

        struct {INPUT_STRUCT_NAME} {{
            {input_struct_fields}
        }};

        {values}

        {INPUT_STRUCT_NAME} {INPUT_NAME} = {{
            {input_struct_initializers}
        }};
    }}
    """

    return CallData(local_prefix=inputs_prefix, call_params=[INPUT_NAME])
