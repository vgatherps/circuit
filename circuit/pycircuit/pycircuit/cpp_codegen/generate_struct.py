from dataclasses import dataclass
from typing import List

from pycircuit.circuit_builder.circuit import Circuit, Component, ComponentInput
from pycircuit.cpp_codegen.type_data import (
    get_output_types_for,
    get_using_declarations_for,
)

EXTERNALS_STRUCT_NAME = "externals"
OUTPUT_STRUCT_NAME = "output"


def get_sorted_inputs(component: Component) -> List[ComponentInput]:
    sorted_by_idx = sorted(component.inputs.values(), key=lambda x: x.input_idx)


def generate_externals_struct(circuit: Circuit) -> str:
    externals = "\n".join(
        f"{ext.type} {name};" for (name, ext) in circuit.external_inputs.items()
    )
    return f"""
        struct Externals {{
            {externals}
        }};
    """


def generate_output_substruct(circuit: Circuit) -> str:
    # TODO this basic loop more or less skips outputs
    output_type_declarations_list = sum(
        [
            get_using_declarations_for("Outputs", "Externals", c)
            for c in circuit.components.values()
        ],
        [],
    )

    output_type_declarations = "\n".join(output_type_declarations_list)

    outputs = "\n".join(
        f"{c.definition.class_name}<{','.join(get_output_types_for(c))}>::Output {name};"
        for (name, c) in circuit.components.items()
    )

    return f"""
        struct Outputs {{
            {output_type_declarations}
            {outputs}
        }};
    """


def generate_circuit_struct(circuit: Circuit, name: str):
    externals = generate_externals_struct(circuit)
    output = generate_output_substruct(circuit)

    return f"""
    struct {name} {{
        {externals}
        Externals externals;

        {output}
        Outputs outputs;
    }};
    """
