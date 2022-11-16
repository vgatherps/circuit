from dataclasses import dataclass

from pycircuit.circuit_builder.circuit import Circuit

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


def generate_output_substruct(circuit: Circuit) -> str:
    # TODO this basic loop more or less skips outputs
    outputs = "\n".join(
        f"{c.definition.class_name}::Output {name};"
        for (name, c) in circuit.components.items()
    )

    return f"""
        struct Outputs {{
            {outputs}
        }};
    """


def generate_circuit_struct(circuit: Circuit, name: str):
    externals = generate_externals_struct(circuit)
    output = generate_output_substruct(circuit)

    return f"""
    struct {name} {{
        {externals}
        {output}

        Externals externals;
        Outputs outputs;
    }}
    """
