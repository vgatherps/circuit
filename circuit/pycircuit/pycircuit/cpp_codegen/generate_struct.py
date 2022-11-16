from dataclasses import dataclass
from typing import List

from pycircuit.circuit_builder.circuit import Circuit, Component, ComponentInput
from pycircuit.cpp_codegen.call_generation.call_metadata import CallMetaData
from pycircuit.cpp_codegen.call_generation.generate_call_for_trigger import (
    generate_calls_for,
)
from pycircuit.cpp_codegen.type_data import (
    get_output_types_for,
    get_using_declarations_for,
)

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

    using_declarations = "\n".join(
        get_using_declarations_for("Outputs", "Externals", component)
    )
    output_declaration = f"{component.definition.class_name}<{','.join(get_output_types_for(component))}>::Output {component.name};"

    return f"""
        {using_declarations}
        {output_declaration}
    """


def generate_output_substruct(circuit: Circuit) -> str:

    circuit_declarations = "\n\n".join(
        map(generate_output_declarations_for_component, circuit.components.values())
    )

    return f"""
        struct Outputs {{
            {circuit_declarations}
        }};
    """


def generate_circuit_struct(
    circuit: Circuit, call_metas: List[CallMetaData], name: str
):
    externals = generate_externals_struct(circuit)
    output = generate_output_substruct(circuit)

    calls = "\n".join(generate_calls_for(call, circuit) for call in call_metas)

    return f"""
    struct {name} {{
        {externals}
        Externals externals;

        {output}
        Outputs outputs;

        {calls}
    }};
    """
