from collections import OrderedDict
from dataclasses import dataclass
from typing import List, Set

from pycircuit.circuit_builder.circuit import Circuit, Component, ComponentInput
from pycircuit.cpp_codegen.call_generation.call_metadata import CallMetaData
from pycircuit.cpp_codegen.call_generation.ephemeral import (
    find_required_inputs,
    is_ephemeral,
)
from pycircuit.cpp_codegen.call_generation.find_children_of import find_all_children_of
from pycircuit.cpp_codegen.call_generation.generate_call_for_trigger import (
    generate_calls_for,
)
from pycircuit.cpp_codegen.generation_metadata import (
    AnnotatedComponent,
    GenerationMetadata,
)
from pycircuit.cpp_codegen.type_data import get_alias_for, get_using_declarations_for

EXTERNALS_STRUCT_NAME = "externals"
OUTPUT_STRUCT_NAME = "output"


def generate_externals_struct(circuit: Circuit) -> str:
    externals = "\n".join(
        f"{ext.type} {name};" for (name, ext) in circuit.external_inputs.items()
    )
    return f"""
        struct Externals {{
            {externals}
        }};
    """


def generate_output_declarations_for_component(component: Component):
    return f"{get_alias_for(component)}::Output {component.name};"


def generate_output_substruct(
    metadata: GenerationMetadata,
) -> str:

    circuit_declarations = "\n\n".join(
        generate_output_declarations_for_component(component.component)
        for component in metadata.annotated_components.values()
        if not component.is_ephemeral
    )

    return f"""
        struct Outputs {{
            {circuit_declarations}
        }};
    """


def generate_usings_for(circuit: Circuit) -> str:
    using_declarations_list: List[str] = sum(
        [
            get_using_declarations_for(component, circuit)
            for component in circuit.components.values()
        ],
        [],
    )
    return "\n".join(using_declarations_list)


def generate_metadata(
    circuit: Circuit, call_metas: List[CallMetaData]
) -> GenerationMetadata:
    all_non_ephemeral_components = set()

    for call in call_metas:
        children = find_all_children_of(call.triggered, circuit)
        all_non_ephemeral_components |= find_required_inputs(children)

    annotated_components = OrderedDict()

    for (name, component) in circuit.components.items():
        annotated_components[name] = AnnotatedComponent(
            component=component,
            is_ephemeral=is_ephemeral(component, all_non_ephemeral_components),
        )

    return GenerationMetadata(
        non_ephemeral_components=all_non_ephemeral_components,
        circuit=circuit,
        annotated_components=annotated_components,
    )


def generate_circuit_struct(
    circuit: Circuit, call_metas: List[CallMetaData], name: str
):

    gen_data = generate_metadata(circuit, call_metas)

    usings = generate_usings_for(circuit)
    externals = generate_externals_struct(circuit)
    output = generate_output_substruct(gen_data)

    calls = "\n".join(generate_calls_for(call, gen_data) for call in call_metas)

    return f"""
    struct {name} {{
        {usings}

        {externals}
        Externals externals;

        {output}
        Outputs outputs;

        {calls}
    }};
    """
